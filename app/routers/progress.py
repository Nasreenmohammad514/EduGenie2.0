from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import QuizAttempt
from app.services import adaptive_service

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/{user_id}")
def get_progress(user_id: int, db: Session = Depends(get_db)):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.timestamp)
        .all()
    )

    by_topic = (
        db.query(
            QuizAttempt.topic,
            func.avg(QuizAttempt.score_percent).label("avg_score"),
            func.count(QuizAttempt.id).label("attempts"),
        )
        .filter(QuizAttempt.user_id == user_id)
        .group_by(QuizAttempt.topic)
        .all()
    )

    weak_topics = adaptive_service.get_weak_topics(db, user_id)

    return {
        "total_attempts": len(attempts),
        "topics": [
            {"topic": t.topic, "avg_score": round(t.avg_score, 1), "attempts": t.attempts}
            for t in by_topic
        ],
        "weak_topics": weak_topics,
        "score_history": [
            {"topic": a.topic, "score": a.score_percent, "timestamp": a.timestamp.isoformat()}
            for a in attempts
        ],
    }
