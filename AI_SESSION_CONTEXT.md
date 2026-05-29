# AI Session Context — TransitFlow

**How to use this file:**
At the start of every AI coding session, paste the full contents of this file as your first message to your AI assistant. This gives the AI the context it needs to produce code that fits your codebase and is consistent with your teammates' work.

**Who maintains this file:**
Whoever makes a schema change or architectural decision updates this file in the same commit. Treat it like a team contract.

---

## Project Overview
TransitFlow is a Python-based AI chat assistant for a fictional transit operator. It queries three databases — PostgreSQL (relational + vector), Neo4j (graph) — and uses an LLM to answer user questions. Our task as students is to design the database schema and implement the query functions in `databases/relational/queries.py` and `databases/graph/queries.py`.

## 團隊分工與專題亮點
- **張茗崴**：負責 PostgreSQL 關聯資料庫 Schema 設計與查詢邏輯 (`relational/queries.py`)。負責實作【亮點 A：常客點數 Loyalty Points】的資料庫狀態更新。

- **吳絃紘**：負責 Neo4j 圖形路網拓樸設計與 Cypher 查詢邏輯 (`graph/queries.py`)。負責跨網轉乘與路徑規劃。

- **施紘宇**：負責資料匯入腳本 (`seed_postgres.py`, `seed_neo4j.py`)。負責實作【亮點 C：隱藏版政策查詢】，擴充 JSON 知識庫與 pgvector 整合。

## Tech Stack
- Language: Python 3.11+
- Relational DB: PostgreSQL via `psycopg2` with `RealDictCursor`
- Graph DB: Neo4j via the `neo4j` Python driver
- Vector search: `pgvector` extension (already implemented — do not modify)
- Web UI: Gradio
- LLM: Google Gemini or local Ollama (configured via `.env`)

## Coding Conventions
- **Naming:** `snake_case` for all Python names and SQL identifiers
- **Docstrings:** All functions must have a docstring with `Args:` and `Returns:` sections
- **Return types:** Use type hints. Read-only functions return `list[dict]` or `Optional[dict]`
- **Empty results:** Return `[]` or `None` (as documented), never raise an exception for "not found"
- **SQL:** Use `%s` placeholders for all user inputs — never string-format into SQL
- **Relational pattern:** Use `_connect()` helper + `psycopg2.extras.RealDictCursor`:
  ```python
  with _connect() as conn:
      with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
          cur.execute("SELECT ...", (param,))
          return [dict(row) for row in cur.fetchall()]

- **Graph pattern:** Use `_driver() `helper + session:
  ```python
  with _driver() as driver:
    with driver.session() as session:
        result = session.run("MATCH ...", station_id=station_id)
        return [dict(record) for record in result]

- **Agreed Relational Schema (PostgreSQL)**
-- 1. Auth & User Profile (Security Compliant + Loyalty Feature)
CREATE TABLE users (
    user_id       VARCHAR(20) PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    first_name    VARCHAR(50) NOT NULL,
    surname       VARCHAR(50) NOT NULL,
    year_of_birth INT,
    loyalty_points INT DEFAULT 0
);

CREATE TABLE user_passwords (
    user_id       VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    salt          VARCHAR(255) NOT NULL,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_questions (
    user_id            VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    secret_question    TEXT NOT NULL,
    secret_answer_hash VARCHAR(255) NOT NULL
);

-- 2. Stations
CREATE TABLE metro_stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       TEXT NOT NULL,
    zone       INT
);

CREATE TABLE national_rail_stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       TEXT NOT NULL
);

-- 3. Schedules (Using JSONB for stops for easier array querying)
CREATE TABLE metro_schedules (
    schedule_id VARCHAR(20) PRIMARY KEY,
    line        VARCHAR(5) NOT NULL,
    direction   VARCHAR(10),
    stops       JSONB NOT NULL -- e.g., [{"station_id": "MS01", "arrival_time": "08:00"}]
);

CREATE TABLE national_rail_schedules (
    schedule_id      VARCHAR(20) PRIMARY KEY,
    route_name       TEXT,
    base_fare_usd    NUMERIC(5,2),
    per_stop_rate_usd NUMERIC(5,2),
    stops            JSONB NOT NULL 
);

-- 4. Bookings & Transactions
CREATE TABLE national_rail_bookings (
    booking_id             VARCHAR(20) PRIMARY KEY,
    user_id                VARCHAR(20) REFERENCES users(user_id),
    schedule_id            VARCHAR(20) REFERENCES national_rail_schedules(schedule_id),
    origin_station_id      VARCHAR(10) REFERENCES national_rail_stations(station_id),
    destination_station_id VARCHAR(10) REFERENCES national_rail_stations(station_id),
    travel_date            DATE NOT NULL,
    fare_class             VARCHAR(20) NOT NULL,
    amount_usd             NUMERIC(5,2) NOT NULL,
    status                 VARCHAR(20) DEFAULT 'confirmed'
);

- **Agreed Graph Schema (Neo4j)**
Node labels:
- Station (Base label for all stations)
- MetroStation (Sub-label)
- NationalRailStation (Sub-label)

Relationship types:
- METRO_LINK (connects MetroStation to MetroStation)
- RAIL_LINK (connects NationalRailStation to NationalRailStation)
- INTERCHANGE_TO (connects MetroStation to NationalRailStation and vice versa)

Key properties:
- Nodes: station_id, name, is_closed (Boolean, default: false - for disruption routing)
- Relationships: line, travel_time_min, distance

- **Function Signatures We Are Implementing**

These are fixed contracts. AI-generated code must match these signatures exactly.

Relational (databases/relational/queries.py)
# Read-only
def query_national_rail_availability(origin_id: str, destination_id: str, travel_date: Optional[str] = None) -> list[dict]: ...
def query_national_rail_fare(schedule_id: str, fare_class: str, stops_travelled: int) -> Optional[dict]: ...
def query_metro_schedules(origin_id: str, destination_id: str) -> list[dict]: ...
def query_metro_fare(schedule_id: str, stops_travelled: int) -> Optional[dict]: ...
def query_available_seats(schedule_id: str, travel_date: str, fare_class: str) -> list[dict]: ...
def query_user_profile(user_email: str) -> Optional[dict]: ...
def query_user_bookings(user_email: str) -> dict: ...  # returns {"national_rail": [...], "metro": [...]}
def query_payment_info(booking_id: str) -> Optional[dict]: ...

# Write operations
def execute_booking(user_id, schedule_id, origin_station_id, destination_station_id, travel_date, fare_class, seat_id, ticket_type="single") -> tuple[bool, dict | str]: ...
def execute_cancellation(booking_id: str, user_id: str) -> tuple[bool, dict | str]: ...

# Auth
def register_user(email, first_name, surname, year_of_birth, password, secret_question, secret_answer) -> tuple[bool, str]: ...
def login_user(email: str, password: str) -> Optional[dict]: ...
def get_user_secret_question(email: str) -> Optional[str]: ...
def verify_secret_answer(email: str, answer: str) -> bool: ...
def update_password(email: str, new_password: str) -> bool: ...

- **Graph (databases/graph/queries.py)**

def query_shortest_route(origin_id: str, destination_id: str, network: str = "auto") -> dict: ...
def query_cheapest_route(origin_id: str, destination_id: str, network: str = "auto", fare_class: str = "standard") -> dict: ...
def query_alternative_routes(origin_id, destination_id, avoid_station_id, network="auto", max_routes=3) -> list[list[dict]]: ...
def query_interchange_path(origin_id: str, destination_id: str) -> dict: ...
def query_delay_ripple(delayed_station_id: str, hops: int = 2) -> list[dict]: ...
def query_station_connections(station_id: str) -> list[dict]: ...

- **Team Decisions Log**
[x] Schema design: Users, Passwords, and Secret Questions are decoupled for security. JSONB is used for schedule stops to avoid complex table joins.

[x] Graph schema: Unified Station label with is_closed property for alternative routing simulations. Added specific link types (METRO_LINK, RAIL_LINK).

[x] Added vector policy embedding support: updated `train-mock-data` JSON policy documents, fixed `skeleton/seed_vectors.py` to read BOM-safe JSON, and successfully seeded the policy documents into PostgreSQL.

## AI Session Update - 張茗崴 PostgreSQL Implementation

Branch: `main`

Completed:
- 實作 PostgreSQL 關聯資料庫查詢邏輯 (`databases/relational/queries.py`)。
- 實作 `execute_booking` 寫入邏輯，使用 `psycopg2` 手動建立連線 (`conn = psycopg2.connect(PG_DSN)`)，避免使用具備 autocommit 的 `_connect()`。
- 將多筆寫入操作包裝於 `try...except` 區塊中，執行多個 `cur.execute` 後呼叫 `conn.commit()` 確保交易完整性。
- 實作例外處理機制，若發生例外則呼叫 `conn.rollback()`。
- 實作常客點數更新邏輯，使用語法：`UPDATE users SET loyalty_points = loyalty_points + %s WHERE user_id = %s`。

Validation:
- 驗證交易管理功能，包含資料成功寫入時的提交 (commit) 與發生錯誤時的回滾 (rollback) 機制。
- 確認常客點數功能可於資料庫中正確更新。

---

## AI Session Update - 吳絃竑 Neo4j Implementation

Branch: `neo4j_吳絃竑`

Completed:
- Implemented Neo4j graph seeding in `skeleton/seed_neo4j.py`.
- Created `Station`, `MetroStation`, and `NationalRailStation` nodes from mock JSON data.
- Created `METRO_LINK`, `RAIL_LINK`, and bidirectional `INTERCHANGE_TO` relationships.
- Added relationship properties: `line`, `travel_time_min`, `distance`, `standard_fare_usd`, and `first_fare_usd`.
- Implemented all required graph query functions in `databases/graph/queries.py`:
    - `query_shortest_route`
    - `query_cheapest_route`
    - `query_alternative_routes`
    - `query_interchange_path`
    - `query_delay_ripple`
    - `query_station_connections`

Validation:
- Ran `python -m py_compile` using the project `.venv` Python.
- Seeded Neo4j successfully after Docker Desktop was started.
- Ran smoke tests for shortest route, cheapest route, interchange routing, alternative routes, delay ripple, station connections, and not-found station cases.
- Confirmed the Neo4j portion has no remaining `TODO` or `NotImplementedError`.

Relational Query Implementation (PostgreSQL):
- **execute_booking 成功提示詞**: 當實作寫入邏輯時，請使用 psycopg2 手動建立連線 (conn = psycopg2.connect(PG_DSN))，避免使用具有 autocommit 的 _connect()。務必包裝在 try...except 中，執行多個 cur.execute 後再呼叫 conn.commit()。如果發生例外請呼叫 conn.rollback()。針對常客點數，請使用 UPDATE users SET loyalty_points = loyalty_points + %s WHERE user_id = %s。

已更新 4 個政策 JSON 檔案，並修正 seed_vectors.py 讓它能正確讀取含 BOM 的 UTF-8 JSON。
