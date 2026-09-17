-- Enrollment trend by month and channel, for the budgeting/marketing calendar.

SELECT
    strftime('%Y-%m', s.signup_date) AS month,
    s.acquisition_channel,
    COUNT(*) AS new_students
FROM students s
GROUP BY 1, 2
ORDER BY 1, 2;
