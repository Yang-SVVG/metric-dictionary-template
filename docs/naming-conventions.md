# 命名规范：一个指标只能有一个名字

规范的目的不是好看，是**让口径可以被机器比对**。三条硬约束，其余是习惯。

## 1. 编码（metric_code）

```text
<域>_<对象>_<度量或动作>
gmv_order_paid      订单支付金额（GMV）
user_dau_active     日活
refund_rate_paid    退款率（口径：以已支付订单为分母）
```

- 全小写 + 下划线，`^[a-z][a-z0-9_]*$`，正则由 `scripts/validate_dictionary.py` 强制；
- 域用固定词表（经营 / 用户 / 供应链 / 财务 / 质量），不要出现 `biz`、`common` 这种垃圾桶词；
- **不要用缩写堆**：`gmvordpay` 比 `gmv_order_paid` 少 5 个字符，多 5 分钟沟通成本。

## 2. 中文名（metric_name）

- 同一业务域内不得重名（校验器给 `NAME_DUPLICATE` warning）；
- 写法：`口径 + 对象 + 度量`，例：`支付订单 GMV`、`近 30 天活跃用户数`；
- 时间窗必须写在名字里，不要靠上下文约定 —— 「活跃用户数」是永不过期的歧义源。

## 3. 公式（formula）

- 必须能被 `from/join` 正则抽出来源表，且抽取结果必须 ⊆ `source_tables`（否则 `FORMULA_SOURCE_MISMATCH`）；
- 用 `{{table}}` 占位可读版，实际 SQL 放 `sql/`；
- 分母写清楚过滤条件：`sum(pay_amount) / count(distinct case when status='paid' then order_id end)`。

## 常见反例

| 反例 | 问题 | 改法 |
| --- | --- | --- |
| `GMV` | 大小写混用、无域 | `gmv_order_paid` |
| `销售额` | 中英混杂定义、无时间窗 | `支付订单 GMV（自然日）` |
| `user_cnt` | 域缺失、度量模糊 | `user_active_cnt_daily` |
| `SELECT * FROM orders` | 来源不可解析 | 显式列名 + 登记来源表 |

## 为什么不直接用 Excel 表头

Excel 表头会被手动改（大小写、空格、合并单元格）。校验器读入时统一 `strip().lower()`，
但**字典文件本身必须是规范格式** —— 归一化是为了容忍历史文件，不是为了放宽标准。
