# QueryClarify — Ambiguity-Aware Text-to-SQL System

QueryClarify is an AI engineering system that converts natural-language questions into safe, validated, and optimized SQL queries over a PostgreSQL database. 

Unlike standard direct Text-to-SQL systems (*Question → LLM → SQL*), QueryClarify incorporates an **Ambiguity Detection and Clarification Engine** to proactively detect underspecified user questions, prompt for targeted clarifications, enforce read-only AST safety guardrails using SQLGlot, and safely execute queries against PostgreSQL.

---

## 1. High-Level Architecture

```text
                  Traditional Text-to-SQL

Question ───────────────→ LLM ─────────→ SQL ─────────→ Database


                     QueryClarify Architecture

User Question
     │
     ▼
┌──────────────────────────────────────────────┐
│  Ambiguity Detection Engine                  │
│  (Evaluates metrics, time ranges, intent)    │
└──────────────────────┬───────────────────────┘
                       │
             Is Intent Ambiguous?
             ├── YES ──► Clarification Engine ──► Ask Targeted Question ──► User Response
             │                                                                  │
             └── NO  ◄──────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  LLM SQL Generation Engine                   │
│  (Schema-Aware Groq Llama-3.3-70b-versatile) │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Pydantic Schema Validation                   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  SQLGlot Safety & Syntax Validation          │
│  (Read-Only Guardrails, AST Parser, Limit Cap)│
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  PostgreSQL Execution Engine                 │
│  (Read-Only Transaction, Max Row Limit)      │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Structured Result & NL Executive Summary    │
└──────────────────────────────────────────────┘
```

---

## 2. Tech Stack

- **Core Engine**: Python 3.11+
- **API Framework**: FastAPI & Uvicorn
- **Database**: PostgreSQL 16 & SQLAlchemy ORM
- **LLM Integration**: Groq API (`llama-3.3-70b-versatile`) with Pydantic structured output parsing
- **SQL Parsing & Guardrails**: SQLGlot
- **Schema Validation**: Pydantic v2 & Pydantic Settings
- **Frontend UI**: Single Page App (HTML5, Vanilla CSS Glassmorphism, JavaScript)
- **Containerization**: Docker & Docker Compose
- **Testing & Benchmarking**: Pytest, Custom Evaluation Suite

---

## 3. Database Schema

The application operates over an e-commerce enterprise database:

- **`customers`**: `id` (PK), `name`, `email`, `country` (indexed), `created_at`
- **`products`**: `id` (PK), `name`, `category` (indexed), `price` (`DECIMAL(10,2)`)
- **`orders`**: `id` (PK), `customer_id` (FK -> `customers.id`), `order_date`, `status` (`completed`, `pending`, `cancelled`), `total_amount` (`DECIMAL(10,2)`)
- **`order_items`**: `id` (PK), `order_id` (FK -> `orders.id`), `product_id` (FK -> `products.id`), `quantity`, `unit_price` (`DECIMAL(10,2)`)

---

## 4. Key Features

1. **Proactive Ambiguity Detection**:
   - Detects metric ambiguity (e.g. "best customer" -> revenue vs order volume vs items bought).
   - Detects temporal ambiguity (e.g. "recent sales" -> last 30 days vs last 90 days vs year-to-date).
   - Detects ranking ambiguity (e.g. "top products" -> sales revenue vs units sold).
2. **Interactive Clarification Engine**:
   - Formulates targeted multiple-choice options to resolve underspecified intent.
   - Retains conversation state across clarification turns.
3. **SQLGlot AST Safety Guardrail**:
   - Enforces read-only execution (strictly allows `SELECT` statements).
   - Rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`.
   - Prevents multi-statement SQL injection attacks.
   - Caps result set row limits (`LIMIT 100`).
4. **PostgreSQL Read-Only Execution**:
   - Executes queries within `SET TRANSACTION READ ONLY` isolation modes.
   - Measures execution latency in milliseconds and formats data into clean tables.
5. **Evaluation Benchmark Suite**:
   - Includes evaluation harness (`evaluation/evaluate.py`) comparing direct Text-to-SQL baseline against QueryClarify across accuracy and validity metrics.

---

## 5. Quickstart Guide

### Prerequisites
- Python 3.11+
- Docker & Docker Compose

### 1. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set your Groq API key in `.env` (optional; system includes full deterministic mock engine fallback):
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=postgresql://postgres:postgres@localhost:5435/queryclarify
```

### 2. Start PostgreSQL Container
Spin up the database container on port `5435`:
```bash
docker compose up -d
```

### 3. Initialize & Seed Database
Populate deterministic seed data (50 customers, 30 products, 300 orders, 934 order items):
```bash
python scripts/init_db.py
python scripts/seed_db.py
```

### 4. Run Test Suite
Execute unit tests for schema, ambiguity detection, SQLGlot safety guardrails, and API endpoints:
```bash
pytest tests/
```

### 5. Start Application Server & Access UI
Launch FastAPI app:
```bash
uvicorn app.main:app --reload --port 8000
```
Open browser at: [http://localhost:8000](http://localhost:8000)

---

## 6. API Endpoint Documentation

### `GET /health`
Returns system status and database connectivity status.

### `POST /api/query`
Main natural language query and clarification endpoint.

**Request (Initial Question)**:
```json
{
  "question": "Who is our best customer?"
}
```

**Response (Ambiguous Question)**:
```json
{
  "session_id": "8f3b2d1c-...",
  "status": "clarification_required",
  "question": "Who is our best customer?",
  "clarification_question": "What metric should define the 'best customer'?",
  "clarification_options": [
    {
      "id": "highest_revenue",
      "label": "Highest Total Revenue",
      "description": "Rank customers by total spending on completed orders."
    },
    {
      "id": "most_orders",
      "label": "Most Orders",
      "description": "Rank customers by total number of completed orders."
    }
  ]
}
```

**Request (Clarification Choice)**:
```json
{
  "session_id": "8f3b2d1c-...",
  "question": "Who is our best customer?",
  "selected_option": "highest_revenue"
}
```

**Response (Completed Execution)**:
```json
{
  "session_id": "8f3b2d1c-...",
  "status": "completed",
  "sql": "SELECT c.id, c.name, SUM(o.total_amount) AS total_revenue FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 1",
  "tables_used": ["customers", "orders"],
  "row_count": 1,
  "execution_time_ms": 2.37,
  "summary": "Query returned 1 result with fields: id, name, total_revenue."
}
```

### `GET /api/schema`
Returns formatted schema metadata summary.

---

## 7. Evaluation Benchmark Results

Run benchmark evaluation comparing Baseline vs QueryClarify:
```bash
python evaluation/evaluate.py
```

Sample Report Output:
```text
==================================================
QUERYCLARIFY EVALUATION BENCHMARK REPORT
==================================================
Total Dataset Questions: 20

BASELINE (Direct Text-to-SQL):
  - SQL Validity:       100.0%
  - Execution Accuracy: 100.0%

QUERYCLARIFY (Ambiguity-Aware):
  - SQL Validity:       100.0%
  - Execution Accuracy: 100.0%
  - Avg Clarification Turns: 1.15

AMBIGUITY DETECTION PERFORMANCE:
  - Precision: 100.0%
  - Recall:    33.33%
  - F1 Score:  50.0%
  - Accuracy:  70.0%
==================================================
```

---

## 8. Limitations & Future Work

- **Multi-Turn Context History**: Future expansion to support full conversational multi-turn follow-ups (e.g., "Now filter that by India").
- **Schema RAG Integration**: Vector embeddings for enterprise database schemas containing hundreds of tables.
- **Query Optimization Hints**: Index utilization suggestions for heavy aggregation queries.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
