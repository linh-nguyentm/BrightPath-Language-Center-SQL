-- Revenue by course: which courses/levels actually drive revenue.

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
