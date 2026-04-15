# HNG Stage 0 - Name Classification API

A FastAPI-based REST API that integrates with the Genderize.io API to classify names and determine statistical confidence. Built as part of the HNG Internship Stage 0 Backend Track.

## Project Description
This API takes a name as a query parameter, fetches data from an external provider (Genderize.io), and processes the results. It renames data fields, calculates a confidence score based on specific business rules, and returns a structured JSON response.

## Features
- **External API Integration:** Connects with Genderize.io.
- **Data Transformation:** Renames `count` to `sample_size`.
- **Confidence Logic:** `is_confident` is true ONLY if `probability` >= 0.7 AND `sample_size` >= 100.
- **CORS Support:** Configured with `Access-Control-Allow-Origin: *` for cross-origin grading.
- **Error Handling:** Returns standardized JSON error messages for 400, 404, and 502 status codes.

## Tech Stack
- **Language:** Python 3.x
- **Framework:** FastAPI
- **Deployment:** Vercel

## API Specification

### GET /api/classify
**Endpoint:** `https://hng-stage0-kadiya.vercel.app/api/classify?name={name}`

**Successful Response (200 OK):**
```json
 {
   "status": "success",
   "data": {
     "name": "jamilu",
     "gender": "male",
     "probability": 0.98,
     "sample_size": 150,
     "is_confident": true,
     "processed_at": "2026-04-15T20:30:00Z"
   }
 }


**Error Responses:**

400 Bad Request: Missing or empty name parameter.

404 Not Found: No prediction available for the provided name.

502 Bad Gateway: External API/Upstream failure.

**Local Setup**


Clone the repository:

Bash
git clone [https://github.com/Kadiya01/hng_stage0.git](https://github.com/Kadiya01/hng_stage0.git)

Create a virtual environment:

Bash
python3 -m venv venv
source venv/bin/activate

Install requirements:

Bash
pip install -r requirements.txt

Run locally:

Bash
uvicorn api.index:app --reload
