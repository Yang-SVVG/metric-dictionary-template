# metric-dictionary-template · 指标字典与口径治理模板

一套「让同一个指标在全公司只有一个定义、一个 SQL」的最小可用模板：**指标字典表结构 + 示例字典 + 校验器 + 质量报告 + Excel 导出**。

## 背景

做经营分析时最常见的问题不是「没有数据」，而是**同一个指标在不同报表里数字不一样**：

- 销售额，财务按含税开票算，业务按发货算，运营按支付成功算 —— 三个数都对，但开会时对不上；
- 新同学要复现一张报表，得先翻聊天记录找「上次那个口径」；
- 每加一张报表就重写一遍 SQL，口径悄悄漂移，没人发现。

根因是口径只存在于人的记忆和 SQL 里，没有成为**可校验的资产**。

## 做法

把口径从「口头约定」变成「结构化数据 + 自动检查」：

1. **一个指标一条记录**：编码、定义、计算公式、来源表、统计粒度、单位、负责人、版本、状态。
2. **公式必须引用字典里登记过的表**：写 `source_tables` 之外的表直接报错，避免口径偷偷换数据源。
3. **状态机管理生命周期**：`draft`（评审中）→ `active`（生效）→ `deprecated`（下线，保留历史口径供追溯）。
4. **CI 里跑校验**：字典改动走 MR/PR，`validate_dictionary.py` 不通过就合不进去 —— 口径治理才不是一阵风。

## 结果

- 交接成本：新人查口径从「问人 30 分钟」变成「查字典 1 分钟」。
- 重复开发：通用组件与报表模板沉淀后，同类报表重复开发量下降约 **30%**（企业数据管理平台实践）。
- 口径争议：评审时对着公式和来源表逐条过，而不是对着两个不同数字争论。

## 快速开始

```bash
# 无第三方依赖，Python 3.9+
python scripts/validate_dictionary.py      # 校验示例字典
python -m pytest -q                        # 17 passed
python scripts/report.py                   # build/quality-report.md
python scripts/export_excel.py             # build/metric_dictionary.xlsx（需要 openpyxl）
```

或者用 Make：

```bash
make check     # 测试 + 校验
make report    # 生成质量报告
make excel     # 导出 Excel
```

校验输出（示例字典，故意留了一个「久未复核」的 warning）：

```
指标字典校验 · metric_dictionary.sample.csv（复核阈值 180 天）
  ⚠️  [STALE_METRIC] refund_rate: 已 331 天未复核

✅ PASS  12 metrics / 12 unique codes / 0 error / 1 warning
   domain     : 经营 3 · 用户 3 · 供应链 3 · 财务 2 · 质量 1
   status     : active 9 · draft 2 · deprecated 1
   completeness: definition 100% · formula 100% · owner 100%
```

想看不合格长什么样，直接跑反例集 —— 8 个 error 覆盖 7 类规则：

```bash
python scripts/validate_dictionary.py --csv data/metric_dictionary.broken.csv
# ❌ FAIL  7 metrics / 6 unique codes / 8 error / 0 warning
```

## 目录结构

```
metric-dictionary-template/
├─ data/
│  ├─ README.md                        # 列说明 + 从 Excel 迁移的注意事项
│  ├─ metric_dictionary.sample.csv      # 示例字典（12 个指标，PASS）
│  └─ metric_dictionary.broken.csv      # 反例集（每个错误各一行，FAIL）
├─ docs/
│  ├─ caliber-governance.md             # 治理流程：谁定口径、怎么评审、怎么下线
│  ├─ naming-conventions.md             # 编码/中文名/公式的命名规范
│  ├─ lifecycle.md                       # draft → active → deprecated 与变更规程
│  └─ review-checklist.md                # 评审会用的 15 条清单
├─ examples/
│  └─ quickstart.md                      # 五分钟接入自己的字典
├─ scripts/
│  ├─ validate_dictionary.py             # 校验器（核心，纯标准库）
│  ├─ report.py                          # 质量报告 → build/quality-report.md
│  └─ export_excel.py                    # Excel 导出（下拉校验、冻结首行）
├─ sql/
│  ├─ 01_schema.sql                      # dim_metric / 版本表 / 血缘表 + 视图
│  ├─ 02_fact_tables.stub.sql            # 示例事实表（换成自己的 DDL）
│  ├─ 03_metric_lineage.sql              # 血缘查询：指标→表、表→指标、递归上游
│  └─ 04_quality_checks.sql              # 落地后检查：空值/断流/环比异常/口径一致性
├─ tests/
│  ├─ test_validate_dictionary.py        # 9 个核心规则用例
│  └─ test_rules.py                      # 8 个 CLI 与集成用例
├─ .github/workflows/validate.yml        # CI：字典改动即校验
├─ Makefile · requirements-dev.txt
└─ LICENSE (MIT) · CONTRIBUTING.md
```

## 校验规则

| 规则 | 级别 | 说明 |
| --- | --- | --- |
| 必填列齐全 | error | 缺列直接失败（退出码 2） |
| `metric_code` 唯一且 snake_case | error | 防止同名不同义 |
| 定义/公式/单位/负责人非空 | error | 空口径等于没口径 |
| 公式引用的表必须在 `source_tables` 且已建表 | error | 防止口径偷偷换源 |
| `status ∈ {draft, active, deprecated}` | error | 生命周期必须收敛 |
| 同一 domain 下中文名不重复 | warning | 命名冲突提醒 |
| `updated_at` 超过 180 天未复核 | warning | 口径会过期（可用 `--max-age-days` 收紧到 90） |

规则是可执行的，不是文档：`tests/` 里每条规则都有失败用例 —— 规则没有失败用例，等于没有规则。

## 质量报告长什么样

`python scripts/report.py` 生成 Markdown，给评审会直接用：

```markdown
# 指标字典质量报告（2026-10-20）
- 指标数：**12**（唯一编码 12）
- 结论：**PASS** — 0 error / 1 warning

## 按业务域
| 业务域 | error | warning | 指标数 |
| 经营 | 0 | 1 | 3 |
...
## 该复核了
| `refund_rate` | 已 331 天未复核 |
```

## 放进 CI

`.github/workflows/validate.yml` 已经有现成配置：字典文件一改动就跑校验，error 时直接失败。工作流跑 `pytest`（17 个用例）+ 校验器，两步都过才允许合并。

## 这套模板适合谁

- 正在做指标平台 / 数据治理，需要一个**能落地的字典结构**（而不是又一张 Excel）；
- 想把「口径评审」从会议变成 CI 检查；
- 面试时要讲清楚「你怎么治理口径」—— 直接给仓库，比讲半小时更有效。

## Roadmap

- [ ] 从 dbt / DataHub 导入既有指标元数据（`--import dbt`）
- [ ] 校验器输出 SARIF，直接进 GitHub Code Scanning
- [ ] 字典变更的 diff 报告（哪几个指标的口径动了）

## License

MIT
