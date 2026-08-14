"""校验器的行为测试：每条规则都要有「会失败」的证据，否则规则等于没写。"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_dictionary as vd  # noqa: E402

HEADER = [
    "metric_code", "metric_name", "domain", "definition", "formula",
    "source_tables", "grain", "unit", "owner", "version", "status", "updated_at",
]

OK_ROW = [
    "gmv", "成交总额", "经营", "支付成功订单金额合计",
    "SUM(o.pay_amount) FROM f_orders o", "f_orders", "日", "元",
    "数据运营组", "v1.0", "active", "2026-10-01",
]


def write_csv(tmp_path: Path, rows: list[list[str]]) -> Path:
    path = tmp_path / "dict.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return path


@pytest.fixture()
def sql_dir(tmp_path: Path) -> Path:
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE f_orders (order_id INT);\nCREATE TABLE f_sessions (session_id INT);",
        encoding="utf-8",
    )
    return tmp_path


def run(csv_path: Path, sql_dir: Path, *extra: str) -> tuple[int, str]:
    import io

    buffer = io.StringIO()
    stdout, sys.stdout = sys.stdout, buffer
    try:
        code = vd.main(["--csv", str(csv_path), "--sql-dir", str(sql_dir), "--today", "2026-10-27", *extra])
    finally:
        sys.stdout = stdout
    return code, buffer.getvalue()


def test_repo_sample_passes() -> None:
    """仓库自带的示例字典必须能通过，否则模板本身不可信。"""
    code = vd.main(["--csv", str(ROOT / "data" / "metric_dictionary.sample.csv"),
                    "--sql-dir", str(ROOT / "sql"), "--today", "2026-10-27"])
    assert code == 0


def test_clean_row_passes(tmp_path: Path, sql_dir: Path) -> None:
    code, out = run(write_csv(tmp_path, [OK_ROW]), sql_dir)
    assert code == 0
    assert "PASS" in out


def test_duplicate_code_is_error(tmp_path: Path, sql_dir: Path) -> None:
    code, out = run(write_csv(tmp_path, [OK_ROW, OK_ROW]), sql_dir)
    assert code == 1
    assert "CODE_DUPLICATE" in out


def test_unknown_status_is_error(tmp_path: Path, sql_dir: Path) -> None:
    row = list(OK_ROW)
    row[10] = "online"
    code, out = run(write_csv(tmp_path, [row]), sql_dir)
    assert code == 1
    assert "STATUS_INVALID" in out


def test_source_table_must_be_declared(tmp_path: Path, sql_dir: Path) -> None:
    row = list(OK_ROW)
    row[5] = "f_not_exist"
    code, out = run(write_csv(tmp_path, [row]), sql_dir)
    assert code == 1
    assert "SOURCE_UNKNOWN" in out


def test_formula_cannot_reference_unregistered_table(tmp_path: Path, sql_dir: Path) -> None:
    """公式偷偷 join 了一张没登记血缘的表 —— 这是口径漂移最隐蔽的来源。"""
    row = list(OK_ROW)
    row[4] = "SUM(o.pay_amount) FROM f_orders o JOIN f_sessions s ON s.session_id = o.session_id"
    code, out = run(write_csv(tmp_path, [row]), sql_dir)
    assert code == 1
    assert "FORMULA_SOURCE_MISMATCH" in out


def test_stale_metric_is_warning_with_exit_zero(tmp_path: Path, sql_dir: Path) -> None:
    row = list(OK_ROW)
    row[11] = "2025-01-01"
    code, out = run(write_csv(tmp_path, [row]), sql_dir)
    assert code == 0
    assert "STALE_METRIC" in out


def test_missing_column_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("metric_code,metric_name\ngmv,成交总额\n", encoding="utf-8")
    code, _ = run(path, tmp_path)
    assert code == 2


def test_json_output_is_parseable(tmp_path: Path, sql_dir: Path) -> None:
    import json

    code, out = run(write_csv(tmp_path, [OK_ROW]), sql_dir, "--json")
    payload = json.loads(out)
    assert code == 0
    assert payload["total"] == 1
    assert payload["unique_codes"] == 1
    assert payload["by_status"]["active"] == 1
