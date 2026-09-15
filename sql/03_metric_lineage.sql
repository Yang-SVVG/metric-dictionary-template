-- 指标血缘：从指标回溯到表，再从表找回受影响的指标
-- 用法：把这当成「改表之前先查一遍」的查询模板。

-- 1) 某个指标用到哪些表（含版本信息）
SELECT m.metric_code,
       m.version,
       l.table_name,
       l.column_name,
       l.join_type
FROM dim_metric m
JOIN dim_metric_version v ON v.metric_id = m.metric_id AND v.version = m.version
JOIN dim_metric_lineage l ON l.version_id = v.version_id
WHERE m.metric_code = 'gmv_order_paid'
ORDER BY l.table_name;

-- 2) 某张表被哪些 active 指标引用（下线/改表前必查）
SELECT m.metric_code, m.metric_name, m.owner, m.version
FROM dim_metric m
JOIN dim_metric_version v ON v.metric_id = m.metric_id AND v.version = m.version
JOIN dim_metric_lineage l ON l.version_id = v.version_id
WHERE l.table_name = 'f_orders'
  AND m.status = 'active'
ORDER BY m.metric_code;

-- 3) 递归展开上游（表 → 上游表），适配「表依赖表」的数仓分层
WITH RECURSIVE upstream(table_name, depth, path) AS (
    SELECT 'f_orders', 0, 'f_orders'
    UNION ALL
    SELECT t.parent_table, u.depth + 1, u.path || ' -> ' || t.parent_table
    FROM dim_table_dependency t
    JOIN upstream u ON t.child_table = u.table_name
    WHERE u.depth < 5
      AND instr(u.path, t.parent_table) = 0   -- 防环
)
SELECT table_name, depth, path FROM upstream ORDER BY depth, table_name;

-- 4) 口径漂移自查：同名指标在不同版本里的公式是否只差过滤条件
SELECT metric_code,
       version,
       formula,
       LAG(formula) OVER (PARTITION BY metric_code ORDER BY version) AS prev_formula
FROM dim_metric_version v
JOIN dim_metric m USING (metric_id)
WHERE m.status IN ('active', 'deprecated')
ORDER BY metric_code, version;
