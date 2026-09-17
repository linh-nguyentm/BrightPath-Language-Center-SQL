-- Cost structure: which expense category eats the most budget, and how
-- that mix shifted over the year.

SELECT
    strftime('%Y-%m', expense_date) AS month,
    category,
    SUM(amount_vnd) AS amount_vnd
FROM expenses
GROUP BY 1, 2
ORDER BY 1, 2;
