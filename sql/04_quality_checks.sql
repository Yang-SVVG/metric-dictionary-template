-- 指标落地后的质量检查：口径对了，数据还得对得上。
-- 每条检查返回「一行 = 一个问题」，空结果集 = 通过。

-- 1) 必填字段空值率（字典侧）
SELECT 'dim_metric.owner' AS field,
       COUNT(*) FILTER (WHERE owner IS NULL OR owner = '') AS null_cnt,
       COUNT(*) AS total
FROM dim_metric
WHERE status = 'active';

-- 2) 指标值为空（数据侧）：已上线指标当天无数据，通常是上游断流或过滤条件写错
SELECT m.metric_code, d.stat_date
FROM dim_metric m
LEFT JOIN f_metric_daily d
       ON d.metric_code = m.metric_code
      AND d.stat_date = CURRENT_DATE - INTERVAL '1 day'
WHERE m.status = 'active'
  AND d.metric_code IS NULL;

-- 3) 环比异常（超过 5 倍或跌破 1/5，先当事故处理，不要先当业务变化）
WITH m AS (
    SELECT metric_code, stat_date, metric_value,
           LAG(metric_value) OVER (PARTITION BY metric_code ORDER BY stat_date) AS prev
    FROM f_metric_daily
    WHERE stat_date >= CURRENT_DATE - INTERVAL '8 days'
)
SELECT metric_code, stat_date, prev, metric_value
FROM m
WHERE prev IS NOT NULL AND prev <> 0
  AND (metric_value > prev * 5 OR metric_value < prev / 5);

-- 4) 口径一致性抽样：同一指标在「明细算」与「预聚合表」里应完全相等
SELECT 'gmv_order_paid' AS metric_code,
       (SELECT SUM(pay_amount) FROM f_orders
         WHERE status = 'paid' AND paid_at::date = CURRENT_DATE - 1) AS from_detail,
       (SELECT gmv FROM dws_month_region
         WHERE stat_month = to_char(CURRENT_DATE - 1, 'YYYY-MM')) AS from_rollup;
