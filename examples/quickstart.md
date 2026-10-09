# 五分钟接入

## 1. 拿模板

```bash
git clone https://github.com/Yang-SVVG/metric-dictionary-template.git
cd metric-dictionary-template
python -m pytest -q          # 9 passed
```

## 2. 换成自己的字典

```bash
cp data/metric_dictionary.sample.csv data/metric_dictionary.csv
# 改 data/metric_dictionary.csv，然后：
python scripts/validate_dictionary.py --csv data/metric_dictionary.csv
```

第一次跑大概率一堆 `SOURCE_UNKNOWN` —— 因为你还没把表声明进 `sql/`。
把 `sql/02_fact_tables.stub.sql` 里的表名换成自己的（或者直接贴真实 DDL），再跑一次。

## 3. 生成给人看的东西

```bash
python scripts/report.py --csv data/metric_dictionary.csv     # build/quality-report.md
python scripts/export_excel.py --csv data/metric_dictionary.csv  # build/metric_dictionary.xlsx
```

- `quality-report.md` 给评审会用：按业务域、按问题类型列问题，标出该复核的指标；
- `metric_dictionary.xlsx` 给业务同事填：表头带色、冻结首行、status 是下拉框。

## 4. 放进 CI

```yaml
- run: python scripts/validate_dictionary.py --csv data/metric_dictionary.csv --max-age-days 90
```

退出码 1 就拦住合并请求；上线前再跑一次 `report.py`，把报告贴进发布说明。

## 5. 常见报错怎么改

| 报错 | 含义 | 改法 |
| --- | --- | --- |
| `SOURCE_UNKNOWN` | 来源表没在 `sql/` 里声明 | 补 DDL 或改表名 |
| `FORMULA_SOURCE_MISMATCH` | 公式里的表多于 `source_tables` | 补登记（通常是漏写 join 的表） |
| `CODE_DUPLICATE` | 编码重复 | 大概率是复制上一行忘了改 |
| `STALE_METRIC` | 超 180 天没复核 | 重算一遍，或把 `updated_at` 改成复核日 |
