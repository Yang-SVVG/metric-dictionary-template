#!/usr/bin/env python3
"""指标字典校验器。

把「口径约定」变成可执行检查：字段完整性、编码唯一、公式与血缘表一致、状态合法、
口径是否过期。适合放进 CI（退出码非 0 即失败）。

用法：
    python scripts/validate_dictionary.py
    python scripts/validate_dictionary.py --csv data/metric_dictionary.sample.csv --sql-dir sql
    python scripts/validate_dictionary.py --json   # 机器可读，便于流水线消费

退出码：0 = 通过（可能有 warning）；1 = 有 error；2 = 文件/格式问题。
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = [
    "metric_code",
    "metric_name",
    "domain",
    "definition",
    "formula",
    "source_tables",
    "grain",
    "unit",
    "owner",
    "version",
    "status",
    "updated_at",
]
REQUIRED_VALUES = ["metric_code", "metric_name", "definition", "formula", "unit", "owner"]
VALID_STATUS = {"draft", "active", "deprecated"}
CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TABLE_REF_RE = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", re.IGNORECASE)
CREATE_RE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-zA-Z_][\w.]*)", re.I)


@dataclass
class Issue:
    level: str  # error / warning
    code: str
    row: str
    message: str


@dataclass
class Report:
    total: int = 0
    unique_codes: int = 0
    issues: list[Issue] = field(default_factory=list)
    by_domain: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    filled: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]


def load_schema_tables(sql_dir: Path) -> set[str]:
    """从 sql 目录下的 .sql 文件中收集已声明的表名。"""
    tables: set[str] = set()
    for path in sorted(sql_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for match in CREATE_RE.finditer(text):
            tables.add(match.group(1).lower())
    return tables


def read_dictionary(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        # 同事从 Excel 导出时表头常常是大写，这里统一归一化，字典规范只认小写
        header = [(c or "").strip().lower() for c in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise ValueError(f"缺少必需列: {', '.join(missing)}")
        return [
            {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k}
            for row in reader
        ]


def parse_date(text: str) -> dt.date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_sources(raw: str) -> set[str]:
    return {s.strip().lower() for s in re.split(r"[,;，；、\s]+", raw) if s.strip()}


def validate(rows: list[dict[str, str]], tables: set[str], max_age_days: int, today: dt.date) -> Report:
    report = Report(total=len(rows))
    seen_codes: dict[str, int] = {}
    seen_names: dict[tuple[str, str], str] = {}

    for idx, row in enumerate(rows, start=2):  # 2 = 表头之后第一行
        code = row.get("metric_code", "")
        label = code or f"<row {idx}>"

        for column in REQUIRED_VALUES:
            if not row.get(column):
                report.issues.append(Issue("error", "EMPTY_FIELD", label, f"{column} 为空"))
            else:
                report.filled[column] = report.filled.get(column, 0) + 1

        if code:
            if not CODE_RE.match(code):
                report.issues.append(
                    Issue("error", "CODE_FORMAT", label, "metric_code 必须是小写 snake_case")
                )
            if code in seen_codes:
                report.issues.append(
                    Issue("error", "CODE_DUPLICATE", label, f"与第 {seen_codes[code]} 行编码重复")
                )
            seen_codes[code] = idx

        domain, name = row.get("domain", ""), row.get("metric_name", "")
        if domain and name:
            key = (domain, name)
            if key in seen_names:
                report.issues.append(
                    Issue("warning", "NAME_DUPLICATE", label, f"同一业务域下中文名与 {seen_names[key]} 重复")
                )
            seen_names[key] = label

        status = row.get("status", "")
        if status and status not in VALID_STATUS:
            report.issues.append(
                Issue("error", "STATUS_INVALID", label, f"status={status!r} 不在 {sorted(VALID_STATUS)} 中")
            )

        sources = parse_sources(row.get("source_tables", ""))
        if not sources:
            report.issues.append(Issue("error", "NO_SOURCE", label, "source_tables 未登记来源表"))
        for table in sources:
            if tables and table not in tables:
                report.issues.append(
                    Issue("error", "SOURCE_UNKNOWN", label, f"来源表 {table} 未在 sql/ 中声明")
                )

        referenced = {m.group(1).lower() for m in TABLE_REF_RE.finditer(row.get("formula", ""))}
        if referenced and sources and not referenced <= sources:
            extra = ", ".join(sorted(referenced - sources))
            report.issues.append(
                Issue("error", "FORMULA_SOURCE_MISMATCH", label, f"公式引用了未登记的表: {extra}")
            )

        updated = parse_date(row.get("updated_at", ""))
        if updated is None:
            report.issues.append(Issue("warning", "DATE_INVALID", label, "updated_at 无法解析"))
        elif (today - updated).days > max_age_days:
            report.issues.append(
                Issue("warning", "STALE_METRIC", label, f"已 {(today - updated).days} 天未复核")
            )

        if domain:
            report.by_domain[domain] = report.by_domain.get(domain, 0) + 1
        if status:
            report.by_status[status] = report.by_status.get(status, 0) + 1

    report.unique_codes = len(seen_codes)
    return report


def render(report: Report, csv_path: Path, max_age_days: int) -> str:
    lines = [f"指标字典校验 · {csv_path.name}（复核阈值 {max_age_days} 天）"]
    for issue in report.issues:
        icon = "❌" if issue.level == "error" else "⚠️ "
        lines.append(f"  {icon} [{issue.code}] {issue.row}: {issue.message}")

    domain_text = " · ".join(f"{k} {v}" for k, v in sorted(report.by_domain.items(), key=lambda kv: -kv[1]))
    status_text = " · ".join(f"{k} {v}" for k, v in sorted(report.by_status.items(), key=lambda kv: -kv[1]))
    total = max(report.total, 1)
    completeness = " · ".join(
        f"{c} {report.filled.get(c, 0) * 100 // total}%" for c in ("definition", "formula", "owner")
    )

    verdict = "PASS" if not report.errors else "FAIL"
    lines.append("")
    lines.append(
        f"{'✅' if not report.errors else '❌'} {verdict}  "
        f"{report.total} metrics / {report.unique_codes} unique codes / "
        f"{len(report.errors)} error / {len(report.warnings)} warning"
    )
    lines.append(f"   domain     : {domain_text}")
    lines.append(f"   status     : {status_text}")
    lines.append(f"   completeness: {completeness}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验指标字典")
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("--csv", default=str(root / "data" / "metric_dictionary.sample.csv"))
    parser.add_argument("--sql-dir", default=str(root / "sql"))
    parser.add_argument("--max-age-days", type=int, default=180)
    parser.add_argument("--today", default=None, help="覆盖今天（便于测试），格式 YYYY-MM-DD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"找不到字典文件: {csv_path}", file=sys.stderr)
        return 2

    try:
        rows = read_dictionary(csv_path)
    except ValueError as exc:
        print(f"字典格式错误: {exc}", file=sys.stderr)
        return 2

    tables = load_schema_tables(Path(args.sql_dir))
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    report = validate(rows, tables, args.max_age_days, today)

    if args.json:
        print(
            json.dumps(
                {
                    "total": report.total,
                    "unique_codes": report.unique_codes,
                    "errors": [i.__dict__ for i in report.errors],
                    "warnings": [i.__dict__ for i in report.warnings],
                    "by_domain": report.by_domain,
                    "by_status": report.by_status,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render(report, csv_path, args.max_age_days))

    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
