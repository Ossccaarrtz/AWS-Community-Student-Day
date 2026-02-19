import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
from botocore.exceptions import ClientError

from dotenv import load_dotenv
load_dotenv()

from repositories.event_users_repo import EventUsersRepo
from utils.pdf_badge import build_badge_pdf
from db.dynamo import TABLE_NAME, AWS_REGION

TICKET_GSI = os.getenv("TICKET_GSI_NAME", "TicketIdIndex")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PdfReq(BaseModel):
    id: str

class TicketReq(BaseModel):
    ticketId: str

@app.get("/health")
def health():
    return {"ok": True, "table": TABLE_NAME, "gsi": TICKET_GSI, "region": AWS_REGION}

@app.post("/pdf")
def pdf_dummy(req: PdfReq):
    now = datetime.now(timezone.utc).isoformat()
    pdf_b64 = build_badge_pdf(req.id, "DUMMY NAME", "DUMMY PROFESSION", now)
    return {"contentType": "application/pdf", "pdfBase64": pdf_b64}

@app.post("/badge")
def badge(req: TicketReq):
    ticket_id = (req.ticketId or "").strip()
    print(f"[DEBUG /badge] raw='{req.ticketId}' | stripped='{ticket_id}' | len={len(ticket_id)} | repr={repr(ticket_id)}")
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticketId requerido")

    try:
        item = EventUsersRepo.get_by_ticket_id(ticket_id)
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", "DynamoDB ClientError")
        raise HTTPException(status_code=500, detail=msg)

    print(f"[DEBUG /badge] DynamoDB item={item}")
    if not item:
        raise HTTPException(status_code=404, detail="ticketId no encontrado")

    user_id = item.get("userId") or "UNKNOWN"
    name = item.get("name") or "UNKNOWN"
    profession = item.get("profession") or "N/A"
    checked_in = item.get("checkedIn") is True
    checked_in_at = item.get("checkedInAt") or "N/A"

    pdf_b64 = build_badge_pdf(ticket_id, name, profession, checked_in_at)

    return {
        "ok": True,
        "ticketId": ticket_id,
        "userId": user_id,
        "name": name,
        "profession": profession,
        "checkedIn": checked_in,
        "checkedInAt": checked_in_at,
        "contentType": "application/pdf",
        "pdfBase64": pdf_b64,
    }

@app.post("/checkin")
def checkin(req: TicketReq):
    ticket_id = (req.ticketId or "").strip()
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticketId requerido")

    now = datetime.now(timezone.utc).isoformat()

    # 1) buscar por ticket
    item = EventUsersRepo.get_by_ticket_id(ticket_id)
    if not item:
        raise HTTPException(status_code=404, detail="ticketId no encontrado")

    user_id = item.get("userId")
    if not user_id:
        raise HTTPException(status_code=500, detail="El item no tiene userId")

    name = item.get("name") or "UNKNOWN"
    profession = item.get("profession") or "N/A"

    # 2) marcar checkin (requiere permisos)
    try:
        updated, already = EventUsersRepo.mark_checkin(user_id, now)
        checked_in_at = (updated.get("checkedInAt") if updated else None) or item.get("checkedInAt") or now
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", "DynamoDB ClientError")
        if code in ("AccessDeniedException", "UnrecognizedClientException"):
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=500, detail=msg)

    pdf_b64 = build_badge_pdf(ticket_id, name, profession, checked_in_at)

    return {
        "ok": True,
        "ticketId": ticket_id,
        "userId": user_id,
        "name": name,
        "profession": profession,
        "checkedIn": True,
        "checkedInAt": checked_in_at,
        "alreadyCheckedIn": already,
        "contentType": "application/pdf",
        "pdfBase64": pdf_b64,
    }

handler = Mangum(app)
