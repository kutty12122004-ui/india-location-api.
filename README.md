# 🇮🇳 India Location SaaS API
**A high-performance, B2B-ready Geographic Data Service providing standardized access to India's administrative hierarchy.**

## 🚀 Overview
This project transforms a raw dataset of over **580,000 villages** into a production-grade SaaS API. It features high-speed fuzzy search, multi-tenant API key validation, and real-time usage tracking.

* **Live API Link:** [https://india-location-api-1.onrender.com](https://india-location-api-1.onrender.com)
* **Interactive API Docs:** [https://india-location-api-1.onrender.com/docs](https://india-location-api-1.onrender.com/docs)

---

## ✨ Key Features
* **Sub-10ms Search Performance:** Utilizes PostgreSQL `pg_trgm` (Trigram) GIN indexing to search 5.8 Lakh records nearly instantaneously.
* **SaaS Metering System:** Real-time request logging and quota enforcement per API key.
* **Standardized Data:** Cleaned and normalized hierarchy (State → District → Village).
* **Security:** Header-based API Authentication (`api-key`).

---

## 🛠 Tech Stack
| Component | Technology |
| :--- | :--- |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL (Neon Serverless) |
| **Indexing** | Trigram GIN Index (`gin_trgm_ops`) |
| **Infrastructure** | Render (Compute), GitHub (CI/CD) |

---

## 📡 API Endpoints

### 1. High-Speed Search (Autocomplete Ready)
`GET /search?q={query}`  
**Example:** `/search?q=Ami`  
*Uses GIN indexing to find villages and districts. Includes `usage_stats` in the response to show remaining quota.*

### 2. Administrative Lists
* `GET /states`: Returns all 36 States and Union Territories.
* `GET /districts/{state_id}`: Returns all districts for a specific state.

---

## 🔑 Authentication & SaaS Logic
To access protected endpoints, include your API key in the request header:
* **Header Name:** `api-key`
* **Demo Key:** `capstone_demo_2024`

### **How Metering Works:**
The API validates the key against the `api_users` table in Neon, increments the usage count, and enforces limits (returning `429 Too Many Requests` if the quota is exceeded).

---

## 📈 Performance
* **Village Fuzzy Search (580k+ records):** ~2.07 ms execution time.
* **Infrastructure:** Serverless compute with auto-scaling capabilities.

---
**Capstone Project - 2024**
