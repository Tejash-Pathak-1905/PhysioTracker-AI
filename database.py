"""
database.py
-----------
SQLAlchemy ORM models and session management.
All models match the schema defined in the PRD exactly.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'physio_tracker.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ──────────────────────────── MODELS ────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, nullable=False, unique=True)
    age        = Column(Integer, nullable=True)
    gender     = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessments   = relationship("Assessment",  back_populates="user", cascade="all, delete-orphan")
    exercise_plans = relationship("ExercisePlan", back_populates="user", cascade="all, delete-orphan")
    session_logs   = relationship("SessionLog",  back_populates="user", cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint        = Column(String, nullable=False)
    pain_level       = Column(Integer, nullable=False)   # 1–10
    llm_raw_response = Column(Text)                      # full JSON string from Gemini
    created_at       = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="assessments")


class ExercisePlan(Base):
    __tablename__ = "exercise_plans"

    id           = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id"),       nullable=False)
    exercise_id  = Column(String,  nullable=False)   # maps to exercises.json id field
    confidence   = Column(Float,   nullable=False)
    target_sets  = Column(Integer, nullable=False)
    target_reps  = Column(Integer, nullable=False)
    side         = Column(String,  default="both") # "left", "right", or "both"
    caution      = Column(String)
    priority     = Column(Integer, default=99)

    user = relationship("User", back_populates="exercise_plans")


class SessionLog(Base):
    __tablename__ = "session_logs"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id      = Column(String,  nullable=False)
    date             = Column(DateTime, default=datetime.utcnow)
    reps_completed   = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    form_errors      = Column(Text, default="{}")  # JSON string e.g. '{"knee_cave": 3}'

    user = relationship("User", back_populates="session_logs")


# ──────────────────────────── HELPERS ───────────────────────────────────────

def init_db():
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a SQLAlchemy session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
