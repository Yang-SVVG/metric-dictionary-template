#!/usr/bin/env python3
"""把校验结果整理成一份给人看的质量报告（Markdown）。

校验器负责「判对错」，这个脚本负责「说清楚该先改什么」：
按业务域统计问题、按问题类型排序、把过期指标单独列出来。

用法：
    python scripts/report.py                        # 写 build/quality-report.md
    python scripts/report.py --csv data/metric_dictionary.broken.csv --stdout
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_dictionary import load_schema_tables, read_dictionary, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def build_report(csv_path: Path, sql_dir: Path, max_age_days: int, today: dt.date) -> str:
    rows = read_dictionary(csv_path)
    tables = load_schema_tables(sql_dir)
    report = validate(rows, tables, max_age_days, today)

    domain_of = {row.get("metric_code", ""): row.get("domain", "(未分类)") for row in rows}
    by_domain: dict[str, Counter] = defaultdict(Counter)
    for issue in report.issues:
        by_domain[domain_of.get(issue.row, issue.row)][issue.level] += 1

    issue_counter = Counter(i.code for i in report.issues)
    stale = [i for i in report.issues if i.code == "STALE_METRIC"]

    lines = [
        f"# 指标字典质量报告（{today.isoformat()}）",
        "",
        f"- 字典文件：`{csv_path.name}`",
        f"- 指标数：**{report.total}**（唯一编码 {report.unique_codes}）",
        f"- 复核阈值：{max_age_days} 天",
        f"- 结论：**{'PASS' if not report.errors else 'FAIL'}** — "
        f"{len(report.errors)} error / {len(report.warnings)} warning",
        "",
        "## 按业务域",
        "",
        "| 业务域 | error | warning | 指标数 |",
        "| --- | --- | --- | --- |",
    ]
    for domain, counter in sorted(by_domain.items(), key=lambda kv: -sum(kv[1].values())):
        lines.append(f"| {domain} | {counter['error']} | {counter['warning']} | {report.by_domain.get(domain, 0)} |")

    lines += ["", "## 按问题类型", "", "| 问题 | 次数 | 说明 |", "| --- | --- | --- |"]
    explain = {
        "EMPTY_FIELD": "必填字段为空",
        "CODE_FORMAT": "编码不符合小写 snake_case",
        "CODE_DUPLICATE": "编码重复",
        "STATUS_INVALID": "状态不在 draft/active/deprecated",
        "NO_SOURCE": "未登记来源表",
        "SOURCE_UNKNOWN": "来源表未在 sql/ 声明",
        "FORMULA_SOURCE_MISMATCH": "公式引用的表未登记",
        "STALE_METRIC": "超过复核阈值未复核",
        "DATE_INVALID": "updated_at 无法解析",
        "NAME_DUPLICATE": "同域中文名重复",
    }
    for code, count in issue_counter.most_common():
        lines.append(f"| `{code}` | {count} | {explain.get(code, '')} |")

    if stale:
        lines += ["", "## 该复核了", "", "| 指标 | 说明 |", "| --- | --- |"]
        for issue in stale:
            lines.append(f"| `{issue.row}` | {issue.message} |")

    if report.errors:
        lines += ["", "## 待修明细", ""]
        for issue in report.errors:
            lines.append(f"- `{issue.code}` **{issue.row}**：{issue.message}")

    lines += ["", "## 下一步", ""]
    if report.errors:
        lines.append("1. 先把 `待修明细` 的 error 清零（CI 会在这一步拦住）；")
    lines.append("2. 处理 `该复核了` 里的指标，重算一遍或写明「核对无变化」；")
    lines.append("3. 把结论同步到指标评审会，避免下个季度重复讨论同一口径。")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成指标字典质量报告")
    parser.add_argument("--csv", default=str(ROOT / "data" / "metric_dictionary.sample.csv"))
    parser.add_argument("--sql-dir", default=str(ROOT / "sql"))
    parser.add_argument("--max-age-days", type=int, default=180)
    parser.add_argument("--today", default=None)
    parser.add_argument("--out", default=str(ROOT / "build" / "quality-report.md"))
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args(argv)

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    text = build_report(Path(args.csv), Path(args.sql_dir), args.max_age_days, today)
    if args.stdout:
        print(text)
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
