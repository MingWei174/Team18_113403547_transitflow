TASK 6 EXTENSION CHECKLIST
==========================

This file lists all files modified or added for the Task 6 Optional Extension.
Our team implemented a dual-feature extension: **My History Panel (UI)** + **Loyalty Points System (Database/Schema Change)**.
The course rubric requires a file at project root and a marker comment at the top 
of each modified source file: `# TASK 6 EXTENSION:`.

Modified files and functions
----------------------------

- **databases/relational/schema.sql**
  - Added `loyalty_points INT DEFAULT 0` column to the `users` table.
  - Added `# TASK 6 EXTENSION:` marker and a `[WHY]` comment explaining the design decision for placing the points column in the users table.

- **databases/relational/queries.py**
  - Added `# TASK 6 EXTENSION:` marker and a `[WHY]` comment inside `execute_booking()` explaining why the loyalty points update must be executed within the main booking transaction to ensure ACID compliance.
  - Added the SQL execution logic to update `loyalty_points` based on ticket price (`points_earned = int(amount_usd)`).
  - Uses existing `query_user_bookings(user_email)` for the UI history feature.

- **DESIGN_DOCUMENT.md**
  - Added Section 7 detailing the Motivation, Schema modifications, Cypher/SQL Query examples, and Testing Evidence for the Task 6 extension.

- **skeleton/ui.py**
  - Added top-of-file marker: `# TASK 6 EXTENSION: Added 'My History' panel (see TASK6.md)`
  - Added function: `do_show_history(current_user_email)` — formats combined booking/trip history into Markdown for display.
  - Added UI components: `my_history_btn` and `history_display` and event wiring.

- **skeleton/agent.py**
  - Added top-of-file marker: `# TASK 6 EXTENSION: Added get_loyalty_points tool for End-to-End integration`
  - Registered `get_loyalty_points` into the `TOOLS` list and implemented LLM routing logic.
  - Enabled true End-to-End tool calling (UI -> Agent -> DB -> Agent -> UI) for loyalty point queries.

Why these files
---------------
To fully satisfy the "Static Code" grading criteria for modifying the database schema and adding new queries, we implemented a **Loyalty Points System**. The schema change ensures that the DB effectively tracks user rewards, while the query modifications dynamically update points upon successful bookings using transactional guarantees. 

Simultaneously, we provided a **My History Panel** on the frontend to visualize booking records, delivering a complete full-stack extension.

How to test
-----------
1. Start Docker and seed the DB if not already seeded:
   ```bash
   docker compose up -d
   python skeleton/seed_postgres.py
   ```
2. Start the UI:
   ```bash
   python skeleton/ui.py
   ```
3. Log in with an email from `train-mock-data/registered_users.json` and make a new booking via the chat.
4. Check pgAdmin (`users` table) to verify the `loyalty_points` increased according to the ticket price.
5. Click **My History** in the sidebar to verify your past bookings.
