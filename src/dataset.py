"""
Shared synthetic-data builder for the BrightPath Language Center project.

This module only builds Python rows (lists of tuples) -- it knows nothing
about SQLite or MySQL. `generate_data.py` loads these rows into SQLite;
`generate_data_mysql.py` loads the same rows into MySQL. Keeping the
generation logic in one place means both databases always hold identical
data.

This is entirely synthetic data, designed to mirror the *shape* of the
operational data (enrollment, revenue, cost, marketing) a small language
center actually produces. No real business's data is used or represented
here.
"""

import random
from datetime import date, timedelta

random.seed(42)

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


# Seasonality multiplier for new signups, by month.
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

# Base monthly cost per category (VND), before marketing (computed from
# spend) and teacher fees (scaled with enrollments) below.
BASE_MONTHLY_COST = {
    "Rent": 18_000_000,
    "Salaries": 22_000_000,
    "Utilities": 3_500_000,
    "Materials": 2_000_000,
}


def build_dataset():
    """Return {table_name: [row_tuple, ...]} for all 6 BrightPath tables."""
    random.seed(42)  # deterministic across both loaders

    # ---- marketing spend & leads, per month per channel ----
    base_leads_per_month = 140
    spend_rows = []
    leads_pool = {}
    for m in MONTHS:
        season = SEASONALITY[m.month]
        month_leads = round(base_leads_per_month * season * random.uniform(0.9, 1.1))
        for ch, prof in CHANNEL_PROFILE.items():
            leads = max(0, round(month_leads * prof["leads_share"] * random.uniform(0.85, 1.15)))
            spend = leads * prof["cost_per_lead"]
            spend_rows.append((m.isoformat()[:7], ch, spend, leads))
            leads_pool[(m.isoformat()[:7], ch)] = leads

    # ---- students: convert each month's leads into signups per channel ----
    students = []
    student_id = 1
    for m in MONTHS:
        mkey = m.isoformat()[:7]
        for ch, prof in CHANNEL_PROFILE.items():
            leads = leads_pool[(mkey, ch)]
            n_signups = round(leads * prof["conv_rate"] * random.uniform(0.9, 1.1))
            for _ in range(n_signups):
                students.append(
                    (student_id, random_date_in_month(m).isoformat(), ch, random.choice(CITIES_WARD))
                )
                student_id += 1

    # ---- enrollments: each student enrolls in 1 (mostly) or 2 courses ----
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

    # ---- payments: each enrollment pays in 1-3 installments ----
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
            payments.append((payment_id, enr_id, pay_dt.isoformat(), amount, random.choice(PAY_METHODS)))
            payment_id += 1

    # ---- expenses: fixed monthly costs + marketing + scaled teacher fees ----
    expenses = []
    expense_id = 1
    for m in MONTHS:
        mkey = m.isoformat()[:7]
        for cat, base in BASE_MONTHLY_COST.items():
            amt = round(base * random.uniform(0.95, 1.05))
            expenses.append((expense_id, m.replace(day=5).isoformat(), cat, amt, None))
            expense_id += 1

        month_marketing = sum(s[2] for s in spend_rows if s[0] == mkey)
        expenses.append((expense_id, m.replace(day=5).isoformat(), "Marketing", month_marketing, "Sum of channel spend"))
        expense_id += 1

        active_that_month = sum(
            1 for _, _, _, enroll_date_s, status, _ in enrollments if enroll_date_s[:7] <= mkey
        )
        teacher_fee = round(active_that_month * 65_000 * random.uniform(0.9, 1.1))
        expenses.append((expense_id, m.replace(day=28).isoformat(), "Teacher Fees", teacher_fee, "Scales with enrollments"))
        expense_id += 1

    return {
        "courses": COURSES,
        "marketing_spend": spend_rows,  # note: no surrogate id column here, added by loader
        "students": students,
        "enrollments": enrollments,
        "payments": payments,
        "expenses": expenses,
    }
