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