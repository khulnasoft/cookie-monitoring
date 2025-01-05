.DEFAULT_GOAL := .all

.PHONY: .all
.all: venv mypy

venv: requirements.txt
	rm -rf venv
	bash -c '\
		python3 -m venv venv \
		&& venv/bin/pip install -r requirements.txt \
	' || rm -rf venv

venv-tools: requirements.tools.txt
	rm -rf venv-tools
	python3 -m venv venv-tools
	venv-tools/bin/pip install -r requirements.tools.txt

.PHONY: format
format: venv-tools
	venv-tools/bin/ruff check --fix --unsafe-fixes
	venv-tools/bin/ruff format

.PHONY: mypy
mypy: venv
	venv/bin/mypy *.py

.PHONY: run
run: venv
	venv/bin/python monitor_cookies.py

.PHONY: clean
clean:
	rm -rf venv
	rm -f cursor.txt
