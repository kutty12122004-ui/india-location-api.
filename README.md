# India Geographic Hierarchy API

A high-performance API providing access to States, Districts, and Villages of India.

## Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (Neon Cloud)
- **Deployment:** Render
- **Data Volume:** 580,000+ Villages

## Live API Link
https://india-location-api-y5tw.onrender.com

## Endpoints
- `GET /states`: Returns all states.
- `GET /districts/{state_id}`: Returns districts for a specific state.
- `GET /villages/{district_id}`: Returns all villages in a district.
