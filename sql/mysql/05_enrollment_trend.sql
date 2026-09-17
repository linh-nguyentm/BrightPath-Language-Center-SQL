-- MySQL version. Only real difference from sql/05_enrollment_trend.sql:
-- DATE_FORMAT() instead of strftime().

SELECT
    DATE_FORMAT(s.signup_date, '%Y-%m') AS month,
    s.acquisition_channel,
    COUNT(*) AS new_students
FROM students s
GROUP BY 1, 2
ORDER BY 1, 2;
