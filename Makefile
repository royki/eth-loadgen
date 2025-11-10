.PHONY: lint format check-lint install test-syntax run run-server docker-build docker-up docker-up-host docker-down docker-logs docker-clean check-block-time infra-check deploy-geth deploy-eth-loadgen deploy-prometheus deploy-grafana deploy-all infra-down

# Install all dependencies
install:
	@which python3 && python3 --version
	@echo "Installing dependencies..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "No active virtual environment detected."; \
		if [ ! -d "venv" ]; then \
			echo "Creating virtual environment..."; \
			python3 -m venv venv; \
		else \
			echo "Using existing venv directory..."; \
		fi; \
		echo "Activating virtual environment and installing dependencies..."; \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		pip install --no-cache-dir -r requirements.txt && \
		echo "✓ Installed dependencies"; \
	else \
		echo "Using already active virtual environment: $$VIRTUAL_ENV"; \
		pip install --upgrade pip && \
		pip install --no-cache-dir -r requirements.txt && \
		echo "✓ Installed dependencies"; \
	fi

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
RPC_URL ?= http://geth-node.local:80
TARGET_INTERVAL ?= 6
CONTINUOUS ?=1
NUM_BLOCKS ?=

check-block-time:
	@echo "Using RPC_URL=$(RPC_URL)"
	@echo "Using TARGET_INTERVAL=$(TARGET_INTERVAL)"
	@echo "Using CONTINUOUS=$(CONTINUOUS)"
	@echo "Using NUM_BLOCKS=$(NUM_BLOCKS)"
	@python3 scripts/check_block_time.py \
		--rpc-url $(RPC_URL) \
		--target $(TARGET_INTERVAL) \
		$(if $(CONTINUOUS),--continuous,) \
		$(if $(NUM_BLOCKS),--num-blocks $(NUM_BLOCKS),)

# Infrastructure commands
infra-check:
	@echo "Checking Kubernetes cluster status..."
	@kubectl cluster-info > /dev/null 2>&1 && \
		echo "✅ Kubernetes cluster is running" && \
		kubectl get nodes || \
		(echo "❌ Kubernetes cluster is not accessible" && exit 1)

# Helm deployment commands
HELM_CHARTS_DIR = infra/helm-charts

deploy-geth:
	@echo "Deploying geth-node to dev namespace..."
	@kubectl create namespace dev 2>/dev/null || true
	@helm upgrade --install geth-node $(HELM_CHARTS_DIR)/geth-node \
		--namespace dev \
		--create-namespace \
		--wait \
		--timeout 5m
	@echo "✅ geth-node deployed to dev namespace"

deploy-eth-loadgen:
	@echo "Deploying eth-loadgen to app namespace..."
	@kubectl create namespace app 2>/dev/null || true
	@helm upgrade --install eth-loadgen $(HELM_CHARTS_DIR)/eth-loadgen \
		--namespace app \
		--create-namespace \
		--wait \
		--timeout 5m
	@echo "✅ eth-loadgen deployed to app namespace"

deploy-prometheus:
	@echo "Adding prometheus-community helm repository..."
	@helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || helm repo update prometheus-community
	@echo "Building prometheus chart dependencies..."
	@helm dependency build $(HELM_CHARTS_DIR)/prometheus
	@echo "Deploying prometheus to monitoring namespace..."
	@kubectl create namespace monitoring 2>/dev/null || true
	@helm upgrade --install prometheus $(HELM_CHARTS_DIR)/prometheus \
		--namespace monitoring \
		--create-namespace \
		--wait \
		--timeout 5m
	@echo "✅ prometheus deployed to monitoring namespace"

deploy-grafana:
	@echo "Adding grafana helm repository..."
	@helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || helm repo update grafana
	@echo "Building grafana chart dependencies..."
	@helm dependency build $(HELM_CHARTS_DIR)/grafana
	@echo "Deploying grafana to monitoring namespace..."
	@kubectl create namespace monitoring 2>/dev/null || true
	@helm upgrade --install grafana $(HELM_CHARTS_DIR)/grafana \
		--namespace monitoring \
		--create-namespace \
		--wait \
		--timeout 5m
	@echo "✅ grafana deployed to monitoring namespace"

deploy-all: deploy-geth deploy-eth-loadgen deploy-prometheus deploy-grafana
	@echo "✅ All applications deployed"

infra-down:
	@helm uninstall geth-node --namespace dev 2>/dev/null || true; \
	helm uninstall eth-loadgen --namespace app 2>/dev/null || true; \
	helm uninstall prometheus --namespace monitoring 2>/dev/null || true; \
	helm uninstall grafana --namespace monitoring 2>/dev/null || true; \
	kubectl delete namespace dev 2>/dev/null || true; \
	kubectl delete namespace app 2>/dev/null || true; \
	kubectl delete namespace monitoring 2>/dev/null || true; \
	echo "✅ All applications stopped"
