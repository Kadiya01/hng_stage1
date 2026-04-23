#import os
#import uuid6
#from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy.orm import sessionmaker
#from datetime import datetime, timezone
#from dotenv import load_dotenv

# Load environment variables
#load_dotenv(".env.local" if os.path.exists(".env.local") else ".env")

# Database connection
#DATABASE_URL = os.getenv("DATABASE_URL", "")
#if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
 #   DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

#engine = create_engine(DATABASE_URL)
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#Base = declarative_base()

# Database initializer
#def init_db():
 #   Base.metadata.drop_all(bind=engine)
  #  Base.metadata.create_all(bind=engine)
   # print("Database tables synchronized with Stage 2 requirements!")

#if __name__ == "__main__":
 #   init_db()
