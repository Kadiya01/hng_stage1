# HNG Stage 2 - Intelligence Query Engine Backend

A high-performance demographic data API built with **FastAPI** and **PostgreSQL**, featuring advanced filtering, sorting, pagination, and natural language search capabilities.

## Overview

This API provides a complete query engine for demographic profiles with:
- ✅ Advanced filtering on multiple dimensions
- ✅ Flexible sorting options
- ✅ Cursor-based pagination
- ✅ Natural language query parsing
- ✅ CORS support for cross-origin requests

## Database Schema

All profiles follow this exact structure:

| Field | Type | Notes |
|-------|------|-------|
| `id` | VARCHAR | UUID v7, Primary Key |
| `name` | VARCHAR | Full name, UNIQUE, indexed |
| `gender` | VARCHAR | "male" or "female" |
| `gender_probability` | FLOAT | Confidence score (0-1) |
| `age` | INT | Exact age |
| `age_group` | VARCHAR | child, teenager, adult, senior |
| `country_id` | VARCHAR(2) | ISO country code |
| `country_name` | VARCHAR | Full country name |
| `country_probability` | FLOAT | Confidence score (0-1) |
| `created_at` | TIMESTAMP | UTC ISO 8601 |

## API Endpoints

### 1. Get All Profiles (with Filtering, Sorting, Pagination)

**Endpoint:** `GET /api/profiles`

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `gender` | string | Filter by gender | `male`, `female` |
| `age_group` | string | Filter by age group | `child`, `teenager`, `adult`, `senior` |
| `country_id` | string | ISO country code (2 chars) | `NG`, `KE`, `ZA` |
| `min_age` | integer | Minimum age (inclusive) | `25` |
| `max_age` | integer | Maximum age (inclusive) | `40` |
| `min_gender_probability` | float | Min gender confidence (0-1) | `0.85` |
| `min_country_probability` | float | Min country confidence (0-1) | `0.80` |
| `sort_by` | string | Sort field | `age`, `created_at`, `gender_probability` |
| `order` | string | Sort order | `asc`, `desc` (default: `asc`) |
| `page` | integer | Page number (1-indexed) | `1` (default) |
| `limit` | integer | Results per page | `10` (default, max: 50) |

**Example Request:**
```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

**Success Response (200):**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 156,
  "data": [
    {
      "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
      "name": "emmanuel",
      "gender": "male",
      "gender_probability": 0.99,
      "age": 34,
      "age_group": "adult",
      "country_id": "NG",
      "country_name": "Nigeria",
      "country_probability": 0.85,
      "created_at": "2026-04-01T12:00:00Z"
    }
  ]
}
```

**Combining Filters:**
- All parameters are combined with AND logic
- A profile must match ALL specified conditions to be returned
- If no filters are specified, returns all profiles

---

### 2. Natural Language Search (Core Feature)

**Endpoint:** `GET /api/profiles/search`

**Query Parameters:**

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `q` | string | Natural language query | Yes |
| `page` | integer | Page number (1-indexed) | No |
| `limit` | integer | Results per page (max: 50) | No |

**Example Queries:**

| Query | Translates To |
|-------|---------------|
| `young males from nigeria` | gender=male + min_age=16 + max_age=24 + country_id=NG |
| `females above 30` | gender=female + min_age=30 |
| `people from kenya` | country_id=KE |
| `adult males from cameroon` | gender=male + age_group=adult + country_id=CM |
| `male and female teenagers above 17` | age_group=teenager + min_age=17 |
| `adults from south africa` | age_group=adult + country_id=ZA |

**Example Request:**
```
GET /api/profiles/search?q=young+males+from+nigeria&page=1&limit=10
```

**Success Response (200):**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 42,
  "data": [...]
}
```

**Error Response (400) - Unable to parse query:**
```json
{
  "status": "error",
  "message": "Unable to interpret query"
}
```

---

## Natural Language Parsing Logic

### Supported Keywords

#### Gender Keywords
- **Male:** "male", "man", "men", "boy"
- **Female:** "female", "woman", "women", "girl"

#### Age Group Keywords
- **Child:** "child", "children"
- **Teenager:** "teenager", "teen", "adolescent"
- **Adult:** "adult", "grown-up"
- **Senior:** "senior", "elderly", "old"

#### Age Range Keywords
- **Young:** ages 16-24 (default range)
- **Old:** ages 60+ (minimum)
- **Numeric ranges:** "25-35", "20 to 40"
- **Comparative:** "above 30", "over 25", "below 18", "under 65"

#### Country Keywords
All African countries are supported by ISO code mapping:
- `Nigeria` → `NG`
- `Kenya` → `KE`
- `Ghana` → `GH`
- `South Africa` → `ZA`
- `Uganda` → `UG`
- `Cameroon` → `CM`
- `Tanzania` → `TZ`
- ...and 30+ more African countries

### Parsing Rules

1. **Case-insensitive**: "MALE", "Male", "male" all work
2. **Order-independent**: "males young" ≈ "young males"
3. **Flexible spacing**: Handles extra spaces and punctuation
4. **Multiple filters**: Combines all detected filters with AND logic
5. **Age ranges**: Detects patterns like "25-35" or "above 30"
6. **Smart defaults**: 
   - "young" → 16-24 years old
   - "adult" + age specified → overrides default mapping

### Parsing Examples

```
Input: "young males from nigeria"
Parsing:
  - "young" → min_age=16, max_age=24
  - "male" → gender=male
  - "nigeria" → country_id=NG
Output: gender=male&min_age=16&max_age=24&country_id=NG

Input: "females above 30 from kenya"
Parsing:
  - "female" → gender=female
  - "above 30" → min_age=30
  - "kenya" → country_id=KE
Output: gender=female&min_age=30&country_id=KE

Input: "teenager from south africa"
Parsing:
  - "teenager" → age_group=teenager
  - "south africa" → country_id=ZA
Output: age_group=teenager&country_id=ZA
```

---

## Limitations & Edge Cases

### What the Parser Handles
✅ Gender filtering  
✅ Age groups and age ranges  
✅ Country identification  
✅ Combination of multiple filters  
✅ Flexible word order and spacing  

### What the Parser Does NOT Handle
❌ Probability filters (`min_gender_probability`, `min_country_probability`)  
❌ Complex logical operators (OR, NOT)  
❌ Negation ("not male")  
❌ Relative terms ("younger than", "taller than")  
❌ Typos and misspellings  
❌ Non-African countries  
❌ Queries in languages other than English  

### Edge Cases & Limitations

| Edge Case | Behavior |
|-----------|----------|
| Empty query | Returns 400 error |
| No matches detected | Returns 400 error with "Unable to interpret query" |
| Both age_group and age range specified | Uses both filters (AND logic) |
| Conflicting gender terms | Uses the last one detected |
| Unknown country name | Ignores it, may still find other filters |
| Age > 150 or < 0 | Applied as-is (no validation) |
| Special characters | Stripped or ignored |
| Multiple country names | Uses the first one found |

---

## Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (Neon recommended)
- FastAPI, SQLAlchemy, HTTPx

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/your-repo/hng_stage1.git
   cd hng_stage1
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your POSTGRES_URL
   ```

3. **Initialize database:**
   ```bash
   python db_setup.py
   python seed.py
   ```

4. **Run server:**
   ```bash
   uvicorn api.index:app --reload
   ```

### Deployment (Vercel)

1. **Add environment variables:**
   - Go to Vercel → Project Settings → Environment Variables
   - Add `POSTGRES_URL` with your Neon connection string

2. **Deploy:**
   ```bash
   git push origin stage-2
   ```

---

## Testing

### Test Filtering
```bash
curl "https://your-api.vercel.app/api/profiles?gender=male&country_id=NG&min_age=25"
```

### Test Sorting & Pagination
```bash
curl "https://your-api.vercel.app/api/profiles?sort_by=age&order=desc&page=1&limit=5"
```

### Test Natural Language Search
```bash
curl "https://your-api.vercel.app/api/profiles/search?q=young+males+from+nigeria"
```

---

## Performance Considerations

- ✅ Indexed columns: `name`, `country_id`, `created_at`, `age`
- ✅ Batch inserts for seeding (1000+ profiles/batch)
- ✅ Single-query filtering (no N+1)
- ✅ Limit max pagination to 50 per page
- ✅ No full-table scans (all queries filtered)

---

## Data Model

Profiles are seeded from `seed_profiles.json` containing 2026 demographic records with:
- Realistic names from multiple African countries
- Gender predictions with confidence scores
- Age estimates with confidence scores
- Country origin predictions with confidence scores

Duplicates are automatically skipped during seeding (idempotent).

---

## Error Handling

All errors follow this structure:

```json
{
  "status": "error",
  "message": "<error description>"
}
```

| Status Code | Scenario |
|-------------|----------|
| 400 | Invalid or missing required parameters |
| 404 | Profile not found |
| 422 | Invalid parameter type or value |
| 500 | Server error |
| 502 | External API error (genderize.io, agify.io, nationalize.io) |

---

## CORS & Deployment

- ✅ CORS enabled for all origins
- ✅ Vercel-optimized (serverless-ready)
- ✅ PostgreSQL connection pooling enabled
- ✅ Automatic table creation on startup

---

## Author

Built for HNG Stage 2 Backend Assessment | April 2026

---

## Requirements Met

✅ **Filtering:** gender, age_group, country_id, min_age, max_age, min_gender_probability, min_country_probability  
✅ **Sorting:** age, created_at, gender_probability (asc/desc)  
✅ **Pagination:** page, limit (max 50)  
✅ **Natural Language Parsing:** Rule-based, no AI/LLM  
✅ **Response Format:** {status, page, limit, total, data}  
✅ **Database Schema:** Exact Stage 2 requirements  
✅ **Data Seeding:** 2026 profiles, idempotent  
✅ **CORS:** All origins allowed  
✅ **Error Handling:** Standard error structure  
✅ **README:** Complete documentation  


3. **Environment Variables:**
   Create a .env.local with your POSTGRES_URL

4. **Run Server:**
      ```bash 
   uvicorn api.index:app --reload