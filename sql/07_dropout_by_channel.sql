-- Dropout rate by acquisition channel: does WHERE a student came from
-- predict whether they stick around? This connects the marketing data to
-- the enrollment data -- a channel with a low CAC is not actually cheap
-- if the students it brings drop out early.

SELECT
    s.acquisition_channel,
    COUNT(*) AS enrollments,
    SUM(CASE WHEN e.status = 'Dropped' THEN 1 ELSE 0 END) AS dropped,
    ROUND(100.0 * SUM(CASE WHEN e.status = 'Dropped' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dropout_pct
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
GROUP BY s.acquisition_channel
ORDER BY dropout_pct DESC;
