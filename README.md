# eth-loadgen

Ethereum TPS Workload Generator

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
  - tps, rps, mgas_per_sec, avg_latency_sec, p50_latency_sec, p95_latency_sec, success_rate_%
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

### Check block production time

```bash
make check-block-time WAIT_NEXT=1 TIMEOUT=120 RPC_URL=http://localhost:8545
```
