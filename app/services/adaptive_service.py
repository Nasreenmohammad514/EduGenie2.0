from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import QuizAttempt, LearningPathItem

WEAK_TOPIC_THRESHOLD = 60.0  # average score % below this = "weak"
RAISE_THRESHOLD = 80.0        # score % at/above this = raise difficulty
LOWER_THRESHOLD = 50.0        # score % below this = lower difficulty

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]


def next_difficulty(current: str, score_percent: float) -> str:
    """Step difficulty up or down by one level based on the latest score."""
    idx = DIFFICULTY_LEVELS.index(current) if current in DIFFICULTY_LEVELS else 1
    if score_percent >= RAISE_THRESHOLD:
        idx = min(idx + 1, len(DIFFICULTY_LEVELS) - 1)
    elif score_percent < LOWER_THRESHOLD:
        idx = max(idx - 1, 0)
    return DIFFICULTY_LEVELS[idx]


def get_weak_topics(db: Session, user_id: int) -> list[dict]:
    """Average score per topic; anything below the threshold is 'weak'."""
    rows = (
        db.query(
            QuizAttempt.topic,
            func.avg(QuizAttempt.score_percent).label("avg_score"),
            func.count(QuizAttempt.id).label("attempts"),
        )
        .filter(QuizAttempt.user_id == user_id)
        .group_by(QuizAttempt.topic)
        .all()
    )
    return [
        {"topic": r.topic, "avg_score": round(r.avg_score, 1), "attempts": r.attempts}
        for r in rows
        if r.avg_score < WEAK_TOPIC_THRESHOLD
    ]


def run_cycle(db: Session, user_id: int, topic: str) -> dict:
    """The Learn -> Assess -> Analyze -> Adapt loop from the project's
    approach slide, made concrete as one callable function.

    Call this right after a quiz is submitted (Assess already happened
    by that point — this does Analyze + Adapt and reports the result).
    """
    weak_topics = get_weak_topics(db, user_id)
    weak_names = {w["topic"] for w in weak_topics}

    # Adapt: push weak topics earlier in the learning path, mark others
    # as completed if they're no longer weak and have an attempt on record.
    items = db.query(LearningPathItem).filter(LearningPathItem.user_id == user_id).all()
    reordered = sorted(items, key=lambda item: (item.topic not in weak_names, item.order_index))

    for i, item in enumerate(reordered):
        item.order_index = i
        item.status = "weak" if item.topic in weak_names else item.status

    db.commit()

    return {
        "topic_just_assessed": topic,
        "weak_topics": weak_topics,
        "updated_path_order": [item.topic for item in reordered],
    }
