import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form
from dotenv import load_dotenv

from app.services import rag_service

load_dotenv()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_material(user_id: int = Form(...), file: UploadFile = File(...)):
    save_path = os.path.join(UPLOAD_DIR, f"user{user_id}_{file.filename}")
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

        filename_lower = file.filename.lower()
    if filename_lower.endswith(".pdf"):
        text = rag_service.extract_text_from_pdf(save_path)
    elif filename_lower.endswith(".docx"):
        text = rag_service.extract_text_from_docx(save_path)
    else:
        with open(save_path, "r", errors="ignore") as f:
            text = f.read()

    chunk_count = rag_service.index_document(user_id, file.filename, text)

    return {
        "filename": file.filename,
        "chunks_indexed": chunk_count,
        "message": "Material indexed. Ask questions with use_rag=true to use it.",
    }
