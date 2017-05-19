VIRTUALENV = virtualenv
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
TOX = $(VENV)/bin/tox
TEMPDIR := $(shell mktemp -d)

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue .
	$(TEMPDIR)/bin/pip freeze > requirements.txt

virtualenv: $(PYTHON)
$(PYTHON):
	virtualenv $(VENV) --python=python3

tox: $(TOX)
$(TOX): virtualenv
	$(VENV)/bin/pip install tox

tests-once: tox
	$(VENV)/bin/tox -e py35

tests: tox
	$(VENV)/bin/tox
