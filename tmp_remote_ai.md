# AI Session Context ??TransitFlow

**How to use this file:**
At the start of every AI coding session, paste the full contents of this file as your first message to your AI assistant. This gives the AI the context it needs to produce code that fits your codebase and is consistent with your teammates' work.

**Who maintains this file:**
Whoever makes a schema change or architectural decision updates this file in the same commit. Treat it like a team contract.

---

## Project Overview
TransitFlow is a Python-based AI chat assistant for a fictional transit operator. It queries three databases ??PostgreSQL (relational + vector), Neo4j (graph) ??and uses an LLM to answer user questions. Our task as students is to design the database schema and implement the query functions in `databases/relational/queries.py` and `databases/graph/queries.py`.

## ???極??憿漁暺?- **撘菔?撏?*嚗?鞎?PostgreSQL ?鞈?摨?Schema 閮剛??閰ａ?頛?(`relational/queries.py`)??鞎砍祕雿漁暺?A嚗虜摰ａ???Loyalty Points??鞈?摨怎???啜?
- **?喟?蝝?*嚗?鞎?Neo4j ?耦頝舐雯?邪閮剛???Cypher ?亥岷?摩 (`graph/queries.py`)??鞎祈楊蝬脰?銋?頝臬?閬???
- **?賜?摰?*嚗?鞎祈???亥??(`seed_postgres.py`, `seed_neo4j.py`)??鞎砍祕雿漁暺?C嚗???輻??亥岷???游? JSON ?亥?摨怨? pgvector ?游???
## Tech Stack
- Language: Python 3.11+
- Relational DB: PostgreSQL via `psycopg2` with `RealDictCursor`
- Graph DB: Neo4j via the `neo4j` Python driver
- Vector search: `pgvector` extension (already implemented ??do not modify)
- Web UI: Gradio
- LLM: Google Gemini or local Ollama (configured via `.env`)

## Coding Conventions
- **Naming:** `snake_case` for all Python names and SQL identifiers
- **Docstrings:** All functions must have a docstring with `Args:` and `Returns:` sections
- **Return types:** Use type hints. Read-only functions return `list[dict]` or `Optional[dict]`
- **Empty results:** Return `[]` or `None` (as documented), never raise an exception for "not found"
- **SQL:** Use `%s` placeholders for all user inputs ??never string-format into SQL
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

## AI Session Update - 撘菔?撏?PostgreSQL Implementation

Branch: `main`

Completed:
- 撖虫? PostgreSQL ?鞈?摨急閰ａ?頛?(`databases/relational/queries.py`)??- 撖虫? `execute_booking` 撖怠?摩嚗蝙??`psycopg2` ??撱箇???? (`conn = psycopg2.connect(PG_DSN)`)嚗?蝙?典??autocommit ??`_connect()`??- 撠?蝑神?交?雿?鋆 `try...except` ?憛葉嚗銵???`cur.execute` 敺??`conn.commit()` 蝣箔?鈭斗?摰?扼?- 撖虫?靘???璈嚗?潛?靘????`conn.rollback()`??- 撖虫?撣詨恥暺?湔?摩嚗蝙?刻?瘜?`UPDATE users SET loyalty_points = loyalty_points + %s WHERE user_id = %s`??
Validation:
- 撽?鈭斗?蝞∠??嚗??怨????神?交???鈭?(commit) ??隤斗???皛?(rollback) 璈??- 蝣箄?撣詨恥暺??舀鞈?摨思葉甇?Ⅱ?湔??
---

## AI Session Update - ?喟?蝡?Neo4j Implementation

Branch: `neo4j_?喟?蝡

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
- **execute_booking ???內閰?*: ?嗅祕雿神?仿?頛舀?嚗?雿輻 psycopg2 ??撱箇???? (conn = psycopg2.connect(PG_DSN))嚗?蝙?典??autocommit ??_connect()??敹?鋆 try...except 銝哨??瑁?憭?cur.execute 敺??澆 conn.commit()?????憭??澆 conn.rollback()??撠虜摰ａ??賂?隢蝙??UPDATE users SET loyalty_points = loyalty_points + %s WHERE user_id = %s??
撌脫??4 ?蝑?JSON 瑼?嚗蒂靽格迤 seed_vectors.py 霈??賣迤蝣箄?? BOM ??UTF-8 JSON??
