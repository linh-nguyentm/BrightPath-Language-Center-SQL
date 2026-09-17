-- Dropout rate by course level: where the center is leaking students.

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
