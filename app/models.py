from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """A learner profile. Kept intentionally simple (no password) for a
    college project — swap in real auth before any real-world deployment."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    level = Column(String, default="high_school")  # e.g. kid, high_school, undergrad
    language = Column(String, default="English")
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="user")
    quiz_attempts = relationship("QuizAttempt", back_populates="user")
    path_items = relationship("LearningPathItem", back_populates="user")


class Interaction(Base):
    """Every question asked and answer given — this is what makes the
    system remember instead of being one-shot."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)
    question = Column(Text)
    answer = Column(Text)
    used_rag = Column(Integer, default=0)  # 1 if grounded in uploaded material
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interactions")


class QuizAttempt(Base):
    """One quiz attempt on one topic, used to drive adaptive difficulty
    and weak-topic detection."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)
    difficulty = Column(String, default="medium")  # easy | medium | hard
    score_percent = Column(Float)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quiz_attempts")


class LearningPathItem(Base):
    """One topic in a learner's dynamic roadmap."""
    __tablename__ = "learning_path_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String)
    order_index = Column(Integer)
    status = Column(String, default="pending")  # pending | in_progress | completed | weak
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="path_items")
