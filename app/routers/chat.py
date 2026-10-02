from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Interaction
from app.services import gemini_service, rag_service

router = APIRouter(prefix="/api", tags=["chat"])


class AskRequest(BaseModel):
    user_id: int
    question: str
    topic: str = "general"
    use_rag: bool = False


class AskResponse(BaseModel):
    answer: str
    used_rag: bool
    sources: list[str] = []


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    level = user.level if user else "high_school"
    language = user.language if user else "English"

    system_instruction = (
        f"You are EduGenie, an educational assistant. Explain things clearly "
        f"for a {level} level learner. Respond in {language}. Keep answers "
        f"focused and include a short educational example where helpful."
    )

    sources = []
    if req.use_rag:
        hits = rag_service.retrieve_context(req.user_id, req.question)
        if hits:
            context = "\n\n".join(h["text"] for h in hits)
            sources = sorted(set(h["source"] for h in hits))
            prompt = (
                f"Using ONLY the context below, answer the question. "
                f"If the context doesn't contain the answer, say so.\n\n"
                f"Context:\n{context}\n\nQuestion: {req.question}"
            )
        else:
            prompt = (
                f"The learner has no relevant uploaded material for this "
                f"question. Answer from general knowledge.\n\nQuestion: {req.question}"
            )
    else:
        prompt = req.question

    answer = gemini_service.ask(prompt, system_instruction)

    interaction = Interaction(
        user_id=req.user_id,
        topic=req.topic,
        question=req.question,
        answer=answer,
        used_rag=1 if (req.use_rag and sources) else 0,
    )
    db.add(interaction)
    db.commit()

    return AskResponse(answer=answer, used_rag=bool(sources), sources=sources)


@router.get("/history/{user_id}")
def history(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.timestamp.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "topic": r.topic,
            "question": r.question,
            "answer": r.answer,
            "used_rag": bool(r.used_rag),
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]
