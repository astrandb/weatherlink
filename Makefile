__VERSION__ = "0.0.1"

bump:
	bump2version --allow-dirty --current-version $(__VERSION__) patch Makefile custom_components/teracom/const.py custom_components/teracom/manifest.json

lint:
	isort custom_components
	black custom_components
	flake8 custom_components

install_dev:
	pip install -r requirements-dev.txt
