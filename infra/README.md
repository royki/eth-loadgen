# Infrastructure Helm Charts

This directory contains Helm charts for deploying the Ethereum load testing infrastructure on Kubernetes.

## Applications

### 1. **geth-node**

Ethereum Geth node running in development mode. Provides the blockchain network for load testing.

- **Namespace:** `dev`
- **Ports:** HTTP (8545), WebSocket (8546), Metrics (6060)
- **Features:**
  - Dev mode with configurable block period
  - HTTP and WebSocket RPC endpoints
  - Prometheus metrics endpoint
  - Persistent storage for blockchain data

### 2. **eth-loadgen**

Ethereum load generator that creates and sends transactions to the Geth node.

- **Namespace:** `app`
- **Port:** Metrics (9000)
- **Features:**
  - Generates configurable transaction load
  - Supports multiple load modes (random, ascending, etc.)
  - Exposes Prometheus metrics for monitoring
  - Manages multiple test accounts

### 3. **prometheus**

Metrics collection and storage system. Scrapes metrics from `geth-node` and `eth-loadgen`.

- **Namespace:** `monitoring`
- **Port:** 9090
- **Features:**
  - Scrapes metrics from both geth-node and eth-loadgen applications

### 4. **grafana**

Dashboards for monitoring metrics from geth-node and eth-loadgen applications.

- **Namespace:** `monitoring`
- **Port:** 3000
- **Features:**
  - Pre-configured dashboards for Ethereum load testing
  - Pre-configured dashboards for Geth node monitoring
  - Connected to Prometheus datasource

## Deployment

See the main [README.md](../README.md) for deployment instructions using the Makefile.
