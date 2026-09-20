-- Revenue concentration: how much does the center depend on a small
-- group of high-paying students vs. a broad base? Ranks every student by
-- total revenue; the running/cumulative share is computed in the Python
-- analysis layer (run_analysis.py) since it needs a running total over
-- ranked rows, which is simplest done there.

SELECT
    s.student_id,
    s.acquisition_channel,
    SUM(p.amount_vnd) AS revenue_vnd
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN payments p ON p.enrollment_id = e.enrollment_id
GROUP BY s.student_id
ORDER BY revenue_vnd DESC;
