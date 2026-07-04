from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
import hashlib
def simple_hash(p): return hashlib.sha256(p.encode()).hexdigest()
def simple_verify(p, h): return hashlib.sha256(p.encode()).hexdigest() == h
from pydantic import BaseModel, EmailStr
import os, shutil, json, re

from database import engine, get_db, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="AI Recruiter Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "ai-recruiter-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24



# ─── Seed Admin ───────────────────────────────────────────────────────────────
def seed_admin():
    db = next(get_db())
    existing = db.query(models.Admin).filter_by(email="kalpana150906@gmail.com").first()
    if not existing:
        admin = models.Admin(
            email="kalpana150906@gmail.com",
            hashed_password=simple_hash("kal@1524"),
            name="Kalpana",
            is_super_admin=True,
        )
        db.add(admin)
        db.commit()
    db.close()

seed_admin()

# ─── Auth Helpers ─────────────────────────────────────────────────────────────
def create_token(data: dict, role: str):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "role": role})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_admin(token: str, db: Session):
    payload = verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Not authenticated")
    admin = db.query(models.Admin).filter_by(email=payload.get("sub")).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin

def get_current_candidate(token: str, db: Session):
    payload = verify_token(token)
    if not payload or payload.get("role") != "candidate":
        raise HTTPException(status_code=401, detail="Not authenticated")
    candidate = db.query(models.Candidate).filter_by(email=payload.get("sub")).first()
    if not candidate:
        raise HTTPException(status_code=401, detail="Candidate not found")
    return candidate

# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class AdminLogin(BaseModel):
    email: str
    password: str

class CandidateSignup(BaseModel):
    name: str
    email: str
    password: str

class CandidateLogin(BaseModel):
    email: str
    password: str

class GoogleLogin(BaseModel):
    name: str
    email: str
    google_id: str

class JobCreate(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = "Full-time"
    skills_required: Optional[str] = None
    experience_required: Optional[str] = None

class AddAdmin(BaseModel):
    name: str
    email: str
    password: str

class UpdateApplicationStatus(BaseModel):
    status: str
    notes: Optional[str] = None

# ─── Simple Resume Parser ─────────────────────────────────────────────────────
def extract_text_from_file(file_path: str, filename: str) -> str:
    try:
        if filename.endswith(".txt"):
            with open(file_path, "r", errors="ignore") as f:
                return f.read()
        # For PDF/DOCX, return placeholder (would need pdfplumber/python-docx in prod)
        return f"Resume file: {filename} (binary content)"
    except:
        return ""

def extract_skills(text: str) -> list:
    common_skills = [
        "python","java","javascript","typescript","react","vue","angular","node",
        "fastapi","django","flask","sql","mysql","postgresql","mongodb","redis",
        "docker","kubernetes","aws","azure","gcp","git","ci/cd","machine learning",
        "deep learning","tensorflow","pytorch","nlp","data science","excel","power bi",
        "tableau","html","css","c++","c#","ruby","php","swift","kotlin","scala",
        "hadoop","spark","kafka","elasticsearch","linux","agile","scrum"
    ]
    found = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            found.append(skill.title())
    return list(set(found))

def compute_match_score(resume_text: str, job_description: str) -> float:
    if not resume_text or not job_description:
        return 0.0
    resume_skills = set(s.lower() for s in extract_skills(resume_text))
    job_skills = set(s.lower() for s in extract_skills(job_description))
    if not job_skills:
        return 50.0
    overlap = resume_skills & job_skills
    return round((len(overlap) / len(job_skills)) * 100, 1)

# ─── ADMIN AUTH ROUTES ────────────────────────────────────────────────────────
@app.post("/api/admin/login")
def admin_login(body: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter_by(email=body.email).first()
    if not admin or not simple_verify(body.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": admin.email}, "admin")
    return {"token": token, "name": admin.name, "email": admin.email, "is_super_admin": admin.is_super_admin}

@app.post("/api/admin/add-admin")
def add_admin(body: AddAdmin, token: str = Form(None), db: Session = Depends(get_db)):
    raise HTTPException(status_code=400, detail="Use JSON endpoint")

@app.post("/api/admin/add")
async def add_admin_json(body: AddAdmin, authorization: Optional[str] = None, db: Session = Depends(get_db)):
    return {"message": "Use header-based auth"}

@app.post("/api/admin/admins/add")
async def add_new_admin(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    auth_token: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = get_current_admin(auth_token, db)
    existing = db.query(models.Admin).filter_by(email=email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")
    new_admin = models.Admin(
        email=email,
        hashed_password=simple_hash(password),
        name=name,
        is_super_admin=False,
        created_by=admin.id
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"message": "Admin added", "id": new_admin.id}

@app.get("/api/admin/admins")
def list_admins(authorization: str, db: Session = Depends(get_db)):
    admin = get_current_admin(authorization, db)
    admins = db.query(models.Admin).all()
    return [{"id": a.id, "name": a.name, "email": a.email, "is_super_admin": a.is_super_admin, "created_at": str(a.created_at)} for a in admins]

# ─── CANDIDATE AUTH ROUTES ────────────────────────────────────────────────────
@app.post("/api/candidate/signup")
def candidate_signup(body: CandidateSignup, db: Session = Depends(get_db)):
    existing = db.query(models.Candidate).filter_by(email=body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    candidate = models.Candidate(
        name=body.name,
        email=body.email,
        hashed_password=simple_hash(body.password),
        auth_provider="email"
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    token = create_token({"sub": candidate.email}, "candidate")
    return {"token": token, "name": candidate.name, "email": candidate.email, "id": candidate.id}

@app.post("/api/candidate/login")
def candidate_login(body: CandidateLogin, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter_by(email=body.email).first()
    if not candidate or not candidate.hashed_password or not simple_verify(body.password, candidate.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": candidate.email}, "candidate")
    return {"token": token, "name": candidate.name, "email": candidate.email, "id": candidate.id}

@app.post("/api/candidate/google-login")
def candidate_google_login(body: GoogleLogin, db: Session = Depends(get_db)):
    existing = db.query(models.Candidate).filter_by(email=body.email).first()
    if existing:
        candidate = existing
    else:
        candidate = models.Candidate(
            name=body.name, email=body.email,
            google_id=body.google_id, auth_provider="google"
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    token = create_token({"sub": candidate.email}, "candidate")
    return {"token": token, "name": candidate.name, "email": candidate.email, "id": candidate.id}

# ─── JOB ROUTES ──────────────────────────────────────────────────────────────
@app.post("/api/jobs/create")
def create_job(
    title: str = Form(...),
    description: str = Form(...),
    department: str = Form(""),
    location: str = Form(""),
    job_type: str = Form("Full-time"),
    skills_required: str = Form(""),
    experience_required: str = Form(""),
    auth_token: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = get_current_admin(auth_token, db)
    job = models.Job(
        title=title, description=description, department=department,
        location=location, job_type=job_type, skills_required=skills_required,
        experience_required=experience_required, created_by=admin.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "Job created", "id": job.id}

@app.get("/api/jobs")
def list_jobs(active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(models.Job)
    if active_only:
        query = query.filter_by(is_active=True)
    jobs = query.order_by(models.Job.created_at.desc()).all()
    return [serialize_job(j) for j in jobs]

@app.get("/api/admin/jobs")
def admin_list_jobs(authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    jobs = db.query(models.Job).order_by(models.Job.created_at.desc()).all()
    return [serialize_job(j, with_count=True, db=db) for j in jobs]

def serialize_job(j, with_count=False, db=None):
    data = {
        "id": j.id, "title": j.title, "description": j.description,
        "department": j.department, "location": j.location, "job_type": j.job_type,
        "skills_required": j.skills_required, "experience_required": j.experience_required,
        "is_active": j.is_active, "created_at": str(j.created_at)
    }
    if with_count and db:
        data["application_count"] = db.query(models.Application).filter_by(job_id=j.id).count()
    return data

@app.delete("/api/admin/jobs/{job_id}")
def delete_job(job_id: int, authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    job = db.query(models.Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_active = False
    db.commit()
    return {"message": "Job deactivated"}

# ─── APPLICATION ROUTES ───────────────────────────────────────────────────────
@app.post("/api/applications/apply")
async def apply_for_job(
    job_id: int = Form(...),
    auth_token: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    candidate = get_current_candidate(auth_token, db)
    job = db.query(models.Job).filter_by(id=job_id, is_active=True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check duplicate
    existing = db.query(models.Application).filter_by(candidate_id=candidate.id, job_id=job_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied for this job")

    # Save resume
    ext = os.path.splitext(resume.filename)[1]
    safe_name = f"resume_{candidate.id}_{job_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    resume_text = extract_text_from_file(file_path, resume.filename)
    match_score = compute_match_score(resume_text, job.description)

    application = models.Application(
        candidate_id=candidate.id, job_id=job_id,
        resume_filename=resume.filename, resume_path=file_path,
        resume_text=resume_text, match_score=match_score, status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"message": "Application submitted", "id": application.id, "match_score": match_score}

@app.get("/api/candidate/applications")
def candidate_applications(authorization: str, db: Session = Depends(get_db)):
    candidate = get_current_candidate(authorization, db)
    apps = db.query(models.Application).filter_by(candidate_id=candidate.id).order_by(models.Application.applied_at.desc()).all()
    result = []
    for a in apps:
        job = db.query(models.Job).filter_by(id=a.job_id).first()
        result.append({
            "id": a.id, "job_id": a.job_id,
            "job_title": job.title if job else "Unknown",
            "department": job.department if job else "",
            "location": job.location if job else "",
            "status": a.status, "match_score": a.match_score,
            "applied_at": str(a.applied_at), "notes": a.notes
        })
    return result

@app.get("/api/admin/applications")
def admin_applications(authorization: str, job_id: Optional[int] = None, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    query = db.query(models.Application)
    if job_id:
        query = query.filter_by(job_id=job_id)
    apps = query.order_by(models.Application.applied_at.desc()).all()
    result = []
    for a in apps:
        candidate = db.query(models.Candidate).filter_by(id=a.candidate_id).first()
        job = db.query(models.Job).filter_by(id=a.job_id).first()
        result.append({
            "id": a.id, "candidate_id": a.candidate_id,
            "candidate_name": candidate.name if candidate else "Unknown",
            "candidate_email": candidate.email if candidate else "",
            "job_id": a.job_id, "job_title": job.title if job else "Unknown",
            "resume_filename": a.resume_filename, "match_score": a.match_score,
            "status": a.status, "notes": a.notes, "applied_at": str(a.applied_at)
        })
    return result

@app.put("/api/admin/applications/{app_id}/status")
def update_application_status(
    app_id: int,
    status: str = Form(...),
    notes: str = Form(""),
    auth_token: str = Form(...),
    db: Session = Depends(get_db)
):
    get_current_admin(auth_token, db)
    app = db.query(models.Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = status
    app.notes = notes
    app.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Status updated"}

@app.get("/api/admin/applications/{app_id}/resume")
def download_resume(app_id: int, authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    application = db.query(models.Application).filter_by(id=app_id).first()
    if not application or not application.resume_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not os.path.exists(application.resume_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(application.resume_path, filename=application.resume_filename)

# ─── DASHBOARD STATS ──────────────────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    total_candidates = db.query(models.Candidate).count()
    total_jobs = db.query(models.Job).filter_by(is_active=True).count()
    total_applications = db.query(models.Application).count()
    selected = db.query(models.Application).filter_by(status="selected").count()
    rejected = db.query(models.Application).filter_by(status="rejected").count()
    pending = db.query(models.Application).filter_by(status="pending").count()
    avg_score = db.query(models.Application).all()
    scores = [a.match_score for a in avg_score if a.match_score]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    return {
        "total_candidates": total_candidates,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "selected": selected,
        "rejected": rejected,
        "pending": pending,
        "avg_match_score": avg
    }

# ─── SKILL GAP & INTERVIEW ────────────────────────────────────────────────────
@app.get("/api/admin/skill-gap/{app_id}")
def skill_gap(app_id: int, authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    application = db.query(models.Application).filter_by(id=app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Not found")
    job = db.query(models.Job).filter_by(id=application.job_id).first()
    resume_skills = set(s.lower() for s in extract_skills(application.resume_text or ""))
    job_skills = set(s.lower() for s in extract_skills(job.description if job else ""))
    missing = list(job_skills - resume_skills)
    matching = list(job_skills & resume_skills)
    return {"missing_skills": missing, "matching_skills": matching, "match_score": application.match_score}

@app.get("/api/admin/interview-questions/{app_id}")
def interview_questions(app_id: int, authorization: str, db: Session = Depends(get_db)):
    get_current_admin(authorization, db)
    application = db.query(models.Application).filter_by(id=app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Not found")
    job = db.query(models.Job).filter_by(id=application.job_id).first()
    job_skills = extract_skills(job.description if job else "")
    questions = [
        f"Can you describe your experience with {skill}?" for skill in job_skills[:5]
    ] + [
        "Tell me about a challenging project you've worked on.",
        "How do you prioritize tasks when working under pressure?",
        "Describe a situation where you had to learn a new technology quickly.",
        "How do you handle disagreements with team members?",
        "What are your long-term career goals?"
    ]
    return {"questions": questions[:10]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
