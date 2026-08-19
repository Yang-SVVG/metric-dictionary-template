# 数据文件说明

| 文件 | 用途 |
| --- | --- |
| `metric_dictionary.sample.csv` | 规范示例：12 个指标，`python scripts/validate_dictionary.py` 应输出 `0 error / 1 warning` |
| `metric_dictionary.broken.csv` | 反例集：每个错误各一行，用来演示校验器报错，**不要**用它跑 CI |

## 列说明

```text
metric_code     指标编码，小写 snake_case，全局唯一
metric_name     中文名，同一 domain 内不重名
domain          业务域（经营/用户/供应链/财务/质量）
definition      口径定义：算什么、不算什么
formula         计算式，用 from/join 指向来源表
source_tables   来源表，逗号分隔，必须在 sql/ 中声明
grain           粒度：order / order_item / user_day ...
unit            单位：元 / 人 / 单 / % / 天
owner           责任人（姓名或团队）
version         版本号，口径变更时 +1
status          draft / active / deprecated
updated_at      复核日期 YYYY-MM-DD，超 180 天告警
```

## 从 Excel 迁移

1. 表头改成上面 12 个小写列名（校验器会 `strip().lower()` 兜底，但别依赖）；
2. 合并单元格拆开，一行一个指标；
3. `status` 只有三个合法值，历史表的「启用/停用/已下线」要映射；
4. 先跑 `python scripts/validate_dictionary.py --csv <你的文件>`，把 error 清完再入库。
