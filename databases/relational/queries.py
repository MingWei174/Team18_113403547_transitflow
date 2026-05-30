"""
TransitFlow — PostgreSQL / Relational Database Layer
=====================================================
This module handles all queries to PostgreSQL.

TWO ROLES ARE SERVED HERE:
  1. Relational  → dual-network transit (metro + national rail),
                   availability, fares, bookings, seat selection
  2. Vector      → policy document similarity search (pgvector)

STUDENT TASK
------------
Design your schema in databases/relational/schema.sql, seed it with
skeleton/seed_postgres.py, then implement the query functions below.

Functions prefixed with `query_`  are read-only lookups called by the agent.
Functions prefixed with `execute_` are write operations (booking/cancellation).

The vector functions (query_policy_vector_search, store_policy_document)
are already implemented — do not modify them.
"""

from __future__ import annotations

import json
import random
import string
import hashlib
from datetime import datetime, timezone
from typing import Optional

import psycopg2  # pyrefly: ignore [missing-import]
import psycopg2.extras  # pyrefly: ignore [missing-import].extras

from skeleton.config import PG_DSN, VECTOR_TOP_K, VECTOR_SIMILARITY_THRESHOLD


def _connect():
    """Return a new psycopg2 connection with autocommit enabled."""
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    return conn


def _gen_booking_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK-{suffix}"


def _gen_payment_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PM-{suffix}"


# ── Example ───────────────────────────────────────────────────────────────────
# The block below shows the query pattern: open a cursor, run SQL, return rows.
# Use _connect() for read-only queries; for write operations use a manual
# connection with conn.commit() / conn.rollback() (see execute_booking below).

def example_query() -> dict:
    """Example: returns the name of the connected database."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT current_database() AS db;")
            return dict(cur.fetchone())

# ─────────────────────────────────────────────────────────────────────────────


# ── NATIONAL RAIL AVAILABILITY ────────────────────────────────────────────────

def query_national_rail_availability(
    origin_id: str,
    destination_id: str,
    travel_date: Optional[str] = None,
) -> list[dict]:
    """
    Return national rail schedules that serve both origin and destination stations
    in the correct order, along with seat occupancy for the requested travel date.
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM national_rail_schedules")
            all_schedules = cur.fetchall()
            
            results = []
            for row in all_schedules:
                sch = row["stops"]
                station_ids = sch.get("stops_in_order", [])
                
                if origin_id in station_ids and destination_id in station_ids:
                    orig_idx = station_ids.index(origin_id)
                    dest_idx = station_ids.index(destination_id)
                    if orig_idx < dest_idx:
                        schedule = dict(row)
                        
                        if travel_date:
                            cur.execute(
                                "SELECT count(*) FROM national_rail_bookings WHERE schedule_id = %s AND travel_date = %s AND status IN ('confirmed', 'completed')",
                                (schedule["schedule_id"], travel_date)
                            )
                            booked_seats = cur.fetchone()["count"]
                            
                            cur.execute("SELECT coaches FROM national_rail_seat_layouts WHERE schedule_id = %s", (schedule["schedule_id"],))
                            layout = cur.fetchone()
                            total_seats = 0
                            if layout and layout["coaches"]:
                                for coach in layout["coaches"]:
                                    total_seats += len(coach.get("seats", []))
                                    
                            schedule["total_seats"] = total_seats
                            schedule["booked_seats"] = booked_seats
                            schedule["available_seats"] = total_seats - booked_seats
                        
                        results.append(schedule)
            return results


def query_national_rail_fare(
    schedule_id: str,
    fare_class: str,
    stops_travelled: int,
) -> Optional[dict]:
    """
    Calculate the fare for a national rail journey.
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT base_fare_usd, per_stop_rate_usd FROM national_rail_schedules WHERE schedule_id = %s", (schedule_id,))
            schedule = cur.fetchone()
            if not schedule:
                return None
            
            base_fare = float(schedule["base_fare_usd"] or 50.00)
            per_stop = float(schedule["per_stop_rate_usd"] or 10.00)
            
            if fare_class.lower() == "first":
                base_fare *= 2
                per_stop *= 2
                
            total_fare = base_fare + (per_stop * stops_travelled)
            
            return {
                "fare_class": fare_class,
                "base_fare_usd": base_fare,
                "per_stop_rate_usd": per_stop,
                "total_fare_usd": total_fare
            }


# ── METRO SCHEDULES & FARE ────────────────────────────────────────────────────

def query_metro_schedules(origin_id: str, destination_id: str) -> list[dict]:
    """
    Return metro schedules that serve both origin and destination in the correct order.
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM metro_schedules")
            all_schedules = cur.fetchall()
            
            results = []
            for row in all_schedules:
                sch = row["stops"]
                station_ids = sch.get("stops_in_order", [])
                
                if origin_id in station_ids and destination_id in station_ids:
                    orig_idx = station_ids.index(origin_id)
                    dest_idx = station_ids.index(destination_id)
                    if orig_idx < dest_idx:
                        results.append(dict(row))
            return results


def query_metro_fare(schedule_id: str, stops_travelled: int) -> Optional[dict]:
    """
    Calculate the metro fare for a single-ticket journey.
    """
    base_fare = 0.80
    per_stop = 0.30
    total_fare = base_fare + (per_stop * stops_travelled)
    return {
        "base_fare_usd": base_fare,
        "per_stop_rate_usd": per_stop,
        "total_fare_usd": total_fare
    }


# ── SEAT SELECTION ────────────────────────────────────────────────────────────

def query_available_seats(
    schedule_id: str,
    travel_date: str,
    fare_class: str,
) -> list[dict]:
    """
    Return available seats for a national rail journey on a given date.
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT coaches FROM national_rail_seat_layouts WHERE schedule_id = %s", (schedule_id,))
            layout = cur.fetchone()
            if not layout or not layout["coaches"]:
                return []
                
            cur.execute(
                "SELECT seat_id FROM national_rail_bookings WHERE schedule_id = %s AND travel_date = %s AND status IN ('confirmed', 'completed')",
                (schedule_id, travel_date)
            )
            booked_seats = {row["seat_id"] for row in cur.fetchall() if row["seat_id"]}
            
            available_seats = []
            for coach in layout["coaches"]:
                if coach.get("fare_class", "").lower() == fare_class.lower():
                    for seat in coach.get("seats", []):
                        if seat["seat_id"] not in booked_seats:
                            available_seats.append({
                                "seat_id": seat["seat_id"],
                                "coach": coach.get("coach"),
                                "row": seat.get("row"),
                                "column": seat.get("column")
                            })
            return available_seats


def auto_select_adjacent_seats(available_seats: list[dict], count: int) -> list[str]:
    """
    Select `count` seats that are as close together as possible (same row preferred,
    then adjacent rows). Returns a list of seat_ids.

    Args:
        available_seats: output of query_available_seats()
        count:           number of seats needed
    """
    if not available_seats or count <= 0:
        return []
    if count >= len(available_seats):
        return [s["seat_id"] for s in available_seats[:count]]

    from collections import defaultdict
    rows: dict[int, list[dict]] = defaultdict(list)
    for seat in available_seats:
        rows[seat["row"]].append(seat)

    for row_seats in sorted(rows.values(), key=lambda s: s[0]["row"]):
        if len(row_seats) >= count:
            return [s["seat_id"] for s in row_seats[:count]]

    sorted_seats = sorted(available_seats, key=lambda s: (s["row"], s["column"]))
    return [s["seat_id"] for s in sorted_seats[:count]]


# ── USER & BOOKING QUERIES ────────────────────────────────────────────────────

def query_user_profile(user_email: str) -> Optional[dict]:
    """Return a user's profile by email."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT user_id, email, first_name, surname, year_of_birth, loyalty_points FROM users WHERE email = %s", (user_email,))
            return cur.fetchone()


def query_user_bookings(user_email: str) -> dict:
    """
    Return a user's combined booking history (national rail + metro).

    Returns:
        dict with keys 'national_rail' (list) and 'metro' (list)
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT user_id FROM users WHERE email = %s", (user_email,))
            user = cur.fetchone()
            if not user:
                return {"national_rail": [], "metro": []}
            
            user_id = user["user_id"]
            
            cur.execute("SELECT * FROM national_rail_bookings WHERE user_id = %s", (user_id,))
            nr_bookings = [dict(row) for row in cur.fetchall()]
            
            for booking in nr_bookings:
                booking["travel_date"] = str(booking["travel_date"])
                booking["amount_usd"] = float(booking["amount_usd"])
            
            cur.execute("SELECT * FROM metro_travel_history WHERE user_id = %s", (user_id,))
            metro_bookings = [dict(row) for row in cur.fetchall()]
            for trip in metro_bookings:
                trip["travel_date"] = str(trip["travel_date"])
                trip["amount_usd"] = float(trip["amount_usd"])
                
            return {"national_rail": nr_bookings, "metro": metro_bookings}


def query_payment_info(booking_id: str) -> Optional[dict]:
    """Return payment record for a booking or metro trip."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM payments WHERE booking_id = %s", (booking_id,))
            row = cur.fetchone()
            if row:
                row["amount_usd"] = float(row["amount_usd"])
                row["paid_at"] = str(row["paid_at"])
                return dict(row)
            return None


# ── TRANSACTIONAL OPERATIONS ──────────────────────────────────────────────────

def execute_booking(
    user_id: str,
    schedule_id: str,
    origin_station_id: str,
    destination_station_id: str,
    travel_date: str,
    fare_class: str,
    seat_id: str,
    ticket_type: str = "single",
) -> tuple[bool, dict | str]:
    """
    Create a national rail booking for a logged-in user.

    Args:
        user_id:                e.g. "RU01" — must match the logged-in user
        schedule_id:            e.g. "NR_SCH01"
        origin_station_id:      e.g. "NR01"
        destination_station_id: e.g. "NR05"
        travel_date:            e.g. "2025-06-01"
        fare_class:             "standard" or "first"
        seat_id:                e.g. "B05" (or "any" to auto-assign)
        ticket_type:            "single" (default) or "return"

    Returns:
        (True, booking_dict)   on success
        (False, error_message) on failure
    """
    booking_id = _gen_booking_id()
    
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT base_fare_usd FROM national_rail_schedules WHERE schedule_id = %s", (schedule_id,))
            schedule = cur.fetchone()
            if not schedule:
                return False, "Schedule not found."
            
            amount_usd = schedule["base_fare_usd"] or 50.00
            if fare_class == "first":
                amount_usd *= 2
                
            cur.execute("""
                INSERT INTO national_rail_bookings 
                (booking_id, user_id, schedule_id, origin_station_id, destination_station_id, travel_date, fare_class, ticket_type, seat_id, amount_usd, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed')
            """, (booking_id, user_id, schedule_id, origin_station_id, destination_station_id, travel_date, fare_class, ticket_type, seat_id, amount_usd))
            
            points_earned = int(amount_usd)
            cur.execute("""
                UPDATE users 
                SET loyalty_points = loyalty_points + %s 
                WHERE user_id = %s
            """, (points_earned, user_id))
            
        conn.commit()
        return True, {
            "booking_id": booking_id,
            "status": "confirmed",
            "amount_usd": float(amount_usd),
            "loyalty_points_earned": points_earned
        }
    except Exception as e:
        conn.rollback()
        return False, f"Booking failed: {str(e)}"
    finally:
        conn.close()


def execute_cancellation(booking_id: str, user_id: str) -> tuple[bool, dict | str]:
    """
    Cancel a national rail booking owned by the given user.

    Calculates the refund amount according to the booking's service type:
      - Normal service: RF001 windows (100% / 75% / 50% / 0%)
      - Express service: RF002 windows (100% / 50% / 0%)
    """
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM national_rail_bookings WHERE booking_id = %s AND user_id = %s FOR UPDATE", (booking_id, user_id))
            booking = cur.fetchone()
            if not booking:
                return False, "Booking not found or does not belong to user."
                
            if booking["status"] in ("cancelled", "refunded"):
                return False, "Booking is already cancelled."
                
            refund_amount_usd = float(booking["amount_usd"]) * 0.75 # Default logic for mock
            
            cur.execute("UPDATE national_rail_bookings SET status = 'cancelled' WHERE booking_id = %s", (booking_id,))
            cur.execute("UPDATE payments SET status = 'refunded' WHERE booking_id = %s", (booking_id,))
            
        conn.commit()
        return True, {
            "booking_id": booking_id,
            "status": "cancelled",
            "refund_amount_usd": refund_amount_usd,
            "policy_note": "75% refunded per standard policy"
        }
    except Exception as e:
        conn.rollback()
        return False, f"Cancellation failed: {str(e)}"
    finally:
        conn.close()


# ── AUTHENTICATION QUERIES ────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()


def register_user(
    email: str,
    first_name: str,
    surname: str,
    year_of_birth: int,
    password: str,
    secret_question: str,
    secret_answer: str,
) -> tuple[bool, str]:
    """Register a new user."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return False, "Email already registered."
                
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            user_id = f"RU-{suffix}"
            salt = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            
            password_hash = _hash_password(password, salt)
            secret_answer_hash = _hash_password(secret_answer.lower(), salt)
            
            cur.execute("""
                INSERT INTO users (user_id, email, first_name, surname, year_of_birth, loyalty_points)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (user_id, email, first_name, surname, year_of_birth))
            
            cur.execute("""
                INSERT INTO user_passwords (user_id, password_hash, salt)
                VALUES (%s, %s, %s)
            """, (user_id, password_hash, salt))
            
            cur.execute("""
                INSERT INTO security_questions (user_id, secret_question, secret_answer_hash)
                VALUES (%s, %s, %s)
            """, (user_id, secret_question, secret_answer_hash))
            
        conn.commit()
        return True, user_id
    except Exception as e:
        conn.rollback()
        return False, f"Registration failed: {str(e)}"
    finally:
        conn.close()


def login_user(email: str, password: str) -> Optional[dict]:
    """Verify credentials."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.email, u.first_name, u.surname, u.year_of_birth, u.loyalty_points, p.password_hash, p.salt
                FROM users u
                JOIN user_passwords p ON u.user_id = p.user_id
                WHERE u.email = %s
            """, (email,))
            user = cur.fetchone()
            if not user:
                return None
                
            expected_hash = _hash_password(password, user["salt"])
            if user["password_hash"] == expected_hash:
                return {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "first_name": user["first_name"],
                    "surname": user["surname"],
                    "full_name": f"{user['first_name']} {user['surname']}",
                    "year_of_birth": user["year_of_birth"],
                    "loyalty_points": user["loyalty_points"],
                    "is_active": True
                }
            return None


def get_user_secret_question(email: str) -> Optional[str]:
    """Return the secret question for a registered email, or None if not found."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sq.secret_question
                FROM users u
                JOIN security_questions sq ON u.user_id = sq.user_id
                WHERE u.email = %s
            """, (email,))
            row = cur.fetchone()
            return row[0] if row else None


def verify_secret_answer(email: str, answer: str) -> bool:
    """Return True if the provided answer matches the stored secret answer."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT sq.secret_answer_hash, p.salt
                FROM users u
                JOIN security_questions sq ON u.user_id = sq.user_id
                JOIN user_passwords p ON u.user_id = p.user_id
                WHERE u.email = %s
            """, (email,))
            row = cur.fetchone()
            if not row:
                return False
            
            expected_hash = _hash_password(answer.lower(), row["salt"])
            return row["secret_answer_hash"] == expected_hash


def update_password(email: str, new_password: str) -> bool:
    """Update the password for a user. Returns True if the row was updated."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.user_id, p.salt
                FROM users u
                JOIN user_passwords p ON u.user_id = p.user_id
                WHERE u.email = %s
            """, (email,))
            row = cur.fetchone()
            if not row:
                return False
                
            user_id = row[0]
            salt = row[1]
            new_hash = _hash_password(new_password, salt)
            
            cur.execute("""
                UPDATE user_passwords
                SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (new_hash, user_id))
            
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# ── VECTOR / RAG QUERIES — do not modify ─────────────────────────────────────

def query_policy_vector_search(embedding: list[float], top_k: int = VECTOR_TOP_K) -> list[dict]:
    """
    Find the most relevant policy documents for a given query embedding.

    Args:
        embedding: Query vector from llm.embed(user_question)
        top_k:     Number of results to return

    Returns:
        List of dicts with title, category, content, and similarity score
    """
    sql = """
        SELECT
            title,
            category,
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM policy_documents
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (vec_str, vec_str, VECTOR_SIMILARITY_THRESHOLD, vec_str, top_k))
            return [dict(row) for row in cur.fetchall()]


def store_policy_document(
    title: str,
    category: str,
    content: str,
    embedding: list[float],
    source_file: str = "",
) -> int:
    """
    Insert a policy document with its embedding into the database.
    Used by skeleton/seed_vectors.py — students don't need to call this directly.

    Returns:
        The new document's id
    """
    sql = """
        INSERT INTO policy_documents (title, category, content, embedding, source_file)
        VALUES (%s, %s, %s, %s::vector, %s)
        RETURNING id
    """
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (title, category, content, vec_str, source_file))
            return cur.fetchone()[0]
