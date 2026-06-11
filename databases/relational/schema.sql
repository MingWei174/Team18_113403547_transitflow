-- TASK 6 EXTENSION: Added loyalty_points column to users table (see TASK6.md)
-- ============================================================
--  TransitFlow PostgreSQL Schema
--  Seed data is loaded separately by: python skeleton/seed_postgres.py
--
--  TWO ROLES:
--    1. Relational  ??dual-network transit data you design below
--    2. Vector      ??policy documents for RAG (provided ??do not modify)
-- ============================================================

-- ============================================================
--  STUDENT TASK ??Design and create your relational tables here
--
--  Start from the mock data in train-mock-data/:
--    metro_stations.json, national_rail_stations.json
--    metro_schedules.json, national_rail_schedules.json
--    national_rail_seat_layouts.json
--    registered_users.json
--    bookings.json, metro_travel_history.json
--    payments.json, feedback.json
--
--  Think about:
--    - What tables do you need?
--    - What columns and data types?
--    - Which fields are primary keys? Which are foreign keys?
--    - What constraints make sense?
--
--  Apply your schema with:
--    docker-compose down -v && docker-compose up -d
-- ============================================================




-- ============================================================
-- Delete Strategy (Hard vs Soft Delete)
-- ============================================================
-- 我們採用 Hard Delete 策略並搭配 ON DELETE CASCADE 處理使用者相關資料
-- (如 user_passwords, security_questions, bookings)。這樣當刪除使用者時，
-- 其個資與訂單會一併徹底刪除，以符合 GDPR 規範與減少無效資料殘留。
-- 但對於系統營運的基礎設施 (如車站、時刻表)，我們則使用 ON DELETE RESTRICT，
-- 避免營運資料被意外刪除導致關聯訂單出錯。
-- ============================================================

-- ============================================================
--  1. Auth & User Profile (Security Compliant + Loyalty Feature)
-- ============================================================
CREATE TABLE users (
    user_id       VARCHAR(20) PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    first_name    VARCHAR(50) NOT NULL,
    surname       VARCHAR(50) NOT NULL,
    year_of_birth INT,
    -- TASK 6 EXTENSION: 常客忠誠度系統
    -- [WHY] 為什麼點數要存在 users 表而不是獨立的 points_ledger 表？
    -- 因為目前的商業邏輯只需要追蹤「當前點數總額」，而不需查詢詳細的「點數增減歷史明細」。
    -- 將 loyalty_points 設計為 INT 欄位並直接依附於 users 表，可有效減少 Join 負擔並提升查詢效率。
    loyalty_points INT DEFAULT 0
);

CREATE TABLE user_passwords (
    user_id       VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    salt          VARCHAR(255) NOT NULL,
    updated_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_questions (
    user_id            VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    secret_question    TEXT NOT NULL,
    secret_answer_hash VARCHAR(255) NOT NULL
);

-- ============================================================
--  2. Stations
-- ============================================================
CREATE TABLE metro_stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       TEXT NOT NULL,
    zone       INT
);

CREATE TABLE national_rail_stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       TEXT NOT NULL
);

-- ============================================================
--  3. Schedules & Stops (Fully Normalized)
-- ============================================================
CREATE TABLE metro_schedules (
    schedule_id VARCHAR(20) PRIMARY KEY,
    line        VARCHAR(5) NOT NULL,
    direction   VARCHAR(10)
);

CREATE TABLE metro_schedule_stops (
    schedule_id VARCHAR(20) REFERENCES metro_schedules(schedule_id) ON DELETE CASCADE,
    station_id  VARCHAR(10) REFERENCES metro_stations(station_id) ON DELETE RESTRICT,
    stop_order  INT NOT NULL,
    PRIMARY KEY (schedule_id, station_id)
);

CREATE TABLE national_rail_schedules (
    schedule_id      VARCHAR(20) PRIMARY KEY,
    route_name       TEXT,
    base_fare_usd    NUMERIC(5,2),
    per_stop_rate_usd NUMERIC(5,2),
    service_type     VARCHAR(20)
);

CREATE TABLE national_rail_schedule_stops (
    schedule_id VARCHAR(20) REFERENCES national_rail_schedules(schedule_id) ON DELETE CASCADE,
    station_id  VARCHAR(10) REFERENCES national_rail_stations(station_id) ON DELETE RESTRICT,
    stop_order  INT NOT NULL,
    PRIMARY KEY (schedule_id, station_id)
);

-- ============================================================
--  4. Bookings & Transactions
-- ============================================================
CREATE TABLE national_rail_bookings (
    booking_id             VARCHAR(20) PRIMARY KEY,
    user_id                VARCHAR(20) REFERENCES users(user_id) ON DELETE CASCADE,
    schedule_id            VARCHAR(20) REFERENCES national_rail_schedules(schedule_id) ON DELETE RESTRICT,
    origin_station_id      VARCHAR(10) REFERENCES national_rail_stations(station_id) ON DELETE RESTRICT,
    destination_station_id VARCHAR(10) REFERENCES national_rail_stations(station_id) ON DELETE RESTRICT,
    travel_date            DATE NOT NULL,
    fare_class             VARCHAR(20) NOT NULL,
    ticket_type            VARCHAR(20) NOT NULL DEFAULT 'single',
    seat_id                VARCHAR(10),
    amount_usd             NUMERIC(5,2) NOT NULL,
    status                 VARCHAR(20) DEFAULT 'confirmed'
);

CREATE TABLE national_rail_seat_layouts (
    layout_id   VARCHAR(20) PRIMARY KEY,
    schedule_id VARCHAR(20) REFERENCES national_rail_schedules(schedule_id) ON DELETE CASCADE,
    coaches     JSONB NOT NULL
);

CREATE TABLE metro_travel_history (
    trip_id                VARCHAR(20) PRIMARY KEY,
    user_id                VARCHAR(20) REFERENCES users(user_id) ON DELETE CASCADE,
    schedule_id            VARCHAR(20) REFERENCES metro_schedules(schedule_id) ON DELETE RESTRICT,
    origin_station_id      VARCHAR(10) REFERENCES metro_stations(station_id) ON DELETE RESTRICT,
    destination_station_id VARCHAR(10) REFERENCES metro_stations(station_id) ON DELETE RESTRICT,
    travel_date            DATE NOT NULL,
    ticket_type            VARCHAR(20),
    stops_travelled        INT,
    amount_usd             NUMERIC(5,2),
    status                 VARCHAR(20) DEFAULT 'completed'
);

CREATE TABLE payments (
    payment_id  VARCHAR(20) PRIMARY KEY,
    booking_id  VARCHAR(20) NOT NULL,
    amount_usd  NUMERIC(5,2) NOT NULL,
    method      VARCHAR(20),
    status      VARCHAR(20),
    paid_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE feedback (
    -- [WHY PK] 為什麼這裡的主鍵選擇使用 UUID？
    -- 在這個專案中，大部分的外部種子資料 (mock data) 都是給定 VARCHAR 格式 (例如 "user_id": "U001")，
    -- 因此為了相容性，我們先前在 users 與 schedules 等表使用了 VARCHAR。
    -- 但針對這個系統內部獨立生成的 `feedback` (回饋) 表格，我們不需要依賴舊有的字串格式，
    -- 所以採用 `UUID`。UUID 具備全域唯一性 (Globally Unique)，比起 VARCHAR 更能避免碰撞風險，
    -- 且比起 SERIAL 可以避免被猜測出系統總共收到多少回饋，提供更好的隱私保護。
    feedback_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    booking_id  VARCHAR(20) REFERENCES national_rail_bookings(booking_id) ON DELETE CASCADE,
    user_id     VARCHAR(20) REFERENCES users(user_id) ON DELETE CASCADE,
    rating      INT,
    comment     TEXT,
    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  VECTOR SCHEMA  (RAG / Help Desk) ??do not modify
-- ============================================================

CREATE TABLE IF NOT EXISTS policy_documents (
    id          SERIAL       PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    category    VARCHAR(50)  NOT NULL,  -- 'refund', 'booking', 'conduct'
    content     TEXT         NOT NULL,
    -- 768-dim  ??Ollama nomic-embed-text (default)
    -- 3072-dim ??Gemini gemini-embedding-001
    -- If you switch LLM_PROVIDER to gemini, change to vector(3072) and reset the database.
    embedding   vector(768),
    source_file VARCHAR(200),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_policy_documents_embedding ON policy_documents USING hnsw (embedding vector_cosine_ops);

