from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import requests

app = FastAPI()

# Requirement: CORS header Access-Control-Allow-Origin: *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/api/classify")
def classify_name(name: str = Query(None)):
    # 1. Validation: Missing or empty name
    if not name or name.strip() == "":
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Missing or empty name parameter"})

    # 2. External API Call
    try:
        external_response = requests.get(f"https://api.genderize.io?name={name}", timeout=5)
        external_response.raise_for_status()
        res_data = external_response.json()
    except Exception:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Upstream server failure"})

    # 3. Handle Genderize Edge Cases (null gender or 0 count)
    gender = res_data.get("gender")
    sample_size = res_data.get("count", 0)
    probability = res_data.get("probability", 0)

    if gender is None or sample_size == 0:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "No prediction available for the provided name"})

    # 4. Confidence Logic: probability >= 0.7 AND sample_size >= 100
    is_confident = probability >= 0.7 and sample_size >= 100

    # 5. Success Response
    return {
        "status": "success",
        "data": {
            "name": res_data.get("name"),
            "gender": gender,
            "probability": probability,
            "sample_size": sample_size,
            "is_confident": is_confident,
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }

# Custom error handler to match the required HNG error format
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return Response(
        content=str(exc.detail).replace("'", '"'), 
        status_code=exc.status_code, 
        media_type="application/json"
    )
