import os
import time
import secrets
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel, EmailStr

app = FastAPI(title="India Location API")

# Aggressive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI, pool_pre_ping=True)

@app.on_event("startup")
def startup_event():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_users (
                user_id SERIAL PRIMARY KEY,
                organization_name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                api_key VARCHAR(100) UNIQUE,
                plan_type VARCHAR(50) DEFAULT 'free',
                request_limit INTEGER DEFAULT 1000,
                current_usage INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            );
            INSERT INTO api_users (organization_name, email, api_key, request_limit)
            VALUES ('Demo User', 'demo@test.com', 'capstone_demo_2024', 5000)
            ON CONFLICT DO NOTHING;
        """))
        conn.commit()

@app.get("/")
def read_root():
    return {"message": "API is Live", "docs": "/docs"}

@app.get("/states")
def get_states(api_key: str = Header(None, alias="api-key")):
    if api_key != "capstone_demo_2024":
        raise HTTPException(status_code=401, detail="Invalid Key")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM states LIMIT 50")).mappings().all()
    return {"states": [dict(r) for r in res]}
