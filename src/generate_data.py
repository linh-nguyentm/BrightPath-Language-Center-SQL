"""
Generate a synthetic operational dataset for a fictional foreign-language
center ("BrightPath Language Center") and load it into a SQLite database.

This is entirely synthetic data, designed to mirror the *shape* of the
operational data (enrollment, revenue, cost, marketing) a small language
center actually produces, so the SQL analysis in this project is realistic.
No real business's data is used or represented here.

Usage:
    python src/generate_data.py
Writes:
    brightpath.db          SQLite database
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DB_PATH = Path(__file__).resolve().parents[1] / "brightpath.db"

# ------------------------------------------------------------------
# 0. REFERENCE DATA
# ------------------------------------------------------------------

COURSES = [
    # course_id, name, language, level, format, duration_weeks, price_vnd
    (1, "English Starter", "English", "Beginner", "Group", 8, 2_400_000),
    (2, "English Pre-Intermediate", "English", "Intermediate", "Group", 10, 2_800_000),
    (3, "English Upper-Intermediate", "English", "Advanced", "Group", 10, 3_200_000),
    (4, "IELTS Foundation", "English", "Intermediate", "Group", 12, 3_600_000),
    (5, "IELTS Intensive", "English", "Advanced", "Group", 8, 4_500_000),
    (6, "English 1-on-1", "English", "Mixed", "1-on-1", 8, 6_000_000),
    (7, "Business English", "English", "Advanced", "Group", 8, 3_800_000),
    (8, "Kids English (7-10y)", "English", "Beginner", "Group", 12, 2_600_000),
]

CHANNELS = ["Facebook Ads", "Google Ads", "Referral", "Zalo", "Walk-in", "Website"]
CITIES_WARD = ["Ward A", "Ward B", "Ward C", "Ward D", "Ward E"]
PAY_METHODS = ["Bank Transfer", "Cash", "Momo"]

# 13-month window: one full year of context ending on the CV period's close.
START = date(2023, 1, 1)
END = date(2024, 1, 31)


def months_between(start: date, end: date):
    y, m = start.year, start.month
    out = []
    while (y, m) <= (end.year, end.month):
        out.append(date(y, m, 1))
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out


MONTHS = months_between(START, END)


def random_date_in_month(d: date) -> date:
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    days = (next_month - d).days
    return d + timedelta(days=random.randint(0, days - 1))


# Seasonality multiplier for new signups, by month (index 0 = Jan 2023).
# Lower in Jun/Jul (summer heat, school holidays before enrollment push),
# a hard dip around Tet (Feb), and a strong push in Aug-Sep (new semester)
# and Dec-Jan (New Year resolutions) -- typical for a VN language center.
SEASONALITY = {
    1: 0.75,  # Jan: post-Tet lull carries over
    2: 0.45,  # Feb: Tet holiday
    3: 0.85,
    4: 0.95,
    5: 1.0,
    6: 0.7,
    7: 0.65,
    8: 1.35,  # Aug: new semester push
    9: 1.3,
    10: 1.0,
    11: 0.95,
    12: 1.15,  # Dec: New Year resolutions
}

# Channel efficiency baked in on purpose, so the analysis has something
# real to find: Referral converts best per lead and costs nothing directly;
# Facebook Ads is the volume channel but at a weaker conversion rate;
# Walk-in has no marketing spend attached.
CHANNEL_PROFILE = {
    "Facebook Ads": {"cost_per_lead": 45_000, "leads_share": 0.34, "conv_rate": 0.28},
    "Google Ads": {"cost_per_lead": 60_000, "leads_share": 0.16, "conv_rate": 0.33},
    "Referral": {"cost_per_lead": 0, "leads_share": 0.18, "conv_rate": 0.52},
    "Zalo": {"cost_per_lead": 20_000, "leads_share": 0.14, "conv_rate": 0.31},
    "Website": {"cost_per_lead": 15_000, "leads_share": 0.08, "conv_rate": 0.36},
    "Walk-in": {"cost_per_lead": 0, "leads_share": 0.10, "conv_rate": 0.60},
}

# Dropout risk baked in per level, so a "which segment leaks students"
# finding is real: Beginner groups (esp. Kids) drop out more than
# Advanced / exam-prep courses where motivation is higher.
DROPOUT_RATE_BY_LEVEL = {"Beginner": 0.22, "Intermediate": 0.14, "Advanced": 0.07, "Mixed": 0.10}

EXPENSE_CATEGORIES = ["Rent", "Teacher Fees", "Salaries", "Marketing", "Utilities", "Materials"]
# Base monthly cost per category (VND), before marketing (computed from spend) and scaling.
BASE_MONTHLY_COST = {
    "Rent": 18_000_000,
    "Teacher Fees": 0,  # scaled with enrollments below
    "Salaries": 22_000_000,
    "Utilities": 3_500_000,
    "Materials": 2_000_000,
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
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
    )

    cur.executemany(
        "INSERT INTO courses VALUES (?,?,?,?,?,?,?)", COURSES
    )

    # ----------------------------------------------------------------
    # 1. MARKETING SPEND & LEADS, PER MONTH PER CHANNEL
    # ----------------------------------------------------------------
    base_leads_per_month = 140
    spend_rows = []
    leads_pool = {}  # (month_str, channel) -> leads_generated
    for m in MONTHS:
        season = SEASONALITY[m.month]
        month_leads = round(base_leads_per_month * season * random.uniform(0.9, 1.1))
        for ch, prof in CHANNEL_PROFILE.items():
            leads = max(0, round(month_leads * prof["leads_share"] * random.uniform(0.85, 1.15)))
            spend = leads * prof["cost_per_lead"]
            spend_rows.append((m.isoformat()[:7], ch, spend, leads))
            leads_pool[(m.isoformat()[:7], ch)] = leads

    cur.executemany(
        "INSERT INTO marketing_spend (month, channel, amount_vnd, leads_generated) VALUES (?,?,?,?)",
        spend_rows,
    )

    # ----------------------------------------------------------------
    # 2. STUDENTS: convert each month's leads into signups per channel
    # ----------------------------------------------------------------
    students = []
    student_id = 1
    for m in MONTHS:
        mkey = m.isoformat()[:7]
        for ch, prof in CHANNEL_PROFILE.items():
            leads = leads_pool[(mkey, ch)]
            n_signups = round(leads * prof["conv_rate"] * random.uniform(0.9, 1.1))
            for _ in range(n_signups):
                students.append(
                    (
                        student_id,
                        random_date_in_month(m).isoformat(),
                        ch,
                        random.choice(CITIES_WARD),
                    )
                )
                student_id += 1

    cur.executemany("INSERT INTO students VALUES (?,?,?,?)", students)

    # ----------------------------------------------------------------
    # 3. ENROLLMENTS: each student enrolls in 1 (mostly) or 2 courses
    # ----------------------------------------------------------------
    enrollments = []
    enrollment_id = 1
    course_by_id = {c[0]: c for c in COURSES}
    for sid, signup_date_s, _, _ in students:
        signup_dt = date.fromisoformat(signup_date_s)
        n_courses = 1 if random.random() < 0.82 else 2
        chosen = random.sample(COURSES, k=n_courses)
        for c in chosen:
            course_id, _, _, level, _, duration_weeks, _ = c
            enroll_dt = signup_dt + timedelta(days=random.randint(0, 5))
            if enroll_dt > END:
                continue
            dropout_p = DROPOUT_RATE_BY_LEVEL[level]
            roll = random.random()
            weeks_elapsed = (END - enroll_dt).days // 7
            if roll < dropout_p and weeks_elapsed >= 2:
                status = "Dropped"
                drop_week = random.randint(2, min(duration_weeks - 1, max(2, weeks_elapsed)))
            elif weeks_elapsed >= duration_weeks:
                status = "Completed"
                drop_week = None
            else:
                status = "Active"
                drop_week = None
            enrollments.append((enrollment_id, sid, course_id, enroll_dt.isoformat(), status, drop_week))
            enrollment_id += 1

    cur.executemany(
        "INSERT INTO enrollments VALUES (?,?,?,?,?,?)", enrollments
    )

    # ----------------------------------------------------------------
    # 4. PAYMENTS: each enrollment pays in 1-3 installments
    # ----------------------------------------------------------------
    payments = []
    payment_id = 1
    for enr_id, sid, course_id, enroll_date_s, status, drop_week in enrollments:
        price = course_by_id[course_id][6]
        enroll_dt = date.fromisoformat(enroll_date_s)
        if status == "Dropped" and drop_week is not None and drop_week <= 1:
            n_installments = 1
            paid_fraction = 0.5
        else:
            n_installments = random.choice([1, 1, 2, 3])
            paid_fraction = 1.0
        remaining = round(price * paid_fraction)
        for i in range(n_installments):
            amount = remaining // (n_installments - i)
            remaining -= amount
            pay_dt = enroll_dt + timedelta(days=i * 20 + random.randint(0, 4))
            if pay_dt > END:
                pay_dt = END
            payments.append(
                (payment_id, enr_id, pay_dt.isoformat(), amount, random.choice(PAY_METHODS))
            )
            payment_id += 1

    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", payments)

    # ----------------------------------------------------------------
    # 5. EXPENSES: fixed monthly costs + marketing (from spend table)
    #    + teacher fees that scale with active enrollments that month
    # ----------------------------------------------------------------
    expenses = []
    expense_id = 1
    for m in MONTHS:
        mkey = m.isoformat()[:7]
        for cat, base in BASE_MONTHLY_COST.items():
            if cat == "Teacher Fees":
                continue
            amt = round(base * random.uniform(0.95, 1.05))
            expenses.append((expense_id, m.replace(day=5).isoformat(), cat, amt, None))
            expense_id += 1

        month_marketing = sum(s[2] for s in spend_rows if s[0] == mkey)
        expenses.append((expense_id, m.replace(day=5).isoformat(), "Marketing", month_marketing, "Sum of channel spend"))
        expense_id += 1

        active_that_month = sum(
            1
            for _, _, _, enroll_date_s, status, _ in enrollments
            if enroll_date_s[:7] <= mkey and status != None  # noqa: E711
        )
        teacher_fee = round(active_that_month * 65_000 * random.uniform(0.9, 1.1))
        expenses.append((expense_id, m.replace(day=28).isoformat(), "Teacher Fees", teacher_fee, "Scales with enrollments"))
        expense_id += 1

    cur.executemany("INSERT INTO expenses VALUES (?,?,?,?,?)", expenses)

    conn.commit()

    # ---- quick sanity print ----
    for t in ["courses", "students", "enrollments", "payments", "marketing_spend", "expenses"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:>16}: {n:,} rows")

    conn.close()
    print(f"\nWrote {DB_PATH}")


if __name__ == "__main__":
    main()
