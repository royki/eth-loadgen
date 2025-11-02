# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


# Load from environment variables with defaults
def get_env(key, default):
    """Get environment variable with optional type conversion"""
    value = os.getenv(key)
    if value is None:
        return default
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


# RPC Configuration
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")

# Default CLI Mode Settings
DEFAULT_GAS = int(os.getenv("DEFAULT_GAS", "21000"))
DEFAULT_TX_VALUE = float(os.getenv("DEFAULT_TX_VALUE", "0.01"))
DEFAULT_CONCURRENCY = int(os.getenv("DEFAULT_CONCURRENCY", "5"))
DEFAULT_TPS = int(os.getenv("DEFAULT_TPS", "5"))
DEFAULT_DURATION = int(os.getenv("DEFAULT_DURATION", "30"))

# Incremental Transaction Value Configuration (CLI mode)
USE_INCREMENTAL_VALUE = get_env("USE_INCREMENTAL_VALUE", True)
TX_VALUE_MIN = float(os.getenv("TX_VALUE_MIN", "0.001"))
TX_VALUE_MAX = float(os.getenv("TX_VALUE_MAX", "0.01"))
TX_VALUE_INCREMENT = float(os.getenv("TX_VALUE_INCREMENT", "0.001"))
TX_VALUE_MODE = os.getenv("TX_VALUE_MODE", "ascending")

# Server Mode Configuration
SERVER_NUM_ACCOUNTS = int(os.getenv("SERVER_NUM_ACCOUNTS", "100"))
SERVER_FUND_AMOUNT = float(os.getenv("SERVER_FUND_AMOUNT", "10000"))
SERVER_TX_MIN = float(os.getenv("SERVER_TX_MIN", "0.1"))
SERVER_TX_MAX = float(os.getenv("SERVER_TX_MAX", "100"))
SERVER_TX_INCREMENT = float(os.getenv("SERVER_TX_INCREMENT", "0.5"))
SERVER_TX_MODE = os.getenv("SERVER_TX_MODE", "ascending")
SERVER_LOAD_MODE = os.getenv("SERVER_LOAD_MODE", "random")
SERVER_TPS = int(os.getenv("SERVER_TPS", "5"))
SERVER_DURATION = int(os.getenv("SERVER_DURATION", "60"))
SERVER_GAS = int(os.getenv("SERVER_GAS", "21000"))

# Server Test Re-execution Configuration
# SERVER_NUM_RUNS: Number of test runs. Default: "1" (single run)
#   - "1" or any positive integer: Run that many times
#   - "continuous" or "0": Run continuously until stopped
SERVER_NUM_RUNS = os.getenv("SERVER_NUM_RUNS", "1")
# SERVER_TEST_INTERVAL: Seconds to wait between test runs (default: 60)
SERVER_TEST_INTERVAL = int(os.getenv("SERVER_TEST_INTERVAL", "60"))

# Metrics Server Configuration
METRICS_HOST = os.getenv("METRICS_HOST", "0.0.0.0")  # 0.0.0.0 for Docker, set to localhost in .env for host
METRICS_PORT = int(os.getenv("METRICS_PORT", "9000"))

# Block Monitor Configuration
BLOCK_POLL_INTERVAL = float(os.getenv("BLOCK_POLL_INTERVAL", "1.0"))  # Seconds between RPC polls for block monitoring

# Metrics Time-Series Configuration
METRICS_WINDOW_PERIOD = int(
    os.getenv("METRICS_WINDOW_PERIOD", "5")
)  # Seconds for time-series metrics window (rolling window period)

# Keystore Configuration
UTC_FILE_PATH = os.getenv("UTC_FILE_PATH")
UTC_PASSWORD = os.getenv("UTC_PASSWORD", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")  # Alternative to UTC file for prefunded account


# Auto-detect UTC file if not set
def find_utc_file():
    """Search for UTC keystore file in common locations"""
    if UTC_FILE_PATH and Path(UTC_FILE_PATH).exists():
        return UTC_FILE_PATH

    # Get search directories from environment or use defaults
    search_paths_env = os.getenv("UTC_SEARCH_PATHS", "")
    if search_paths_env:
        search_dirs = [Path(p.strip()) for p in search_paths_env.split(",")]
    else:
        # Default search: current dir, parent, parent of parent, keystores/ (no hardcoded dir names)
        current = Path.cwd()
        search_dirs = [
            current,  # Current working directory
            current.parent,  # Parent directory
            current.parent.parent,  # Parent of parent
            current / "keystores",  # keystores/ directory (if exists)
        ]

    for search_dir in search_dirs:
        if search_dir.exists():
            for file in search_dir.glob("UTC--*"):
                return str(file)

    return None


# Auto-detect and set UTC_FILE_PATH if not configured
if not UTC_FILE_PATH or UTC_FILE_PATH.strip() == "":
    detected_path = find_utc_file()
    if detected_path:
        UTC_FILE_PATH = detected_path
        print(f"Auto-detected UTC keystore: {UTC_FILE_PATH}")
    else:
        print("⚠️  UTC_FILE_PATH not configured. Set it in .env file or config.")
        print("   Example: UTC_FILE_PATH=/path/to/keystore/UTC--...")
