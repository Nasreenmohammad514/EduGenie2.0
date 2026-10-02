from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import LearningPathItem
from app.services import gemini_service

router = APIRouter(prefix="/api/path", tags=["learning-path"])


class PathRequest(BaseModel):
    user_id: int
    subject: str


PATH_PROMPT_TEMPLATE = """Create a learning roadmap for the subject "{subject}" with 6 to 9
topics ordered from beginner to advanced.

Return ONLY valid JSON (no markdown fences) as a list of topic names, like:
["Topic 1", "Topic 2", "Topic 3"]
"""


@router.post("/generate")
def generate_path(req: PathRequest, db: Session = Depends(get_db)):
    prompt = PATH_PROMPT_TEMPLATE.format(subject=req.subject)
    topics = gemini_service.ask_json(prompt)

    if isinstance(topics, dict) and "error" in topics:
        return topics

    # Replace any existing path for this user with the new one.
    db.query(LearningPathItem).filter(LearningPathItem.user_id == req.user_id).delete()
    for i, topic in enumerate(topics):
        db.add(LearningPathItem(user_id=req.user_id, topic=topic, order_index=i))
    db.commit()

    return {"subject": req.subject, "topics": topics}


@router.get("/{user_id}")
def get_path(user_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(LearningPathItem)
        .filter(LearningPathItem.user_id == user_id)
        .order_by(LearningPathItem.order_index)
        .all()
    )
    return [
        {"topic": i.topic, "status": i.status, "order": i.order_index}
        for i in items
    ]
