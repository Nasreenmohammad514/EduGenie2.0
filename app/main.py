from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import Base, engine, get_db
from app.models import User
from app.routers import chat, quiz, upload, progress, path as path_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EduGenie 2.0 - AI-Powered Adaptive Learning Platform")

app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(upload.router)
app.include_router(progress.router)
app.include_router(path_router.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


class UserCreateRequest(BaseModel):
    name: str
    level: str = "high_school"
    language: str = "English"


@app.post("/api/users")
def create_user(req: UserCreateRequest, db: Session = Depends(get_db)):
    user = User(name=req.name, level=req.level, language=req.language)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "level": user.level, "language": user.language}


@app.get("/api/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    return {"id": user.id, "name": user.name, "level": user.level, "language": user.language}


@app.get("/")
def serve_frontend():
    return FileResponse("templates/index.html")
