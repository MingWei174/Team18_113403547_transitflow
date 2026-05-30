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
--  1. Auth & User Profile (Security Compliant + Loyalty Feature)
-- ============================================================
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
--  3. Schedules (Using JSONB for stops for easier array querying)
-- ============================================================
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

-- ============================================================
--  4. Bookings & Transactions
-- ============================================================
CREATE TABLE national_rail_bookings (
    booking_id             VARCHAR(20) PRIMARY KEY,
    user_id                VARCHAR(20) REFERENCES users(user_id),
    schedule_id            VARCHAR(20) REFERENCES national_rail_schedules(schedule_id),
    origin_station_id      VARCHAR(10) REFERENCES national_rail_stations(station_id),
    destination_station_id VARCHAR(10) REFERENCES national_rail_stations(station_id),
    travel_date            DATE NOT NULL,
    fare_class             VARCHAR(20) NOT NULL,
    ticket_type            VARCHAR(20) NOT NULL DEFAULT 'single',
    seat_id                VARCHAR(10),
    amount_usd             NUMERIC(5,2) NOT NULL,
    status                 VARCHAR(20) DEFAULT 'confirmed'
);

CREATE TABLE national_rail_seat_layouts (
    layout_id   VARCHAR(20) PRIMARY KEY,
    schedule_id VARCHAR(20) REFERENCES national_rail_schedules(schedule_id),
    coaches     JSONB NOT NULL
);

CREATE TABLE metro_travel_history (
    trip_id                VARCHAR(20) PRIMARY KEY,
    user_id                VARCHAR(20) REFERENCES users(user_id),
    schedule_id            VARCHAR(20) REFERENCES metro_schedules(schedule_id),
    origin_station_id      VARCHAR(10) REFERENCES metro_stations(station_id),
    destination_station_id VARCHAR(10) REFERENCES metro_stations(station_id),
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
    paid_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  VECTOR SCHEMA  (RAG / Help Desk) ??do not modify
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

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

