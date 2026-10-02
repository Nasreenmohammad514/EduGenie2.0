from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import QuizAttempt
from app.services import gemini_service, adaptive_service

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class QuizRequest(BaseModel):
    user_id: int
    topic: str
    num_questions: int = 5
    difficulty: str = "medium"  # caller can pass the learner's last known difficulty


class QuizSubmitRequest(BaseModel):
    user_id: int
    topic: str
    difficulty: str
    total_questions: int
    correct_answers: int


QUIZ_PROMPT_TEMPLATE = """Generate {n} multiple-choice quiz questions on the topic "{topic}"
at {difficulty} difficulty for a student.

Return ONLY valid JSON (no markdown fences, no extra text) as a list like this:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "A"
  }}
]
"""


@router.post("/generate")
def generate_quiz(req: QuizRequest):
    prompt = QUIZ_PROMPT_TEMPLATE.format(
        n=req.num_questions, topic=req.topic, difficulty=req.difficulty
    )
    questions = gemini_service.ask_json(prompt)
    return {"topic": req.topic, "difficulty": req.difficulty, "questions": questions}


@router.post("/submit")
def submit_quiz(req: QuizSubmitRequest, db: Session = Depends(get_db)):
    score_percent = (req.correct_answers / req.total_questions) * 100 if req.total_questions else 0

    attempt = QuizAttempt(
        user_id=req.user_id,
        topic=req.topic,
        difficulty=req.difficulty,
        score_percent=score_percent,
        total_questions=req.total_questions,
        correct_answers=req.correct_answers,
    )
    db.add(attempt)
    db.commit()

    next_difficulty = adaptive_service.next_difficulty(req.difficulty, score_percent)
    cycle_result = adaptive_service.run_cycle(db, req.user_id, req.topic)

    return {
        "score_percent": score_percent,
        "next_difficulty": next_difficulty,
        "feedback_loop": cycle_result,
    }
