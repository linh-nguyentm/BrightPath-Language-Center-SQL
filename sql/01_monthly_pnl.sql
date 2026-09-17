-- Monthly P&L: revenue, cost, and margin.
-- Revenue = payments received that month (cash basis, matches how a small
-- center actually tracks cashflow). Cost = all expense categories that month.

WITH monthly_revenue AS (
    SELECT strftime('%Y-%m', payment_date) AS month, SUM(amount_vnd) AS revenue_vnd
    FROM payments
    GROUP BY 1
),
monthly_cost AS (
    SELECT strftime('%Y-%m', expense_date) AS month, SUM(amount_vnd) AS cost_vnd
    FROM expenses
    GROUP BY 1
)
SELECT
    r.month,
    r.revenue_vnd,
    c.cost_vnd,
    r.revenue_vnd - c.cost_vnd AS margin_vnd,
    ROUND(100.0 * (r.revenue_vnd - c.cost_vnd) / r.revenue_vnd, 1) AS margin_pct
FROM monthly_revenue r
JOIN monthly_cost c USING (month)
ORDER BY r.month;
