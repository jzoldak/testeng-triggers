SHELL := /bin/bash

init:
	@python setup.py develop
	@pip install -r requirements.txt

test:
	rm -f .coverage
	@pip install -r test-requirements.txt
	@nosetests

publish:
	python setup.py sdist bdist_wheel upload
