# HNG Stage 1: Profile Management API

A FastAPI-based RESTful API that predicts and stores user demographic data (gender, age, and nationality) using three external APIs. This project implements data persistence with Postgres and focuses on performance through asynchronous programming.

## Features
- **Data Persistence:** Uses SQLAlchemy and Vercel Postgres.
- **Asynchronous Execution:** Calls three external APIs (Genderize, Agify, Nationalize) simultaneously using `httpx` and `asyncio.gather`.
- **Idempotency:** Checks if a name already exists in the database to prevent duplicate API calls.
- **Filtering:** Search through stored profiles by gender, country, or age group.
- **UUID v7:** Uses time-sortable unique identifiers for all records.

## Tech Stack
- **Framework:** FastAPI
- **Database:** PostgreSQL (Vercel/Neon)
- **ORM:** SQLAlchemy
- **Environment:** Kali Linux / Vercel

## Endpoints

### 1. Create Profile
- **Method:** `POST`
- **Path:** `/api/profiles`
- **Body:** `{"name": "ella"}`
- **Success (201):** Returns the predicted demographic data and saved ID.

### 2. Get All Profiles
- **Method:** `GET`
- **Path:** `/api/profiles`
- **Query Params:** `gender`, `country_id`, `age_group` (e.g., `?gender=female`)

### 3. Get Single Profile
- **Method:** `GET`
- **Path:** `/api/profiles/{id}`

### 4. Delete Profile
- **Method:** `DELETE`
- **Path:** `/api/profiles/{id}`

## Setup & Local Development

1. **Clone the repository:**
      ```bash
   git clone github.com/Kadiya01
   cd hng_stage0

2. **Setup Virtual Environment:**
      ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

3. **Environment Variables:**
   Create a .env.local with your POSTGRES_URL

4. **Run Server:**
      ```bash 
   uvicorn api.index:app --reload