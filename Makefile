.PHONY: lint format check-lint install test-syntax run run-server docker-build docker-up docker-up-host docker-down docker-logs docker-clean check-block-time

# Install all dependencies
install:
	which python3 && python3 --version
	@echo "Installing dependencies..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "No active virtual environment detected."; \
		if [ ! -d "venv" ]; then \
			echo "Creating virtual environment..."; \
			python3 -m venv venv; \
		else \
			echo "Using existing venv directory..."; \
		fi; \
		. venv/bin/activate; \
	else \
		echo "Using already active virtual environment: $$VIRTUAL_ENV"; \
	fi; \
	pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt && \
	echo "✓ Installed dependencies"

# Run application in CLI mode
run:
	python3 app.py

# Run application in server mode
run-server:
	python3 app.py --server

# Format code with black
format:
	black app.py src/

# Check code formatting without changing files
check-format:
	black --check app.py src/

# Run flake8 linting
lint:
	flake8 app.py src/ --max-line-length=120 --ignore=E501,W503

# Run pylint
pylint:
	pylint app.py src/ --max-line-length=120 --fail-under=8.0

# Check syntax only
check-syntax:
	python3 -m py_compile app.py src/*.py
	@echo "✓ Syntax check passed"

# Run all linting checks
check-lint: check-format lint
	@echo "✓ All linting checks passed"

# Auto-fix formatting
fix: format
	@echo "✓ Code formatted"

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up -d --force-recreate

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-restart: docker-down docker-up

docker-clean:
	docker compose down -v
	docker rmi eth-loadgen:latest || true
	# docker images -a |  grep "<none>" | awk '{print $3}' | xargs docker rmi --force

# Default RPC URL if not provided
RPC_URL ?= http://localhost:8545
WAIT_NEXT ?=
TIMEOUT ?=

check-block-time:
	@echo "Using RPC_URL=$(RPC_URL)"
	@python3 scripts/check_block_time.py \
		--rpc-url $(RPC_URL) \
		$(if $(WAIT_NEXT),--wait-next,) \
		$(if $(TIMEOUT),--timeout $(TIMEOUT),)
	@echo "Usage examples:"
	@echo "  make check-block-time RPC_URL=http://localhost:8545"
	@echo "  make check-block-time RPC_URL=http://localhost:8545 WAIT_NEXT=1"
	@echo "  make check-block-time RPC_URL=http://localhost:8545 TIMEOUT=120"
