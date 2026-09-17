-- Marketing channel performance: cost per lead, conversion, CAC, ROI.
-- CAC = marketing spend / students actually acquired via that channel.
-- ROI = revenue from those students' payments, divided by spend.

WITH channel_spend AS (
    SELECT channel, SUM(amount_vnd) AS spend_vnd, SUM(leads_generated) AS leads
    FROM marketing_spend
    GROUP BY channel
),
channel_students AS (
    SELECT acquisition_channel AS channel, COUNT(*) AS students_acquired
    FROM students
    GROUP BY acquisition_channel
),
channel_revenue AS (
    SELECT s.acquisition_channel AS channel, SUM(p.amount_vnd) AS revenue_vnd
    FROM students s
    JOIN enrollments e ON e.student_id = s.student_id
    JOIN payments p ON p.enrollment_id = e.enrollment_id
    GROUP BY s.acquisition_channel
)
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
FROM channel_spend cs
JOIN channel_students st ON st.channel = cs.channel
JOIN channel_revenue cr ON cr.channel = cs.channel
ORDER BY revenue_per_vnd_spent DESC NULLS LAST;
