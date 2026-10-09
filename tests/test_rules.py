"""规则层面的用例：每条校验规则至少一个正例、一个反例。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate_dictionary.py"
BROKEN = ROOT / "data" / "metric_dictionary.broken.csv"

HEADER = ["metric_code", "metric_name", "domain", "definition", "formula", "source_tables",
          "grain", "unit", "owner", "version", "status", "updated_at"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def write_csv(path: Path, rows: list[list[str]], header: list[str] = HEADER) -> Path:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def test_broken_sample_hits_every_rule():
    result = run("--csv", str(BROKEN), "--today", "2026-10-20")
    assert result.returncode == 1, "反例集必须判 FAIL"
    for code in ["CODE_FORMAT", "CODE_DUPLICATE", "STATUS_INVALID", "SOURCE_UNKNOWN",
                 "FORMULA_SOURCE_MISMATCH", "EMPTY_FIELD", "NO_SOURCE"]:
        assert code in result.stdout, f"没报出 {code}"


def test_broken_sample_counts():
    result = run("--csv", str(BROKEN), "--today", "2026-10-20")
    assert "7 metrics / 6 unique codes / 8 error" in result.stdout


def test_uppercase_header_is_normalized(tmp_path: Path):
    path = write_csv(
        tmp_path / "upper.csv",
        [["gmv_order_paid", "支付订单 GMV", "经营", "支付金额合计", "select sum(pay_amount) from f_orders",
          "f_orders", "day", "元", "张三", "1", "active", "2026-10-01"]],
        header=[h.upper() for h in HEADER],
    )
    result = run("--csv", str(path), "--today", "2026-10-10")
    assert result.returncode == 0, result.stdout
    assert "1 metrics" in result.stdout


def test_stale_metric_warning(tmp_path: Path):
    path = write_csv(
        tmp_path / "stale.csv",
        [["gmv_order_paid", "支付订单 GMV", "经营", "支付金额合计", "select sum(pay_amount) from f_orders",
          "f_orders", "day", "元", "张三", "1", "active", "2025-01-01"]],
    )
    result = run("--csv", str(path), "--today", "2026-10-10", "--max-age-days", "90")
    assert result.returncode == 0
    assert "STALE_METRIC" in result.stdout
    assert "648 天" in result.stdout or "647 天" in result.stdout


def test_missing_column_exits_2(tmp_path: Path):
    path = write_csv(
        tmp_path / "nocol.csv",
        [["gmv_order_paid", "支付订单 GMV"]],
        header=["metric_code", "metric_name"],
    )
    result = run("--csv", str(path))
    assert result.returncode == 2
    assert "缺少必需列" in result.stderr


def test_missing_file_exits_2(tmp_path: Path):
    result = run("--csv", str(tmp_path / "nope.csv"))
    assert result.returncode == 2


def test_json_output_is_parseable(tmp_path: Path):
    path = write_csv(
        tmp_path / "dup.csv",
        [
            ["gmv_order_paid", "支付订单 GMV", "经营", "支付金额合计", "select sum(pay_amount) from f_orders",
             "f_orders", "day", "元", "张三", "1", "active", "2026-10-01"],
            ["gmv_order_paid", "支付订单 GMV", "经营", "重复行", "select sum(pay_amount) from f_orders",
             "f_orders", "day", "元", "张三", "1", "active", "2026-10-01"],
        ],
    )
    result = run("--csv", str(path), "--today", "2026-10-10", "--json")
    payload = json.loads(result.stdout)
    assert payload["total"] == 2
    assert payload["unique_codes"] == 1
    assert any(e["code"] == "CODE_DUPLICATE" for e in payload["errors"])


def test_report_script_writes_markdown(tmp_path: Path):
    out = tmp_path / "report.md"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "report.py"), "--today", "2026-10-01", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "指标字典质量报告" in text
    assert "按业务域" in text
