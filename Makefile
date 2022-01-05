PYTHON = python3

help:
	echo usage: make [python, javascript]

python:
	$(PYTHON) -m build
	rm -r src/koral.egg-info

javascript:
	echo ...
