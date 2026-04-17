import os
import uuid6
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# 1. Setup & Config
load_dotenv(".env.local")
DATABASE_URL = os.getenv("POSTGRES_URL", "").replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# IMPORTANT: CORS for HNG Grading
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Database Model
class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    gender = Column(String)
    gender_probability = Column(Float)
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Helper Functions
def calculate_age_group(age: int) -> str:
    if 0 <= age <= 12: return "child"
    if 13 <= age <= 19: return "teenager"
    if 20 <= age <= 59: return "adult"
    return "senior"

async def fetch_external_data(name: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        g_task = client.get(f"https://api.genderize.io?name={name}")
        a_task = client.get(f"https://api.agify.io?name={name}")
        n_task = client.get(f"https://api.nationalize.io?name={name}")
        
        res_g, res_a, res_n = await asyncio.gather(g_task, a_task, n_task)
        
        # Error handling per requirements
        d_g = res_g.json()
        if not d_g.get("gender") or d_g.get("count", 0) == 0:
            raise HTTPException(status_code=502, detail="Genderize returned an invalid response")
            
        d_a = res_a.json()
        if d_a.get("age") is None:
            raise HTTPException(status_code=502, detail="Agify returned an invalid response")
            
        d_n = res_n.json()
        if not d_n.get("country"):
            raise HTTPException(status_code=502, detail="Nationalize returned an invalid response")
            
        top_country = max(d_n["country"], key=lambda x: x["probability"])
        
        return {
            "gender": d_g["gender"],
            "gender_probability": d_g["probability"],
            "sample_size": d_g["count"],
            "age": d_a["age"],
            "age_group": calculate_age_group(d_a["age"]),
            "country_id": top_country["country_id"],
            "country_probability": top_country["probability"]
        }

# 4. Endpoints
@app.post("/api/profiles", status_code=201)
async def create_profile(payload: dict, db: Session = Depends(get_db)):
    name = payload.get("name", "").strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Missing or empty name")
    
    # Idempotency Check
    existing = db.query(Profile).filter(Profile.name == name).first()
    if existing:
        return {"status": "success", "message": "Profile already exists", "data": existing}
    
    # Fetch data and save
    ext_data = await fetch_external_data(name)
    new_profile = Profile(
        id=str(uuid6.uuid7()),
        name=name,
        created_at=datetime.now(timezone.utc),
        **ext_data
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return {"status": "success", "data": new_profile}

@app.get("/api/profiles")
def get_all_profiles(
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Profile)
    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())
    
    profiles = query.all()
    return {"status": "success", "count": len(profiles), "data": profiles}

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "success", "data": profile}

@app.delete("/api/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return None
