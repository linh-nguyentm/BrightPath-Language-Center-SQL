-- MySQL 5.7 version. Two dialect differences from sql/01_monthly_pnl.sql:
-- (1) no strftime() -- use DATE_FORMAT() instead.
-- (2) no WITH / CTEs (added in MySQL 8.0) -- use derived tables (subqueries
--     in FROM) instead. Functionally identical, just older syntax.

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
