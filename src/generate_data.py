"""
Load the synthetic BrightPath dataset (see dataset.py) into a SQLite
database.

Usage:
    python src/generate_data.py
Writes:
    brightpath.db          SQLite database
"""

import sqlite3
from pathlib import Path

from dataset import build_dataset

DB_PATH = Path(__file__).resolve().parents[1] / "brightpath.db"

SCHEMA = """
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS marketing_spend;

CREATE TABLE courses (
    course_id       INTEGER PRIMARY KEY,
    course_name     TEXT NOT NULL,
    language        TEXT NOT NULL,
    level           TEXT NOT NULL,
    format          TEXT NOT NULL,
    duration_weeks  INTEGER NOT NULL,
    price_vnd       INTEGER NOT NULL
);

CREATE TABLE students (
    student_id          INTEGER PRIMARY KEY,
    signup_date          TEXT NOT NULL,
    acquisition_channel  TEXT NOT NULL,
    ward                 TEXT NOT NULL
);

CREATE TABLE enrollments (
    enrollment_id   INTEGER PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(student_id),
    course_id       INTEGER NOT NULL REFERENCES courses(course_id),
    enroll_date     TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('Active','Completed','Dropped')),
    drop_week       INTEGER
);

CREATE TABLE payments (
    payment_id      INTEGER PRIMARY KEY,
    enrollment_id   INTEGER NOT NULL REFERENCES enrollments(enrollment_id),
    payment_date    TEXT NOT NULL,
    amount_vnd      INTEGER NOT NULL,
    method          TEXT NOT NULL
);

CREATE TABLE marketing_spend (
    spend_id        INTEGER PRIMARY KEY,
    month           TEXT NOT NULL,
    channel         TEXT NOT NULL,
    amount_vnd      INTEGER NOT NULL,
    leads_generated INTEGER NOT NULL
);

CREATE TABLE expenses (
    expense_id      INTEGER PRIMARY KEY,
    expense_date    TEXT NOT NULL,
    category        TEXT NOT NULL,
    amount_vnd      INTEGER NOT NULL,
    note            TEXT
);
"""


def main():
    data = build_dataset()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    cur.executemany("INSERT INTO courses VALUES (?,?,?,?,?,?,?)", data["courses"])
    cur.executemany(
        "INSERT INTO marketing_spend (month, channel, amount_vnd, leads_generated) VALUES (?,?,?,?)",
        data["marketing_spend"],
    )
    cur.executemany("INSERT INTO students VALUES (?,?,?,?)", data["students"])
    cur.executemany("INSERT INTO enrollments VALUES (?,?,?,?,?,?)", data["enrollments"])
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", data["payments"])
    cur.executemany("INSERT INTO expenses VALUES (?,?,?,?,?)", data["expenses"])

    conn.commit()

    for t in ["courses", "students", "enrollments", "payments", "marketing_spend", "expenses"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:>16}: {n:,} rows")

    conn.close()
    print(f"\nWrote {DB_PATH}")


if __name__ == "__main__":
    main()
