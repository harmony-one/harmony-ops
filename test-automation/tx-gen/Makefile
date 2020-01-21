.PHONY: clean-py clean-build

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-py - remove Python file artifacts"
	@echo "install - install the library locally"
	@echo "test - run full test suite"
	@echo "sdist - package"

clean: clean-build clean-py

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr .eggs/

clean-py:
	rm -fr .pytest_cache/
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

test:
	python3 -m py.test tests

release: clean
	python3 -m incremental.update harmony_transaction_generator --patch --rc
	python3 -m incremental.update harmony_transaction_generator
	python3 setup.py sdist bdist_wheel
	twine upload dist/*

install:
	python3 -m pip install -e .

doc docs: clean
	python3 -m pdoc --html harmony_transaction_generator --force

sdist: clean
ifdef VERSION  # Argument for incremental, reference: https://pypi.org/project/incremental/ .
	python3 -m incremental.update harmony_transaction_generator --$(VERSION)
else
	python3 -m incremental.update harmony_transaction_generator --dev
endif
	python3 setup.py sdist bdist_wheel
	ls -l dist