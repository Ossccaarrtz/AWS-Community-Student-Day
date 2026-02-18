import os
import io
import base64
from datetime import datetime, timezone
from functools import lru_cache

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from dotenv import load_dotenv
load_dotenv()  # lee .env (si existe) en local

# ---------- Config ----------
TABLE_NAME = os.getenv("TABLE_NAME", "EventUsers")
TICKET_GSI = os.getenv("TICKET_GSI_NAME", "TicketIdIndex")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

@lru_cache
def get_table():
    """Lazy init: no toca DynamoDB al arrancar Uvicorn."""
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return ddb.Table(TABLE_NAME)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo cierran a su dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class PdfReq(BaseModel):
    id: str

class TicketReq(BaseModel):
    ticketId: str

# ---------- PDF helper ----------
def build_badge_pdf(ticket_id: str, name: str, profession: str, checked_in_at: str) -> str:
    """
    Genera un PDF tamaño etiqueta y regresa base64 string.
    4x2 pulgadas.
    """
    width, height = 4 * inch, 2 * inch
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.25 * inch, 1.65 * inch, "AWS Community Student Day")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.25 * inch, 1.35 * inch, f"{name}")

    c.setFont("Helvetica", 9)
    c.drawString(0.25 * inch, 1.15 * inch, f"{profession}")
    c.drawString(0.25 * inch, 0.95 * inch, f"Ticket: {ticket_id}")

    c.setFont("Helvetica", 8)
    c.drawString(0.25 * inch, 0.75 * inch, f"CheckedInAt: {checked_in_at}")

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(0.25 * inch, 0.25 * inch, "Badge generado por AWSQR")

    c.showPage()
    c.save()

    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"ok": True, "table": TABLE_NAME, "gsi": TICKET_GSI, "region": AWS_REGION}

@app.post("/pdf")
def pdf_dummy(req: PdfReq):
    now = datetime.now(timezone.utc).isoformat()
    pdf_b64 = build_badge_pdf(
        ticket_id=req.id,
        name="DUMMY NAME",
        profession="DUMMY PROFESSION",
        checked_in_at=now
    )
    return {"contentType": "application/pdf", "pdfBase64": pdf_b64}

@app.post("/badge")
def badge_preview(req: TicketReq):
    """
    Preview REAL: busca por ticketId en el GSI y genera el PDF.
    NO hace UpdateItem (sirve mientras no tengas permisos).
    """
    ticket_id = (req.ticketId or "").strip()
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticketId requerido")

    table = get_table()

    try:
        resp = table.query(
            IndexName=TICKET_GSI,
            KeyConditionExpression=Key("ticketId").eq(ticket_id),
            ProjectionExpression="#uid, #tid, #name, #prof, checkedIn, checkedInAt",
            ExpressionAttributeNames={
                "#uid": "userId",
                "#tid": "ticketId",
                "#name": "name",
                "#prof": "profession",
            },
        )
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", "DynamoDB ClientError")
        raise HTTPException(status_code=500, detail=msg)

    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="ticketId no encontrado")

    item = items[0]
    user_id = item.get("userId") or "UNKNOWN"
    name = item.get("name") or "UNKNOWN"
    profession = item.get("profession") or "N/A"
    checked_in = bool(item.get("checkedIn", False))
    checked_in_at = item.get("checkedInAt") or "N/A"

    pdf_b64 = build_badge_pdf(
        ticket_id=ticket_id,
        name=name,
        profession=profession,
        checked_in_at=checked_in_at,
    )

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
    """
    Check-in REAL: requiere dynamodb:UpdateItem.
    Si todavía no tienes permisos, te regresa 403 con el mensaje real de AWS.
    """
    ticket_id = (req.ticketId or "").strip()
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticketId requerido")

    table = get_table()
    now = datetime.now(timezone.utc).isoformat()

    try:
        resp = table.query(
            IndexName=TICKET_GSI,
            KeyConditionExpression=Key("ticketId").eq(ticket_id),
            ProjectionExpression="#uid, #tid, #name, #prof, checkedIn, checkedInAt",
            ExpressionAttributeNames={
                "#uid": "userId",
                "#tid": "ticketId",
                "#name": "name",
                "#prof": "profession",
            },
        )

        items = resp.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="ticketId no encontrado")

        item = items[0]
        user_id = item.get("userId")
        if not user_id:
            raise HTTPException(status_code=500, detail="El item no tiene userId")

        name = item.get("name") or "UNKNOWN"
        profession = item.get("profession") or "N/A"

        # Update (puede fallar por permisos IAM)
        try:
            upd = table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET checkedIn = :true, checkedInAt = :now",
                ConditionExpression="attribute_not_exists(checkedIn) OR checkedIn = :false",
                ExpressionAttributeValues={":true": True, ":false": False, ":now": now},
                ReturnValues="ALL_NEW",
            )
            updated = upd.get("Attributes", {})
            already = False
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            updated = item
            already = True

        checked_in_at = updated.get("checkedInAt") or now

        pdf_b64 = build_badge_pdf(
            ticket_id=ticket_id,
            name=name,
            profession=profession,
            checked_in_at=checked_in_at,
        )

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

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", "DynamoDB ClientError")
        if code in ("AccessDeniedException", "UnrecognizedClientException"):
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=500, detail=msg)

# Para AWS Lambda
handler = Mangum(app)
