.PHONY: check validate report excel clean

check:            ## 跑测试 + 校验示例字典
	python -m pytest -q
	python scripts/validate_dictionary.py

validate:         ## 只跑校验（CI 主入口）
	python scripts/validate_dictionary.py

report:           ## 生成 Markdown 质量报告 → build/quality-report.md
	python scripts/report.py

excel:            ## 导出 Excel 版字典 → build/metric_dictionary.xlsx
	python scripts/export_excel.py

clean:
	rm -rf build .pytest_cache __pycache__
