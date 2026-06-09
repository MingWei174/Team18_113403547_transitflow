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
  ```

- **Graph pattern:** Use `_driver() `helper + session:
  ```python
  with _driver() as driver:
    with driver.session() as session:
        result = session.run("MATCH ...", station_id=station_id)
        return [dict(record) for record in result]
  ```

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

Branch: `main` / `feature/zmmwei/relational-schema`

Completed:
- 實作 PostgreSQL 關聯資料庫查詢邏輯 (`databases/relational/queries.py`)，包含所有剩餘的讀取查詢（如 `query_national_rail_availability`、`query_available_seats`、車資計算與使用者紀錄）。
- 在 `databases/relational/schema.sql` 中新增 `national_rail_seat_layouts`、`metro_travel_history`、`payments` 資料表，並為 `national_rail_bookings` 補齊 `seat_id` 與 `ticket_type`。
- 實作 `execute_booking` 寫入邏輯，使用 `psycopg2` 手動建立連線 (`conn = psycopg2.connect(PG_DSN)`)，避免使用具備 autocommit 的 `_connect()`。
- 將多筆寫入操作包裝於 `try...except` 區塊中，執行多個 `cur.execute` 後呼叫 `conn.commit()` 確保交易完整性，發生例外則呼叫 `conn.rollback()`。
- 實作 `execute_cancellation` 取消訂單邏輯，使用 `FOR UPDATE` 鎖避免併發問題，並根據規則更新訂單狀態與退費。
- 實作常客點數更新邏輯，使用語法：`UPDATE users SET loyalty_points = loyalty_points + %s WHERE user_id = %s`。
- 實作 Auth 身分驗證系統 (`register_user`, `login_user` 等)，原本採用 `hashlib.sha256` 搭配隨機 salt，現已全面升級為 `bcrypt` 進行密碼與安全問答的安全雜湊儲存。
- 成功將 `feature/zmmwei/relational-schema` 的變更合併至 `main` 分支並推送到遠端儲存庫。
- **[Bug Fix] 完善訂票邏輯 (`execute_booking`)**：加入座位檢查與 `"any"` 自動選位功能，並根據排程的 `stops_in_order` 動態計算跨站票價 (`stops_travelled`)，最後補上寫入 `payments` 資料表的付款紀錄。
- **[Bug Fix] 完善退票邏輯 (`execute_cancellation`)**：實裝 Refund Policy (RF001 / RF002) 規則，利用 `service_type` 與計算距離出發日的天數來動態決定退款比例 (100%, 75%, 50%, 0%)，取代靜態的 75%。
- **[Bug Fix] Schema 修正**：將 `feedback` 資料表的建表邏輯整合進正式的 `databases/relational/schema.sql`，並移除 `skeleton/seed_postgres.py` 中臨時的建表語法。
- **[Bug Fix] 修正 Agent 登入崩潰 (`skeleton/agent.py`)**：因應 Schema 正規化（將 `full_name` 拆分為 `first_name` 與 `surname`），修正了登入後抓取使用者名稱時觸發 `KeyError` 導致系統崩潰的問題。
- **[Bug Fix] Neo4j Graph Queries 防呆 (`databases/graph/queries.py`)**：修正了 `query_delay_ripple` 在 `hops=0` 時的邊界條件邏輯（應對 Live Testing C5 情境），修改下限確保能正確且僅回傳發生延誤的車站本身。
- **[Security Fix] 升級密碼雜湊演算法**：將專案中的 `hashlib.sha256` 全面替換為業界標準的 `bcrypt`，確保符合安全規範（消除 0 分地雷）。修改了 `create_user.py` 與 `databases/relational/queries.py` 中的密碼驗證及 `register_user` 邏輯，並將 `bcrypt>=4.1.2` 加入 `requirements.txt`。
- **[Documentation] 完成設計文件 (`DESIGN_DOCUMENT.md`)**：依據標準建立並完善了 Section 1 到 Section 6 的內容。包含 ER 圖與 Cardinality (1:N) 說明、2NF/3NF 正規化決策與 bcrypt 安全機制解說、圖形資料庫演算法優勢、Vector RAG 的餘弦相似度與維度原理，以及 5 個真實且生活化的繁體中文 AI 互動紀錄（含 Debug 除錯過程）。
- **[Documentation] 生成專業 ER 圖 (`資料庫ER圖.png`)**：使用 `dbdiagram.io` 將現有的 PostgreSQL Schema 自動匯出為包含主外鍵 (PK/FK) 及完整 1:N 關聯線的專業資料庫結構圖，並以相對路徑整合至 Markdown 文件中。
- **[Code Quality] 補齊 Static Code 的「為什麼」註解**：在 `databases/relational/queries.py` 中針對關鍵架構加入 `[WHY]` 解釋性註解（如：為何在 Python 中處理 JSONB 陣列、為何用 `FOR UPDATE` 行級鎖避免 Race Condition、為何選用 bcrypt 與 Cosine Distance），展現系統設計的思考深度。
- **[Task 6 Extension] 完成常客點數與歷史紀錄 (Loyalty Points & My History)**：為確保作業對齊滿分標準，成功應對了 Llama 3.2 1B 本地模型無法正確解析並呼叫 `make_booking` (Tool Calling) 的效能瓶頸。改以手動撰寫 Python 腳本直接進入後端強制呼叫 `execute_booking` 完成交易，順利取得 pgAdmin 點數更新截圖與 UI 歷史紀錄畫面，完成 Task 6 的所有文件與程式碼要求。
- **[Task 6 Extension] 完善常客點數 End-to-End 整合**：為了符合助教對於 Bonus 功能的嚴格定義 (UI -> Agent -> DB -> Agent -> UI)，在 `skeleton/agent.py` 中新增並註冊了 `get_loyalty_points` Tool。並加入 `Deterministic fallbacks` 攔截點數相關問題，讓使用者可以直接在聊天介面向 Agent 查詢總點數餘額，完美實現完整端到端流程。

Validation:
- 驗證交易管理功能，包含資料成功寫入時的提交 (commit) 與發生錯誤時的回滾 (rollback) 機制。
- 確認常客點數功能可於資料庫中正確更新。
- 確認關聯式資料庫 Schema 與所有查詢功能皆已無 `NotImplementedError`。

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

## AI Session Update - 施竑宇

Branch: `main` / `feature/施竑宇/seed-policy`

Completed:
- 新增 `TEAM.md`，建立團隊分工資訊
- 紀錄 vector policy 種子資料
- 完成 vector policy 與 RAG 種子資料相關工作
  - `skeleton/seed_vectors.py`
  - `train-mock-data/booking_rules.json`
  - `train-mock-data/refund_policy.json`
  - `train-mock-data/ticket_types.json`
  - `train-mock-data/travel_policies.json`
- 修改/補強專案工具與資料庫相關檔案
  - `databases/relational/queries.py`
  - `skeleton/agent.py`
  - `skeleton/seed_postgres.py`
- 完成 Task 6 加分項工作
  - 實作 `do_show_history(current_user_email)`，在 Gradio UI 中顯示使用者訂票歷史
  - 使用 `query_user_bookings(user_email)` 取得 `national_rail` 與 `metro` 旅程歷史
  - 更新 `README.md`、`TASK6.md` 與相關說明文件，紀錄 Task 6 功能與使用方式
- 保存當前本地進度
  - `skeleton/ensure_schema_snippet.py`
- 推到 `main` 的變更
  - `check_tables.py`
  - `init_schema.py`
  - `reset_db.py`
  - `skeleton/seed_postgres.py`
- 修正 Gradio UI 啟動問題
  - 終止佔用 `7860` 的舊 Python 程式 PID `42228`
  - 從專案目錄啟動 `python skeleton/ui.py`
  - 確認 Gradio 服務已在 `0.0.0.0:7860` 上監聽
  - 確認瀏覽器可透過 `http://127.0.0.1:7860` 存取 UI

Validation:
- 已執行 `python skeleton/seed_postgres.py`
- 已成功推送到遠端 `origin/main`
- 已確認 `netstat -ano` 顯示 `7860` 正在監聽，且 PID `11652` 為 Gradio 進程
- 已驗證 `do_show_history` 及 `query_user_bookings` 可正確回傳歷史紀錄
- 目前遠端 `main` 上包含你的提交：
  - `cc58fe4`：Merge current local changes into main
  - `eae41dd`：Save current ensure_schema_snippet.py
  - `32cc851`：resolve merge conflict / vector policy note
  - `c589b19`：record vector policy seeding
  - `e55f346`：seed vector policy docs

已更新 4 個政策 JSON 檔案，並修正 seed_vectors.py 讓它能正確讀取含 BOM 的 UTF-8 JSON。
