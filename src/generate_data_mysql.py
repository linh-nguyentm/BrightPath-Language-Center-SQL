"""
Load the synthetic BrightPath dataset (see dataset.py) into a MySQL
database, using the exact same rows as generate_data.py's SQLite version.

Usage:
    python src/generate_data_mysql.py

Reads connection settings from environment variables (with sane local
defaults so it "just works" against a local dev server):
    BRIGHTPATH_MYSQL_HOST     default: 127.0.0.1
    BRIGHTPATH_MYSQL_PORT     default: 3307
    BRIGHTPATH_MYSQL_USER     default: brightpath_app
    BRIGHTPATH_MYSQL_PASSWORD default: BrightPath2026!
    BRIGHTPATH_MYSQL_DB       default: brightpath
"""

import os

import pymysql

from dataset import build_dataset

SCHEMA = """
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS marketing_spend;

CREATE TABLE courses (
    course_id       INT PRIMARY KEY,
    course_name     VARCHAR(100) NOT NULL,
    language        VARCHAR(50) NOT NULL,
    level           VARCHAR(20) NOT NULL,
    format          VARCHAR(20) NOT NULL,
    duration_weeks  INT NOT NULL,
    price_vnd       INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE students (
    student_id           INT PRIMARY KEY,
    signup_date           DATE NOT NULL,
    acquisition_channel   VARCHAR(50) NOT NULL,
    ward                  VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE enrollments (
    enrollment_id   INT PRIMARY KEY,
    student_id      INT NOT NULL,
    course_id       INT NOT NULL,
    enroll_date     DATE NOT NULL,
    status          VARCHAR(20) NOT NULL,
    drop_week       INT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payments (
    payment_id      INT PRIMARY KEY,
    enrollment_id   INT NOT NULL,
    payment_date    DATE NOT NULL,
    amount_vnd      INT NOT NULL,
    method          VARCHAR(30) NOT NULL,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE marketing_spend (
    spend_id        INT AUTO_INCREMENT PRIMARY KEY,
    month           CHAR(7) NOT NULL,
    channel         VARCHAR(50) NOT NULL,
    amount_vnd      INT NOT NULL,
    leads_generated INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE expenses (
    expense_id      INT PRIMARY KEY,
    expense_date    DATE NOT NULL,
    category        VARCHAR(30) NOT NULL,
    amount_vnd      INT NOT NULL,
    note            VARCHAR(100) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def connect():
    return pymysql.connect(
        host=os.environ.get("BRIGHTPATH_MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("BRIGHTPATH_MYSQL_PORT", "3307")),
        user=os.environ.get("BRIGHTPATH_MYSQL_USER", "brightpath_app"),
        password=os.environ.get("BRIGHTPATH_MYSQL_PASSWORD", "BrightPath2026!"),
        database=os.environ.get("BRIGHTPATH_MYSQL_DB", "brightpath"),
        autocommit=False,
    )


def main():
    data = build_dataset()

    conn = connect()
    cur = conn.cursor()

    for statement in SCHEMA.split(";"):
        statement = statement.strip()
        if statement:
            cur.execute(statement)

    cur.executemany("INSERT INTO courses VALUES (%s,%s,%s,%s,%s,%s,%s)", data["courses"])
    cur.executemany(
        "INSERT INTO marketing_spend (month, channel, amount_vnd, leads_generated) VALUES (%s,%s,%s,%s)",
        data["marketing_spend"],
    )
    cur.executemany("INSERT INTO students VALUES (%s,%s,%s,%s)", data["students"])
    cur.executemany("INSERT INTO enrollments VALUES (%s,%s,%s,%s,%s,%s)", data["enrollments"])
    cur.executemany("INSERT INTO payments VALUES (%s,%s,%s,%s,%s)", data["payments"])
    cur.executemany("INSERT INTO expenses VALUES (%s,%s,%s,%s,%s)", data["expenses"])

    conn.commit()

    for t in ["courses", "students", "enrollments", "payments", "marketing_spend", "expenses"]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        n = cur.fetchone()[0]
        print(f"{t:>16}: {n:,} rows")

    conn.close()
    print("\nLoaded into MySQL database 'brightpath'.")


if __name__ == "__main__":
    main()
