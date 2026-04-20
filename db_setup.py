import os
import uuid
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from dotenv import load_dotenv

# 1. Load the variables from your local env file
load_dotenv(".env.local")

#load_dotenv(".env.local")
# Add these temporary lines:
print(f"Current Directory: {os.getcwd()}")
print(f"Database URL from Env: {os.getenv('POSTGRES_URL')}")


# 2. Database Connection Setup
DATABASE_URL = os.getenv("POSTGRES_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. The Updated Profile Model (HNG Stage 2 Requirements)
class Profile(Base):
    __tablename__ = "profiles"
    
    # Primary Key - Requirement: UUID v7
    id = Column(String, primary_key=True, index=True) 
    
    # Person's Details - Requirement: UNIQUE Name
    name = Column(String, unique=True, index=True, nullable=False)
    gender = Column(String)
    gender_probability = Column(Float)
    
    # Age Details
    age = Column(Integer)
    age_group = Column(String) # child, teenager, adult, senior
    
    # Country Details - Requirement: ISO code (2 chars) + Full Name
    country_id = Column(String(2)) 
    country_name = Column(String)
    country_probability = Column(Float)
    
    # Timestamp - Requirement: UTC ISO 8601
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# 4. Database Initializer
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database tables synchronized with Stage 2 requirements!")

if __name__ == "__main__":
    init_db()