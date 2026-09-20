-- ============================================================================
-- BrightPath SQL Tutorial -- Steps 1-12
-- ============================================================================
-- Run these top to bottom in MySQL Workbench, one at a time. Steps 1-6 are
-- data validation (always do this before analysis). Steps 7-12 are the six
-- business questions the project answers.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- STEP 1: Look at what's actually in a table before doing anything else.
-- ----------------------------------------------------------------------------
SELECT * FROM students LIMIT 10;


-- ----------------------------------------------------------------------------
-- STEP 2: Confirm the row count matches what's expected (620 students).
-- ----------------------------------------------------------------------------
SELECT COUNT(*) FROM students;


-- ----------------------------------------------------------------------------
-- STEP 3: Check for missing values in a key column.
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS missing_signup_date
FROM students
WHERE signup_date IS NULL;


-- ----------------------------------------------------------------------------
-- STEP 4: Check the data's date range makes sense (no year 1970s or
-- future dates from a data-entry error).
-- ----------------------------------------------------------------------------
SELECT MIN(signup_date) AS earliest, MAX(signup_date) AS latest
FROM students;


-- ----------------------------------------------------------------------------
-- STEP 5: Check the distinct values of a categorical column -- catches
-- typos or inconsistent casing that would silently split one real category
-- into two.
-- ----------------------------------------------------------------------------
SELECT acquisition_channel, COUNT(*) AS n
FROM students
GROUP BY acquisition_channel
ORDER BY n DESC;


-- ----------------------------------------------------------------------------
-- STEP 6a: See what a JOIN actually produces, before filtering anything.
-- For every enrollment row, this attaches the matching student row next to
-- it (if one exists).
-- ----------------------------------------------------------------------------
SELECT e.enrollment_id, e.student_id, s.student_id AS matched_student, s.ward
FROM enrollments e
LEFT JOIN students s ON s.student_id = e.student_id
LIMIT 10;

-- STEP 6b: Referential integrity check -- count enrollments that point to
-- a student_id that doesn't exist in students. LEFT JOIN keeps every
-- enrollment row even when no match is found, and fills the unmatched
-- side with NULL; filtering on that NULL finds exactly the broken rows.
-- Expected result: 0.
SELECT COUNT(*) AS orphan_enrollments
FROM enrollments e
LEFT JOIN students s ON s.student_id = e.student_id
WHERE s.student_id IS NULL;


-- ============================================================================
-- Business questions start here. Data has been validated -- now we answer
-- the actual questions a director would ask.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- STEP 7: Are we making money? Monthly revenue vs. cost.
-- Built in three small pieces, then combined.
-- ----------------------------------------------------------------------------

-- 7a. Revenue alone, by month.
SELECT DATE_FORMAT(payment_date, '%Y-%m') AS month, SUM(amount_vnd) AS revenue_vnd
FROM payments
GROUP BY 1
ORDER BY 1;

-- 7b. Cost alone, by month.
SELECT DATE_FORMAT(expense_date, '%Y-%m') AS month, SUM(amount_vnd) AS cost_vnd
FROM expenses
GROUP BY 1
ORDER BY 1;

-- 7c. Combine both into one P&L table. MySQL 5.7 has no WITH/CTEs (added
-- in 8.0), so each of 7a/7b becomes a derived table (a subquery inside
-- FROM) instead, then joined on month.
SELECT
    r.month,
    r.revenue_vnd,
    c.cost_vnd,
    r.revenue_vnd - c.cost_vnd AS margin_vnd,
    ROUND(100.0 * (r.revenue_vnd - c.cost_vnd) / r.revenue_vnd, 1) AS margin_pct
FROM (
    SELECT DATE_FORMAT(payment_date, '%Y-%m') AS month, SUM(amount_vnd) AS revenue_vnd
    FROM payments
    GROUP BY 1
) r
JOIN (
    SELECT DATE_FORMAT(expense_date, '%Y-%m') AS month, SUM(amount_vnd) AS cost_vnd
    FROM expenses
    GROUP BY 1
) c USING (month)
ORDER BY r.month;


-- ----------------------------------------------------------------------------
-- STEP 8: Which courses actually drive revenue?
-- ----------------------------------------------------------------------------
SELECT
    co.course_name,
    co.level,
    co.format,
    COUNT(DISTINCT e.enrollment_id) AS enrollments,
    SUM(p.amount_vnd) AS revenue_vnd,
    ROUND(SUM(p.amount_vnd) * 1.0 / COUNT(DISTINCT e.enrollment_id)) AS avg_revenue_per_enrollment
FROM payments p
JOIN enrollments e ON e.enrollment_id = p.enrollment_id
JOIN courses co ON co.course_id = e.course_id
GROUP BY co.course_id
ORDER BY revenue_vnd DESC;


-- ----------------------------------------------------------------------------
-- STEP 9: Which marketing channel is actually worth the spend?
-- CAC = spend / students acquired. ROI = revenue from those students /
-- spend. Three derived tables (spend, students, revenue per channel),
-- joined together.
-- ----------------------------------------------------------------------------
SELECT
    cs.channel,
    cs.leads,
    st.students_acquired,
    ROUND(100.0 * st.students_acquired / cs.leads, 1) AS lead_to_student_pct,
    cs.spend_vnd,
    CASE WHEN st.students_acquired > 0
         THEN ROUND(cs.spend_vnd * 1.0 / st.students_acquired) ELSE NULL END AS cac_vnd,
    cr.revenue_vnd,
    CASE WHEN cs.spend_vnd > 0
         THEN ROUND(cr.revenue_vnd * 1.0 / cs.spend_vnd, 2) ELSE NULL END AS revenue_per_vnd_spent
FROM (
    SELECT channel, SUM(amount_vnd) AS spend_vnd, SUM(leads_generated) AS leads
    FROM marketing_spend
    GROUP BY channel
) cs
JOIN (
    SELECT acquisition_channel AS channel, COUNT(*) AS students_acquired
    FROM students
    GROUP BY acquisition_channel
) st ON st.channel = cs.channel
JOIN (
    SELECT s.acquisition_channel AS channel, SUM(p.amount_vnd) AS revenue_vnd
    FROM students s
    JOIN enrollments e ON e.student_id = s.student_id
    JOIN payments p ON p.enrollment_id = e.enrollment_id
    GROUP BY s.acquisition_channel
) cr ON cr.channel = cs.channel
ORDER BY (cs.spend_vnd = 0), revenue_per_vnd_spent DESC;


-- ----------------------------------------------------------------------------
-- STEP 10: Which course level loses the most students, and how fast?
-- ----------------------------------------------------------------------------
SELECT
    co.level,
    COUNT(*) AS enrollments,
    SUM(CASE WHEN e.status = 'Dropped' THEN 1 ELSE 0 END) AS dropped,
    ROUND(100.0 * SUM(CASE WHEN e.status = 'Dropped' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dropout_pct,
    ROUND(AVG(CASE WHEN e.status = 'Dropped' THEN e.drop_week END), 1) AS avg_week_dropped
FROM enrollments e
JOIN courses co ON co.course_id = e.course_id
GROUP BY co.level
ORDER BY dropout_pct DESC;


-- ----------------------------------------------------------------------------
-- STEP 11: New-student trend by month and channel (for the marketing
-- calendar).
-- ----------------------------------------------------------------------------
SELECT
    DATE_FORMAT(s.signup_date, '%Y-%m') AS month,
    s.acquisition_channel,
    COUNT(*) AS new_students
FROM students s
GROUP BY 1, 2
ORDER BY 1, 2;


-- ----------------------------------------------------------------------------
-- STEP 12: Cost structure -- which expense category eats the most budget,
-- and how that mix shifted over the year.
-- ----------------------------------------------------------------------------
SELECT
    DATE_FORMAT(expense_date, '%Y-%m') AS month,
    category,
    SUM(amount_vnd) AS amount_vnd
FROM expenses
GROUP BY 1, 2
ORDER BY 1, 2;
