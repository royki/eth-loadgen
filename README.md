# Ethereum TPS Workload Generator app with local dev network

## Features

- Apply total tps transactions per second for duration_sec seconds.
- App mode: "server" (default), "cli" (interactive)
- Apply Load mode: "default" (all tx from prefunded), "random", "round-robin"
- Ephemeral Accounts: only for dev network
  - create and fund ephemeral accounts
- Configurable parameters: Check `src/config.py` or `.env.sample` for details
- Metrics:
  - block monitor
  - system monitor
  - tps, rps, mgas_per_sec, avg_latency_sec, p50_latency_sec, p95_latency_sec, success_rate_%, failed_rate_% etc.
  - prometheus exporter

## Prerequisites

- Python 3.11, pip, and virtualenv
- Docker v24.0.0+
- Docker Compose v2.18.1+

## Installation

### Install dependencies and run locally

```bash
git clone https://github.com/royki/eth-loadgen.git
cd eth-loadgen
# install dependencies
make install
# run locally in interactive CLI mode
make run
# run locally in server mode, predefined parameters in .env
make run-server
# run linting checks
make check-format (run formatting checks)
make lint (run linting checks)
make pylint (run pylint checks)
make check-syntax (run syntax checks)
make check-lint (run all linting checks)
make fix (auto-fix formatting)
```

### Build Image and run with Docker

```bash
# build image
make docker-build
# run container
make docker-up
# show logs
make docker-logs
# stop container
make docker-down
# restart container
make docker-restart
# clean up
make docker-clean
```

### Infrastructure commands to deploy applications using Helm charts

**Note:** _Local kubernetes cluster should have installed with ingress, nginx-ingress-controller,storage-provisioner, kubernetes default-storageclass. You can use `minikube` and enable addons like `ingress`, `default-storageclass` and `storage-provisioner`._

```bash
# check if local Kubernetes cluster is running
make infra-check
# deploy geth-node to dev namespace
make deploy-geth
# deploy eth-loadgen to app namespace
make deploy-eth-loadgen
# deploy prometheus to monitoring namespace
make deploy-prometheus
# deploy grafana to monitoring namespace
make deploy-grafana
# deploy all applications at once
make deploy-all
# tear down all applications at once
make infra-down
```

### Check block production time and block persistence

```bash
# To check the block, geth-node must be running on local kubernetes
make check-network-block-info

```bash

Setting up port-forward for geth-node-service...
✅ Port-forward established (PID: 69206)
Using RPC_URL=<http://localhost:8545>
Using TARGET_INTERVAL=6
Using CONTINUOUS=1
Using NUM_BLOCKS=
✅ Connected to RPC at <http://localhost:8545>
🌐 Chain ID: 1337
📏 Current block height: 39
🟢 Node is fully synced
⏱️ Starting monitoring from block 39 @ 2025-11-11 12:45:06 UTC

====================================================================================================
📦 BLOCK 39 → 40
====================================================================================================

⏱️ Production Time: 6.00s (target: ~6.0s)
✅ Block interval within expected range.
🕒 Previous Block Time: 2025-11-11 12:45:06 UTC
🕒 Current Block Time:  2025-11-11 12:45:12 UTC
✅ Block 40 persists in canonical chain (hash matches).
⏳ Block 40 pending finalization (finalized block: 32, lag: 8 blocks)
----------------------------------------------------------------------------------------------------
```

- `scripts/check_block_time.py` script can be used for external RPC URL as well.
  - `-c` check the block time continuously.
  - `-n` check the block time for the given number of blocks.
  - `-t` target block time in seconds (default: 6 seconds).

```bash
python3 scripts/check_block_time.py --rpc-url <external_rpc_url> -c [ with continuous mode]
python3 scripts/check_block_time.py --rpc-url <external_rpc_url> -n <num_blocks> [ with num_blocks mode]
```

### Access applications

- To access applications, there are two ways:
  - Using ingress controller
  - Using port-forwarding
- Using ingress controller, access applications through the ingress controller.
  - Before accessing applications using ingress controller, add the following entries to `/etc/hosts` file for local development:
    - `local k8s node_ip geth-node.local eth-loadgen.local grafana.local prometheus.local`
    - `192.168.49.2    geth-node.local eth-loadgen.local grafana.local prometheus.local` [using minikube - `minikube ip`]
- Then, access applications using the following URLs:
  - to access Grafana, use the following URL:
    - <http://grafana.local>
  - to access Prometheus, use the following URL:
    - <http://prometheus.local>
  - to access eth-loadgen, use the following URL:
    - <http://eth-loadgen.local/metrics>
  - to access geth-node, use the following URL:
    - <http://geth-node.local:80>
- Using port-forwarding, access applications directly from your local machine.
  - to access Prometheus, use the following command:
    - `kubectl port-forward -n monitoring service/prometheus-server 9090:9090`
    - access URL: <http://localhost:9090>
  - to access Grafana, use the following command:
    - `kubectl port-forward -n monitoring service/grafana 3000:3000`
    - access URL: <http://localhost:3000>
  - to access eth-loadgen, use the following command:
    - `kubectl port-forward -n app service/eth-loadgen-service 9000:9000`
    - access URL: <http://localhost:9000>
  - to access geth-node, use the following command:
    - `kubectl port-forward -n dev service/geth-node-service 8545:8545`
    - access URL: <http://localhost:8545>

### Eth-loadgen Application details

Python application that generates and sends transactions to the Geth node for load testing.

- App mode: "server" (default), "cli" (interactive)
  - In server mode, application takes values either from `config.py` (default values) or fron `.env` file.
  - In cli mode, application takes values from `config.py` (default values) or fron `.env` file or from user input.
- Configurable transaction load (TPS, duration, value range, gas limit, etc.)
- Load modes (random, round-robin, default)
- Ephemeral account creation and funding
- Real-time metrics via Prometheus exporter
- Block and system monitoring

#### Environment Variables

**Core Configuration:**

- `RPC_URL` - Ethereum node RPC endpoint (default: `http://localhost:8545`)
- `SERVER_TPS` - Target transactions per second (default: `5`)
- `SERVER_DURATION` - Test duration in seconds (default: `60`)
- `SERVER_NUM_ACCOUNTS` - Number of ephemeral accounts to create (default: `100`)
- `SERVER_LOAD_MODE` - Transaction distribution mode: `random`, `round-robin`, or `default` (default: `random`)
- `SERVER_TX_MIN` / `SERVER_TX_MAX` - Transaction value range in ETH (default: `0.1` - `100`)
- `SERVER_TX_MODE` - Transaction value progression: `ascending`, `descending`, or `random` (default: `ascending`). Ascending mode means the transaction value will increase from `SERVER_TX_MIN` to `SERVER_TX_MAX` in steps of `SERVER_TX_INCREMENT`.
- `SERVER_TX_INCREMENT` - Transaction value increment in ETH (default: `0.5`).
- `SERVER_TX_MAX` - Maximum transaction value in ETH (default: `100`).
- `SERVER_TX_MIN` - Minimum transaction value in ETH (default: `0.1`).
- `SERVER_GAS` - Gas limit per transaction (default: `21000`)

**Metrics Configuration:**

- `METRICS_PORT` - Prometheus metrics server port (default: `9000`)
- `METRICS_WINDOW_PERIOD` - Rolling window period for time-series metrics in seconds (default: `20`)

**Keystore Configuration:**

- `UTC_FILE_PATH` - Path to UTC keystore file
- `PRIVATE_KEY` - Private key for prefunded account (alternative to UTC file)

#### Metrics

- **TPS Variance** - Difference between actual and requested TPS (`actual_tps - requested_tps`). Positive values indicate exceeding target, negative indicates below target.
- **p50_latency_sec** - 50th percentile (median) transaction latency.
- **p95_latency_sec** - 95th percentile transaction latency. 95% of transactions complete faster than this value. Useful for identifying tail latency issues.
