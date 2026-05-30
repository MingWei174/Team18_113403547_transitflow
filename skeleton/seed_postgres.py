"""
Seed PostgreSQL with all TransitFlow mock data from train-mock-data/.

Usage:
    python skeleton/seed_postgres.py

Run AFTER docker-compose up -d.
You must first design and create your tables in databases/relational/schema.sql.
Safe to re-run: implement your inserts with ON CONFLICT DO NOTHING.
"""

import json
import os
import sys

import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extras import Json
import hashlib
import uuid

# ── resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR    = os.path.join(PROJECT_DIR, "train-mock-data")

sys.path.insert(0, PROJECT_DIR)
from skeleton import config as cfg


def load(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def connect():
    return psycopg2.connect(
        host=cfg.PG_HOST,
        port=cfg.PG_PORT,
        dbname=cfg.PG_DB,
        user=cfg.PG_USER,
        password=cfg.PG_PASSWORD,
    )


def insert_many(cur, table, columns, rows):
    """Bulk insert with ON CONFLICT DO NOTHING. Returns row count inserted."""
    if not rows:
        return 0
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT DO NOTHING"
    )
    execute_values(cur, sql, rows)
    return cur.rowcount


def ensure_schema(cur):
    """Create minimal tables if they do not exist so seeder can run safely."""
    cur.execute("""
    CREATE TABLE IF NOT EXISTS metro_stations (
        station_id VARCHAR(10) PRIMARY KEY,
        name TEXT NOT NULL,
        zone INT
    );

    CREATE TABLE IF NOT EXISTS national_rail_stations (
        station_id VARCHAR(10) PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS metro_schedules (
        schedule_id VARCHAR(20) PRIMARY KEY,
        line VARCHAR(5) NOT NULL,
        direction VARCHAR(10),
        stops JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS national_rail_schedules (
        schedule_id VARCHAR(20) PRIMARY KEY,
        route_name TEXT,
        base_fare_usd NUMERIC(5,2),
        per_stop_rate_usd NUMERIC(5,2),
        stops JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS national_rail_seat_layouts (
        layout_id VARCHAR(20) PRIMARY KEY,
        schedule_id VARCHAR(20),
        coaches JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(20) PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        first_name VARCHAR(50) NOT NULL,
        surname VARCHAR(50) NOT NULL,
        year_of_birth INT,
        loyalty_points INT DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS user_passwords (
        user_id VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        password_hash VARCHAR(255) NOT NULL,
        salt VARCHAR(255) NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS security_questions (
        user_id VARCHAR(20) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        secret_question TEXT NOT NULL,
        secret_answer_hash VARCHAR(255) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS national_rail_bookings (
        booking_id VARCHAR(20) PRIMARY KEY,
        user_id VARCHAR(20),
        schedule_id VARCHAR(20),
        origin_station_id VARCHAR(10),
        destination_station_id VARCHAR(10),
        travel_date DATE NOT NULL,
        fare_class VARCHAR(20) NOT NULL,
        ticket_type VARCHAR(20) NOT NULL DEFAULT 'single',
        seat_id VARCHAR(10),
        amount_usd NUMERIC(5,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'confirmed'
    );

    CREATE TABLE IF NOT EXISTS metro_travel_history (
        trip_id VARCHAR(20) PRIMARY KEY,
        user_id VARCHAR(20),
        schedule_id VARCHAR(20),
        origin_station_id VARCHAR(10),
        destination_station_id VARCHAR(10),
        travel_date DATE NOT NULL,
        ticket_type VARCHAR(20),
        stops_travelled INT,
        amount_usd NUMERIC(5,2),
        status VARCHAR(20) DEFAULT 'completed'
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id VARCHAR(20) PRIMARY KEY,
        booking_id VARCHAR(20) NOT NULL,
        amount_usd NUMERIC(5,2) NOT NULL,
        method VARCHAR(20),
        status VARCHAR(20),
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("Ensured minimal schema exists.")


# ── seeders ──────────────────────────────────────────────────────────────────

def seed_metro_stations(cur):
    data = load("metro_stations.json")
    # Each item in `data` is a dict — inspect the JSON to see available fields.
    rows = []
    for s in data:
        station_id = s.get("station_id")
        name = s.get("name")
        zone = s.get("zone") if s.get("zone") is not None else None
        rows.append((station_id, name, zone))
    inserted = insert_many(cur, "metro_stations", ["station_id", "name", "zone"], rows)
    print(f"Inserted metro_stations: {inserted}")


def seed_national_rail_stations(cur):
    data = load("national_rail_stations.json")
    rows = []
    for s in data:
        rows.append((s.get("station_id"), s.get("name")))
    inserted = insert_many(cur, "national_rail_stations", ["station_id", "name"], rows)
    print(f"Inserted national_rail_stations: {inserted}")


def seed_metro_schedules(cur):
    data = load("metro_schedules.json")
    rows = []
    for sch in data:
        schedule_id = sch.get("schedule_id")
        line = sch.get("line")
        direction = sch.get("direction")
        # store the rest of schedule as JSON in `stops` JSONB column
        stops = Json(sch)
        rows.append((schedule_id, line, direction, stops))
    inserted = insert_many(cur, "metro_schedules", ["schedule_id", "line", "direction", "stops"], rows)
    print(f"Inserted metro_schedules: {inserted}")


def seed_national_rail_schedules(cur):
    data = load("national_rail_schedules.json")
    rows = []
    for sch in data:
        schedule_id = sch.get("schedule_id")
        route_name = f"{sch.get('line')} {sch.get('direction', '')}".strip()
        # pick standard fares as base values
        fare_classes = sch.get("fare_classes", {})
        standard = fare_classes.get("standard", {})
        base_fare = standard.get("base_fare_usd")
        per_stop = standard.get("per_stop_rate_usd")
        stops = Json(sch)
        rows.append((schedule_id, route_name, base_fare, per_stop, stops))
    inserted = insert_many(cur, "national_rail_schedules", ["schedule_id", "route_name", "base_fare_usd", "per_stop_rate_usd", "stops"], rows)
    print(f"Inserted national_rail_schedules: {inserted}")


def seed_seat_layouts(cur):
    data = load("national_rail_seat_layouts.json")
    rows = []
    for layout in data:
        layout_id = layout.get("layout_id")
        schedule_id = layout.get("schedule_id")
        coaches = Json(layout.get("coaches"))
        rows.append((layout_id, schedule_id, coaches))
    inserted = insert_many(cur, "national_rail_seat_layouts", ["layout_id", "schedule_id", "coaches"], rows)
    print(f"Inserted national_rail_seat_layouts: {inserted}")


def seed_users(cur):
    data = load("registered_users.json")
    users_rows = []
    passwords_rows = []
    secq_rows = []
    for u in data:
        user_id = u.get("user_id")
        full = u.get("full_name", "")
        parts = full.split()
        first = parts[0] if parts else ""
        surname = " ".join(parts[1:]) if len(parts) > 1 else ""
        email = u.get("email")
        dob = u.get("date_of_birth")
        yob = None
        if dob:
            try:
                yob = int(dob.split("-")[0])
            except Exception:
                yob = None
        users_rows.append((user_id, email, first, surname, yob, 0))

        # password hashing (simple salted sha256 for seed)
        raw_pw = u.get("password", "")
        salt = uuid.uuid4().hex
        pw_hash = hashlib.sha256((salt + raw_pw).encode("utf-8")).hexdigest()
        passwords_rows.append((user_id, pw_hash, salt))

        # security question
        question = u.get("secret_question") or ""
        answer = u.get("secret_answer") or ""
        answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        secq_rows.append((user_id, question, answer_hash))

    inserted_u = insert_many(cur, "users", ["user_id", "email", "first_name", "surname", "year_of_birth", "loyalty_points"], users_rows)
    inserted_p = insert_many(cur, "user_passwords", ["user_id", "password_hash", "salt"], passwords_rows)
    inserted_s = insert_many(cur, "security_questions", ["user_id", "secret_question", "secret_answer_hash"], secq_rows)
    print(f"Inserted users: {inserted_u}, passwords: {inserted_p}, security_questions: {inserted_s}")


def seed_national_rail_bookings(cur):
    data = load("bookings.json")
    rows = []
    for b in data:
        rows.append((
            b.get("booking_id"),
            b.get("user_id"),
            b.get("schedule_id"),
            b.get("origin_station_id"),
            b.get("destination_station_id"),
            b.get("travel_date"),
            b.get("fare_class"),
            b.get("ticket_type") or "single",
            b.get("seat_id"),
            b.get("amount_usd"),
            b.get("status") or "confirmed",
        ))
    inserted = insert_many(cur, "national_rail_bookings", ["booking_id", "user_id", "schedule_id", "origin_station_id", "destination_station_id", "travel_date", "fare_class", "ticket_type", "seat_id", "amount_usd", "status"], rows)
    print(f"Inserted national_rail_bookings: {inserted}")


def seed_metro_travels(cur):
    data = load("metro_travel_history.json")
    rows = []
    for t in data:
        rows.append((
            t.get("trip_id"),
            t.get("user_id"),
            t.get("schedule_id"),
            t.get("origin_station_id"),
            t.get("destination_station_id"),
            t.get("travel_date"),
            t.get("ticket_type"),
            t.get("stops_travelled"),
            t.get("amount_usd"),
            t.get("status") or "completed",
        ))
    inserted = insert_many(cur, "metro_travel_history", ["trip_id", "user_id", "schedule_id", "origin_station_id", "destination_station_id", "travel_date", "ticket_type", "stops_travelled", "amount_usd", "status"], rows)
    print(f"Inserted metro_travel_history: {inserted}")


def seed_payments(cur):
    data = load("payments.json")
    rows = []
    for p in data:
        rows.append((
            p.get("payment_id"),
            p.get("booking_id"),
            p.get("amount_usd"),
            p.get("method"),
            p.get("status"),
            p.get("paid_at"),
        ))
    inserted = insert_many(cur, "payments", ["payment_id", "booking_id", "amount_usd", "method", "status", "paid_at"], rows)
    print(f"Inserted payments: {inserted}")


def seed_feedback(cur):
    data = load("feedback.json")
    # Create feedback table if students didn't add it to schema.sql
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id VARCHAR(20) PRIMARY KEY,
        booking_id VARCHAR(20),
        user_id VARCHAR(20),
        rating INT,
        comment TEXT,
        submitted_at TIMESTAMP
    )
    """)
    rows = []
    for f in data:
        rows.append((
            f.get("feedback_id"),
            f.get("booking_id"),
            f.get("user_id"),
            f.get("rating"),
            f.get("comment"),
            f.get("submitted_at"),
        ))
    inserted = insert_many(cur, "feedback", ["feedback_id", "booking_id", "user_id", "rating", "comment", "submitted_at"], rows)
    print(f"Inserted feedback: {inserted}")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to PostgreSQL...")
    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Seeding tables (dependency order):")
        # create minimal schema if missing to allow seeding to proceed
        ensure_schema(cur)
        # ensure schema changes are visible
        conn.commit()
        seed_metro_stations(cur)
        seed_national_rail_stations(cur)
        seed_metro_schedules(cur)
        seed_national_rail_schedules(cur)
        seed_seat_layouts(cur)
        seed_users(cur)
        seed_national_rail_bookings(cur)
        seed_metro_travels(cur)
        seed_payments(cur)
        seed_feedback(cur)
        conn.commit()
        print("\nAll done. Database seeded successfully.")
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
