#!/usr/bin/env python3
"""把字典 CSV 导出成「业务同事能直接填」的 Excel。

做三件事：表头样式 + 冻结首行、列宽自适应、status 列加下拉校验（防止填出 published 这种值）。
依赖 openpyxl（可选）：pip install -e ".[excel]"

用法：
    python scripts/export_excel.py                       # build/metric_dictionary.xlsx
    python scripts/export_excel.py --csv data/metric_dictionary.sample.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLUMN_WIDTH = {
    "metric_code": 26, "metric_name": 22, "domain": 10, "definition": 52,
    "formula": 52, "source_tables": 26, "grain": 12, "unit": 8,
    "owner": 12, "version": 9, "status": 12, "updated_at": 13,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出 Excel 版指标字典")
    parser.add_argument("--csv", default=str(ROOT / "data" / "metric_dictionary.sample.csv"))
    parser.add_argument("--out", default=str(ROOT / "build" / "metric_dictionary.xlsx"))
    args = parser.parse_args(argv)

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        raise SystemExit('需要 openpyxl：pip install -e ".[excel]"')

    with open(args.csv, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]

    wb = Workbook()
    ws = wb.active
    ws.title = "指标字典"
    ws.append(header)
    for row in body:
        ws.append(row)

    head_fill = PatternFill("solid", fgColor="2F5B6D")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(vertical="center", horizontal="center")

    for idx, name in enumerate(header, start=1):
        letter = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[letter].width = COLUMN_WIDTH.get(name, 18)

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ws.freeze_panes = "A2"

    if "status" in header:
        col = ws.cell(row=1, column=header.index("status") + 1).column_letter
        dv = DataValidation(type="list", formula1='"draft,active,deprecated"', allow_blank=False,
                            showErrorMessage=True, errorTitle="状态非法",
                            error="只能是 draft / active / deprecated")
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{ws.max_row}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"已写入 {out}（{len(body)} 个指标）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
