all:
	noop

coverage:
	COVERAGE_FILE="$(shell pwd)/.coverage" python -m regression_runner --coverage regression/*.yaml
	coverage report -m
	coverage html

regression:
	python -m regression_runner regression/*.yaml


.PHONY: all coverage regression
