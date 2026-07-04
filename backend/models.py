from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    auth_provider = Column(String, default="email")  # email or google
    google_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    applications = relationship("Application", back_populates="candidate")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String, nullable=True)
    location = Column(String, nullable=True)
    job_type = Column(String, default="Full-time")
    skills_required = Column(Text, nullable=True)
    experience_required = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_filename = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, selected, rejected
    match_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
