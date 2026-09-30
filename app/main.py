from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import get_connection, init_db
from app.s3 import upload_image

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class MessageOut(BaseModel):
    id: int
    content: str
    image_url: str
    created_at: datetime


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="WeHelp Message Board", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/messages", response_model=list[MessageOut])
def list_messages():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, image_url, created_at
                FROM messages
                ORDER BY created_at DESC, id DESC
                """
            )
            rows = cur.fetchall()
    return [MessageOut(**row) for row in rows]


@app.post("/api/messages", response_model=MessageOut, status_code=201)
def create_message(
    content: str = Form(...),
    image: UploadFile = File(...),
):
    text = content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Content is required")
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Content must be 1000 characters or fewer")

    image_url = upload_image(image)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (content, image_url)
                VALUES (%s, %s)
                """,
                (text, image_url),
            )
            message_id = cur.lastrowid
            cur.execute(
                """
                SELECT id, content, image_url, created_at
                FROM messages
                WHERE id = %s
                """,
                (message_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create message")
    return MessageOut(**row)
