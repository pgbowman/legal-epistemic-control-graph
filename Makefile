.PHONY: install validate ingest review evaluate report demo test clean

install:
	pip install -e .

validate:
	python -m src.validate

ingest:
	python -m src.ingest

review:
	python -m src.review

evaluate:
	python -m src.evaluate

report:
	python -m src.render_report

demo: validate ingest review evaluate report

test:
	pytest

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
