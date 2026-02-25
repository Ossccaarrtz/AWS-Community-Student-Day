# AWS Community Student Day — QR Check-In & Badge System

A full-stack event check-in application built for **AWS Community Student Day**. Attendees present a QR code from their ticket; staff scan it with a tablet or laptop camera to instantly verify registration, mark attendance in **Amazon DynamoDB**, and generate a personalised PDF badge on the spot.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [AWS Setup](#aws-setup)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Environment Variables](#environment-variables)
- [Deployment (AWS Lambda)](#deployment-aws-lambda)

---

## Overview

This system solves the problem of manual event check-in. Instead of printed lists or manual searches:

1. Each registered attendee has a **unique QR code** tied to their `ticketId`.
2. Staff open the web app on any device with a camera.
3. Scanning the QR code calls the backend, which looks up the attendee in DynamoDB, marks them as checked in (`checkedIn: true`), and returns a generated PDF badge.
4. The badge can be downloaded and printed on site.

---

## Architecture

```
┌─────────────────────────┐          ┌──────────────────────────────┐
│   Frontend (React/Vite) │   HTTP   │  Backend (FastAPI / Uvicorn) │
│                         │ ───────► │                              │
│  • Camera QR Scanner    │          │  POST /badge                 │
│  • Confirm Modal        │          │  POST /checkin               │
│  • PDF Badge download   │ ◄─────── │  GET  /health                │
└─────────────────────────┘  JSON    └──────────────┬───────────────┘
                                                    │ boto3
                                                    ▼
                                        ┌───────────────────┐
                                        │   Amazon DynamoDB │
                                        │   Table: EventUsers│
                                        │   GSI: TicketIdIndex│
                                        └───────────────────┘
```

> The backend is also **AWS Lambda-compatible** via [Mangum](https://mangum.io/), so it can be deployed serverlessly behind API Gateway.

---

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| [React](https://react.dev/) | 19 | UI framework |
| [Vite](https://vite.dev/) | 7 | Build tool & dev server |
| [html5-qrcode](https://github.com/mebjas/html5-qrcode) | 2.3 | QR camera scanning |
| [@yudiel/react-qr-scanner](https://github.com/yudielcurbelo/react-qr-scanner) | 2.5 | React QR scanner component |
| [@zxing/browser](https://github.com/zxing-js/library) | 0.1 | QR decoding library |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/) | 3.11+ | Runtime |
| [FastAPI](https://fastapi.tiangolo.com/) | 0.129 | REST API framework |
| [Uvicorn](https://www.uvicorn.org/) | 0.41 | ASGI server |
| [Mangum](https://mangum.io/) | 0.21 | AWS Lambda adapter for FastAPI |
| [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) | 1.42 | AWS SDK — DynamoDB client |
| [ReportLab](https://www.reportlab.com/) | 4.4 | PDF badge generation |
| [Pydantic](https://docs.pydantic.dev/) | 2.12 | Request/response validation |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | 1.2 | Environment variable management |
| [Pillow](https://python-pillow.org/) | 12.1 | Image processing for badges |

### Cloud
| Service | Purpose |
|---|---|
| **Amazon DynamoDB** | Attendee database (NoSQL) |
| **AWS Lambda** (optional) | Serverless backend deployment |
| **Amazon API Gateway** (optional) | HTTP trigger for Lambda |

---

## Project Structure

```
AWS-Community-Student-Day/
├── backend/
│   ├── main.py                  # FastAPI app — all API routes
│   ├── requirements.txt         # Python dependencies
│   ├── verify_env.py            # Helper script to verify AWS env vars
│   ├── .env                     # Local environment variables (not committed)
│   ├── db/
│   │   └── dynamo.py            # DynamoDB connection (boto3 resource)
│   ├── repositories/
│   │   └── event_users_repo.py  # DynamoDB queries (get by ticketId, mark check-in)
│   └── utils/
│       └── pdf_badge.py         # PDF badge generation with ReportLab
│
└── frontend/
    ├── package.json             # Node dependencies & scripts
    ├── vite.config.js           # Vite configuration
    ├── index.html               # Entry HTML
    ├── .env                     # Frontend environment variables (VITE_API_URL)
    └── src/
        ├── main.jsx             # React entry point
        ├── App.jsx              # Root component / routing
        ├── pages/
        │   ├── CheckInPage.jsx      # Main check-in UI (QR scan + modal)
        │   └── BadgePreviewPage.jsx # Badge preview / download page
        ├── components/
        │   ├── qr/
        │   │   └── QRScanner.jsx    # Camera-based QR scanner component
        │   ├── ConfirmModal.jsx     # Overlay modal (loading / confirm / error)
        │   └── ErrorBoundary.jsx    # React error boundary
        └── utils/
            └── pdfUtils.js          # Helper: download PDF from base64 string
```

---

## Prerequisites

Make sure you have the following installed before continuing:

| Tool | Minimum Version | Check with |
|---|---|---|
| **Node.js** | 18+ | `node -v` |
| **npm** | 9+ | `npm -v` |
| **Python** | 3.11+ | `python --version` |
| **pip** | latest | `pip --version` |
| **AWS CLI** | v2 | `aws --version` |

You will also need:
- An **AWS account** with access to DynamoDB.
- AWS credentials configured locally (`aws configure`) **or** IAM environment variables set in `.env`.

---


## Backend Setup

### 1. Navigate to the backend folder

```bash
cd AWS-Community-Student-Day/backend
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file inside the `backend/` folder:

```env
# The name of your DynamoDB table
TABLE_NAME=EventUsers

# AWS region where the table lives
AWS_REGION=us-east-1

# Name of the GSI for ticker lookups
TICKET_GSI_NAME=TicketIdIndex

# AWS credentials (only needed if NOT using aws configure or IAM roles)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```



### 5. Verify configuration (optional)

```bash
python verify_env.py
```

---

## Frontend Setup

### 1. Navigate to the frontend folder

```bash
cd AWS-Community-Student-Day/frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment variables

Create a `.env` file inside the `frontend/` folder:

```env
# URL of the running backend API (no trailing slash)
VITE_API_URL=http://localhost:8000
```

---

## Running the Application

You need **two terminals running simultaneously**.

### Terminal 1 — Start the Backend

```bash
cd AWS-Community-Student-Day/backend

# Activate virtual environment first
venv\Scripts\activate      # Windows
# source venv/bin/activate # macOS/Linux

uvicorn main:app --reload --port 8000
```

The API will be available at: **http://localhost:8000**
Interactive API docs (Swagger UI): **http://localhost:8000/docs**

### Terminal 2 — Start the Frontend

```bash
cd AWS-Community-Student-Day/frontend
npm run dev
```

The web app will be available at: **http://localhost:5173**

---

## API Reference

### `GET /health`
Health check. Returns current table name, GSI name, and region.

**Response:**
```json
{ "ok": true, "table": "EventUsers", "gsi": "TicketIdIndex", "region": "us-east-1" }
```

---

### `POST /badge`
Looks up an attendee by their `ticketId` and returns their info + a base64-encoded PDF badge. **Does NOT mark the attendee as checked in.**

**Request body:**
```json
{ "ticketId": "TKT-2026-MKVIV4CK-D9C4FB27" }
```

**Response (200 OK):**
```json
{
  "ok": true,
  "ticketId": "TKT-2026-MKVIV4CK-D9C4FB27",
  "userId": "usr-abc123",
  "name": "Oscar Hernandez",
  "profession": "Cloud Engineer",
  "checkedIn": false,
  "checkedInAt": "N/A",
  "contentType": "application/pdf",
  "pdfBase64": "JVBERi0xLjc..."
}
```

**Error responses:** `400` (missing ticketId), `404` (not found), `500` (DynamoDB error)

---

### `POST /checkin`
Looks up an attendee by `ticketId`, marks them as `checkedIn: true` in DynamoDB (with a timestamp), and returns their info + a PDF badge.

**Request body:**
```json
{ "ticketId": "TKT-2026-MKVIV4CK-D9C4FB27" }
```

**Response (200 OK):**
```json
{
  "ok": true,
  "ticketId": "TKT-2026-MKVIV4CK-D9C4FB27",
  "userId": "usr-abc123",
  "name": "Oscar Hernandez",
  "profession": "Cloud Engineer",
  "checkedIn": true,
  "checkedInAt": "2026-03-15T09:30:00+00:00",
  "alreadyCheckedIn": false,
  "contentType": "application/pdf",
  "pdfBase64": "JVBERi0xLjc..."
}
```

> If the attendee was already checked in, `alreadyCheckedIn` will be `true`.

**Error responses:** `400`, `403` (missing IAM permissions), `404`, `500`

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                         CheckInPage (React)                       │
│                                                                  │
│  1. QRScanner component activates the device camera.             │
│  2. When a QR code is detected, the raw text is parsed to        │
│     extract the ticketId (supports plain text, URLs, JSON).      │
│  3. A de-duplication lock (2 s cooldown) prevents accidental     │
│     double-scans of the same code.                               │
│  4. POST /badge is called → shows a loading modal.               │
│  5. On success → a confirmation modal shows the attendee's name. │
│  6. Staff confirm → the PDF badge is downloaded automatically.   │
│  7. On error → an error modal is shown; scanner re-enables.      │
└──────────────────────────────────────────────────────────────────┘
```

### QR Code Formats Supported

The app intelligently extracts the `ticketId` from multiple QR formats:

| Format | Example |
|---|---|
| Plain text | `TKT-2026-MKVIV4CK-D9C4FB27` |
| URL (path segment) | `https://event.com/checkin/TKT-2026-MKVIV4CK-D9C4FB27` |
| URL (query param) | `https://event.com/?ticketId=TKT-2026-MKVIV4CK-D9C4FB27` |
| JSON string | `{"ticketId":"TKT-2026-MKVIV4CK-D9C4FB27"}` |

### Badge PDF Generation

The backend uses **ReportLab** to dynamically build a PDF badge containing the attendee's name, profession, ticket ID, and check-in timestamp. The PDF is returned as a **base64-encoded string** in the JSON response so the frontend can trigger a browser download without needing a file storage service.

### Duplicate Check-In Protection

The DynamoDB `UpdateItem` uses a **ConditionExpression** that only writes if `checkedIn` is `false` or does not exist. If the condition fails (already checked in), the backend returns `alreadyCheckedIn: true` without overwriting the original timestamp.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `TABLE_NAME` | Yes | `EventUsers` | DynamoDB table name |
| `AWS_REGION` | Yes | `us-east-1` | AWS region |
| `TICKET_GSI_NAME` | No | `TicketIdIndex` | Name of the GSI for ticket lookups |
| `AWS_ACCESS_KEY_ID` | No* | — | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No* | — | AWS secret key |

*Not required if using `aws configure` or IAM roles.

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes | Full URL of the backend API, e.g. `http://localhost:8000` |

---

## Deployment (AWS Lambda)

The backend is already Lambda-ready thanks to **Mangum**. The last line of `main.py` wraps the FastAPI app:

```python
handler = Mangum(app)
```

To deploy:
1. Package the backend code and dependencies into a zip file (or use a container image).
2. Create an AWS Lambda function pointing to `main.handler`.
3. Attach appropriate IAM permissions: `dynamodb:Query`, `dynamodb:UpdateItem`.
4. Create an **API Gateway** (HTTP API) and connect it to the Lambda.
5. Update `VITE_API_URL` in the frontend `.env` to point to the API Gateway URL.
6. Build the frontend for production: `npm run build` (output is in `frontend/dist/`).
7. Host the `dist/` folder on **S3 + CloudFront** or any static hosting service.

---

## License

This project was developed for the **AWS Community Student Day** event. All rights reserved to the contributors.
