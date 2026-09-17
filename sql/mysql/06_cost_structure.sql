-- MySQL version. Only real difference from sql/06_cost_structure.sql:
-- DATE_FORMAT() instead of strftime().

SELECT
    DATE_FORMAT(expense_date, '%Y-%m') AS month,
    category,
    SUM(amount_vnd) AS amount_vnd
FROM expenses
GROUP BY 1, 2
ORDER BY 1, 2;
