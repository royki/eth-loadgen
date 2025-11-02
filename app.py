# app.py
import sys
from dotenv import load_dotenv

# Load .env file if it exists (must be before config imports)
load_dotenv()

# Now import everything else
# noqa: E402 - load_dotenv() must be called before config imports
from web3 import Web3  # noqa: E402
from src.accounts import load_prefunded_account, create_and_fund_ephemeral_accounts  # noqa: E402
from src.load_generator import apply_tps_load  # noqa: E402
from src.config import (  # noqa: E402
    RPC_URL,
    DEFAULT_GAS,
    DEFAULT_TPS,
    DEFAULT_TX_VALUE,
    DEFAULT_DURATION,
)
from src.config import (  # noqa: E402
    USE_INCREMENTAL_VALUE,
    TX_VALUE_MIN,
    TX_VALUE_MAX,
    TX_VALUE_INCREMENT,
    TX_VALUE_MODE,
)
from src.config import (  # noqa: E402
    SERVER_NUM_ACCOUNTS,
    SERVER_FUND_AMOUNT,
    SERVER_TX_MIN,
    SERVER_TX_MAX,
    SERVER_TX_INCREMENT,
)
from src.config import (  # noqa: E402
    SERVER_TX_MODE,
    SERVER_LOAD_MODE,
    SERVER_TPS,
    SERVER_DURATION,
    SERVER_GAS,
)
from src.config import METRICS_HOST, METRICS_PORT, BLOCK_POLL_INTERVAL, METRICS_WINDOW_PERIOD  # noqa: E402
from src.metrics import Metrics  # noqa: E402
from src.system_monitor import SystemMonitor  # noqa: E402
from src.block_monitor import BlockMonitor  # noqa: E402
from src.prometheus_exporter import (  # noqa: E402
    format_prometheus_metrics,
    add_system_metrics_prometheus,
)
from src.metrics_server import MetricsServer  # noqa: E402


def show_network_info(w3):
    try:
        print("Chain ID:", w3.eth.chain_id)
        print("Network ID:", w3.net.version)
        sync_status = w3.eth.syncing
        print("Syncing:", sync_status)
    except Exception as e:
        print("Failed to fetch network info:", e)


def run_server_mode(w3, pref_account, pref_key_hex):
    """Run in server mode with configuration from config.py"""
    print("=" * 60)
    print("ETH TPS Workload - SERVER MODE")
    print("=" * 60)

    # Server mode configuration from config.py
    NUM_ACCOUNTS = SERVER_NUM_ACCOUNTS
    FUND_AMOUNT = SERVER_FUND_AMOUNT
    TX_MIN = SERVER_TX_MIN
    TX_MAX = SERVER_TX_MAX
    TX_INCREMENT = SERVER_TX_INCREMENT
    VALUE_MODE = SERVER_TX_MODE  # ascending, descending, random (for value sequence)
    LOAD_MODE = SERVER_LOAD_MODE  # default, random, round-robin (for sender selection)
    TPS_SERVER = SERVER_TPS
    DURATION_SERVER = SERVER_DURATION
    GAS_SERVER = SERVER_GAS

    print("\n📋 Server Mode Configuration:")
    print(f"   Accounts: {NUM_ACCOUNTS}")
    print(f"   Fund per account: {FUND_AMOUNT} ETH")
    print(f"   TX value range: {TX_MIN} to {TX_MAX} ETH")
    print(f"   Increment: {TX_INCREMENT} ETH")
    print(f"   Value mode: {VALUE_MODE} (ascending/descending/random)")
    print(f"   Load mode: {LOAD_MODE} (default/random/round-robin)")
    print(f"   TPS: {TPS_SERVER}")
    print(f"   Duration: {DURATION_SERVER}s")

    metrics = Metrics()
    system_monitor = SystemMonitor()
    block_monitor = BlockMonitor(w3, poll_interval=BLOCK_POLL_INTERVAL)
    block_monitor.start()  # Start continuous block monitoring
    metrics_server = MetricsServer(host=METRICS_HOST, port=METRICS_PORT)
    metrics_server.start(w3, [], pref_account, block_monitor=block_monitor)

    # Start continuous metrics reporting (independent of test lifecycle)
    # Like BlockMonitor - runs continuously in background
    metrics.start(window_period=METRICS_WINDOW_PERIOD)

    print("\n⏳ Creating and funding accounts...")
    ephemeral_accounts = create_and_fund_ephemeral_accounts(w3, pref_account, pref_key_hex, NUM_ACCOUNTS, FUND_AMOUNT)
    print(f"✅ Created {len(ephemeral_accounts)} ephemeral accounts")

    # Wait for transactions to be mined
    import time

    print("Waiting for funding transactions to be mined...")
    time.sleep(10)

    # Store balances
    balances = {
        "prefunded": {
            "address": pref_account.address,
            "balance_eth": float(w3.from_wei(w3.eth.get_balance(pref_account.address), "ether")),
        },
        "ephemeral": [],
    }

    for acct, _ in ephemeral_accounts:
        balance = w3.eth.get_balance(acct.address)
        balances["ephemeral"].append(
            {
                "address": acct.address,
                "balance_eth": float(w3.from_wei(balance, "ether")),
            }
        )

    metrics.set_account_balances(balances)
    metrics_server.ephemeral_accounts = ephemeral_accounts

    # Update metrics server
    report = metrics.report()
    metrics_server.update_metrics(report, mode="default")

    print("\n💰 Balances loaded:")
    print(f"   Prefunded: {balances['prefunded']['balance_eth']:.2f} ETH")
    print(
        f"   Ephemeral (avg): {sum([a['balance_eth'] for a in balances['ephemeral']]) / len(balances['ephemeral']):.2f} ETH"
    )

    # Start load test with preset values
    print("\n🚀 Starting automated load test...")
    metrics.reset()

    tx_value_config = (TX_MIN, TX_MAX, TX_INCREMENT, VALUE_MODE)
    metrics.set_tx_value_config(
        {
            "TX_VALUE_MIN": TX_MIN,
            "TX_VALUE_MAX": TX_MAX,
            "TX_VALUE_INCREMENT": TX_INCREMENT,
            "TX_VALUE_MODE": VALUE_MODE,
        }
    )

    # Capture baseline system metrics before test starts
    system_monitor.capture_baseline()

    try:
        apply_tps_load(
            w3,
            pref_account,
            pref_key_hex,
            ephemeral_accounts,
            TPS_SERVER,
            DURATION_SERVER,
            GAS_SERVER,
            tx_value_config,
            LOAD_MODE,
            metrics,
            system_monitor,
        )
    except Exception as e:
        print(f"\n❌ ERROR during load test: {e}", flush=True)
        import traceback

        traceback.print_exc()
        raise

    # Update metrics after load test
    print("\n📊 Generating metrics report...", flush=True)
    report = metrics.report()
    sys_summary = system_monitor.get_summary() if system_monitor.samples else None
    metrics_server.update_metrics(report, sys_summary, LOAD_MODE)

    # Print metrics report
    print("\n" + "=" * 60, flush=True)
    print("📊 METRICS REPORT", flush=True)
    print("=" * 60, flush=True)
    print("\n=== Transaction Metrics ===", flush=True)
    for key, value in report.items():
        if key != "account_balances":  # Skip account_balances, will print separately
            print(f"  {key}: {value}", flush=True)

    if sys_summary:
        print("\n=== System Metrics ===", flush=True)
        for key, value in sys_summary.items():
            print(f"  {key}: {value}", flush=True)

    # Add block production time metrics
    block_stats = block_monitor.get_stats()
    if block_stats:
        print("\n=== Block Production Time ===", flush=True)
        current_block_number = block_stats.get("current_block_number")
        current_interval = block_stats.get("current_block_interval_seconds")
        if current_block_number is not None and current_interval is not None:
            print(
                f"  eth_block_production_time_seconds: {current_interval:.2f} seconds (block {current_block_number})",
                flush=True,
            )
        elif current_interval is not None:
            print(
                f"  eth_block_production_time_seconds: {current_interval:.2f} seconds",
                flush=True,
            )
        avg_interval = block_stats.get("average_block_interval_seconds")
        if avg_interval is not None:
            print(
                f"  eth_block_production_time_avg_seconds: {avg_interval:.2f} seconds",
                flush=True,
            )
        if current_block_number is not None:
            print(
                f"  eth_block_total_blocks_tracked: {block_stats.get('total_blocks_tracked', 0)} (current block: {current_block_number})",
                flush=True,
            )
        else:
            print(f"  eth_block_total_blocks_tracked: {block_stats.get('total_blocks_tracked', 0)}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("📊 SERVER MODE COMPLETE", flush=True)
    print("=" * 60, flush=True)
    print(f"Metrics available at: http://{METRICS_HOST}:{METRICS_PORT}/metrics", flush=True)

    # NOTE: Periodic metrics reporting continues independently
    # It was started when server started and runs continuously in background
    # No need to stop it here - it runs independently like BlockMonitor

    print("\nPress Ctrl+C to exit (server keeps running)...", flush=True)

    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down...")
        metrics.stop()  # Stop continuous metrics reporting
        block_monitor.stop()
        metrics_server.stop()


def main():
    # Check for server mode
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        print("Starting in SERVER MODE...")
    else:
        print("Starting in CLI MODE...")
        print("Use 'python3 app.py --server' for server mode\n")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("ERROR: cannot connect to RPC at", RPC_URL)
        return

    # Load prefunded account from mounted UTC keystore
    try:
        pref_account, pref_key_hex = load_prefunded_account()
    except Exception as e:
        print("Failed to load prefunded account from UTC file:", e)
        return

    print(f"Prefunded account: {pref_account.address}")
    try:
        balance = w3.eth.get_balance(pref_account.address)
        print("Balance:", w3.from_wei(balance, "ether"), "ETH")
    except Exception as e:
        print("Failed to read prefunded balance:", e)

    # Choose mode
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        run_server_mode(w3, pref_account, pref_key_hex)
        return

    # Otherwise run CLI mode
    run_cli_mode(w3, pref_account, pref_key_hex)


def run_cli_mode(w3, pref_account, pref_key_hex):
    """Run in interactive CLI mode (original menu-based interface)."""
    print("=" * 60)
    print("ETH TPS Workload - INTERACTIVE CLI MODE")
    print("=" * 60)

    ephemeral_accounts = []  # List of (account, private_key) tuples
    metrics = Metrics()
    system_monitor = SystemMonitor()
    block_monitor = BlockMonitor(w3, poll_interval=BLOCK_POLL_INTERVAL)
    block_monitor.start()  # Start continuous block monitoring
    metrics_server = MetricsServer(host=METRICS_HOST, port=METRICS_PORT)
    metrics_server.start(w3, ephemeral_accounts, pref_account, block_monitor=block_monitor)

    while True:
        print("\nMenu:")
        print("1. Show network info")
        print("2. Create & fund ephemeral accounts")
        print("3. Apply TPS load")
        print("4. Print metrics report")
        print("5. Export Prometheus metrics")
        print("6. Show metrics URL")
        print("7. Show account balances")
        print("8. Quit")
        choice = input("Choose: ").strip()

        if choice == "1":
            show_network_info(w3)
        elif choice == "2":
            try:
                n = int(input("Number of ephemeral accounts: ").strip())
                eth_amt = float(input("ETH to fund each: ").strip())
            except Exception:
                print("Invalid number")
                continue
            ephemeral_accounts = create_and_fund_ephemeral_accounts(w3, pref_account, pref_key_hex, n, eth_amt)
            print(f"Created {len(ephemeral_accounts)} ephemeral accounts")

            # Store account balances for metrics export
            balances = {
                "prefunded": {
                    "address": pref_account.address,
                    "balance_eth": float(w3.from_wei(w3.eth.get_balance(pref_account.address), "ether")),
                },
                "ephemeral": [],
            }

            for acct, _ in ephemeral_accounts:
                balance = w3.eth.get_balance(acct.address)
                balances["ephemeral"].append(
                    {
                        "address": acct.address,
                        "balance_eth": float(w3.from_wei(balance, "ether")),
                    }
                )

            metrics.set_account_balances(balances)

            # Update metrics server with reference to ephemeral accounts
            metrics_server.ephemeral_accounts = ephemeral_accounts

            # Update metrics server
            report = metrics.report()
            metrics_server.update_metrics(report, mode="default")

        elif choice == "3":
            if not ephemeral_accounts:
                print("You must create & fund ephemeral accounts first.")
                continue
            try:
                tps = int(input(f"TPS [{DEFAULT_TPS}]: ").strip() or DEFAULT_TPS)
                gas = int(input(f"Gas [{DEFAULT_GAS}]: ").strip() or DEFAULT_GAS)

                # Ask about incremental values
                use_inc = input(f"Use incremental tx values? [{USE_INCREMENTAL_VALUE}]: ").strip()
                use_inc = use_inc.lower() if use_inc else str(USE_INCREMENTAL_VALUE).lower()
                use_incremental = use_inc in ("yes", "y", "true", "1")

                if use_incremental:
                    tx_value_min = float(input(f"Min tx value ETH [{TX_VALUE_MIN}]: ").strip() or TX_VALUE_MIN)
                    tx_value_max = float(input(f"Max tx value ETH [{TX_VALUE_MAX}]: ").strip() or TX_VALUE_MAX)

                    # Validate and guide increment input
                    range_size = tx_value_max - tx_value_min
                    print("\n💡 Guidance for increment:")
                    print(f"   - Range: {tx_value_min} to {tx_value_max} ETH (span: {range_size:.6f} ETH)")
                    print(f"   - Typical: Use {range_size/10:.6f} ETH to generate ~10 values")
                    print("   - Example: Range 0.001-0.01 → Use increment ~0.001 for 10 values")
                    print(f"   - Increment should be: 0 to {range_size:.6f} ETH")

                    while True:
                        tx_value_inc_input = (
                            input(f"\nIncrement ETH [{TX_VALUE_INCREMENT}]: ").strip() or TX_VALUE_INCREMENT
                        )
                        tx_value_inc = float(tx_value_inc_input)

                        # Check if increment is reasonable
                        if tx_value_inc > (tx_value_max - tx_value_min):
                            print(f"\n⚠️  ERROR: Increment ({tx_value_inc}) is larger than range ({range_size:.6f})")
                            print(f"   This will only generate 1 value: {tx_value_min} ETH")
                            print(f"   Please use increment <= {range_size:.6f}")
                            proceed = input("Use this anyway? (y/n) [n]: ").strip().lower()
                            if proceed != "y":
                                continue  # Ask again

                        # Check how many values will be generated
                        num_values = int((tx_value_max - tx_value_min) / tx_value_inc) + 1

                        if num_values < 2:
                            suggested_inc = (tx_value_max - tx_value_min) / 10  # Generate ~10 values
                            print(f"\n⚠️  WARNING: Only {num_values} value(s) will be generated")
                            print(f"   Suggested increment for ~10 values: {suggested_inc:.6f}")
                            proceed = input("Use this anyway? (y/n) [n]: ").strip().lower()
                            if proceed != "y":
                                continue  # Ask again

                        # Success - show confirmation
                        if num_values > 1:
                            print(f"\n✓ Confirmed: Will generate {num_values} values")
                            print(f"  Values: {tx_value_min}, {tx_value_min + tx_value_inc}, ..., {tx_value_max}")
                        break

                    tx_value_mode = (
                        input(f"\nValue mode (ascending/descending/random) [{TX_VALUE_MODE}]: ").strip()
                        or TX_VALUE_MODE
                    )
                    tx_value = (tx_value_min, tx_value_max, tx_value_inc, tx_value_mode)
                else:
                    tx_value = float(input(f"Fixed tx value ETH [{DEFAULT_TX_VALUE}]: ").strip() or DEFAULT_TX_VALUE)

                duration = int(input(f"Duration seconds [{DEFAULT_DURATION}]: ").strip() or DEFAULT_DURATION)
                mode = input("Mode (default/random/round-robin) [default]: ").strip() or "default"
            except Exception as e:
                print("Invalid input", e)
                continue
            # Reset metrics before each load test
            metrics.reset()

            # Store TX value configuration for metrics
            if isinstance(tx_value, tuple):
                metrics.set_tx_value_config(
                    {
                        "TX_VALUE_MIN": tx_value[0],
                        "TX_VALUE_MAX": tx_value[1],
                        "TX_VALUE_INCREMENT": tx_value[2],
                        "TX_VALUE_MODE": tx_value[3],
                    }
                )
            else:
                metrics.set_tx_value_config({"TX_VALUE_FIXED": tx_value})

            # Capture baseline system metrics before test starts
            system_monitor.capture_baseline()

            apply_tps_load(
                w3,
                pref_account,
                pref_key_hex,
                ephemeral_accounts,
                tps,
                duration,
                gas,
                tx_value,
                mode,
                metrics,
                system_monitor,
            )

            # Update metrics server after load test
            report = metrics.report()
            sys_summary = system_monitor.get_summary() if system_monitor.samples else None
            metrics_server.update_metrics(report, sys_summary, mode=mode)
        elif choice == "4":
            report = metrics.report()
            print("\n=== Transaction Metrics ===")
            print(report)

            # Add system metrics if available
            if system_monitor.samples:
                sys_summary = system_monitor.get_summary()
                print("\n=== System Metrics ===")
                print(sys_summary)

            # Add block production time metrics
            block_stats = block_monitor.get_stats()
            if block_stats:
                print("\n=== Block Production Time ===")
                current_block_number = block_stats.get("current_block_number")
                current_interval = block_stats.get("current_block_interval_seconds")
                if current_block_number is not None and current_interval is not None:
                    print(
                        f"  eth_block_production_time_seconds: {current_interval:.2f} seconds (block {current_block_number})"
                    )
                elif current_interval is not None:
                    print(f"  eth_block_production_time_seconds: {current_interval:.2f} seconds")
                avg_interval = block_stats.get("average_block_interval_seconds")
                if avg_interval is not None:
                    print(f"  eth_block_production_time_avg_seconds: {avg_interval:.2f} seconds")
                if current_block_number is not None:
                    print(
                        f"  eth_block_total_blocks_tracked: {block_stats.get('total_blocks_tracked', 0)} (current block: {current_block_number})"
                    )
                else:
                    print(f"  eth_block_total_blocks_tracked: {block_stats.get('total_blocks_tracked', 0)}")
        elif choice == "5":
            # Export Prometheus metrics
            report = metrics.report()

            # Re-read account balances from chain to get current values
            if ephemeral_accounts:
                balances = {
                    "prefunded": {
                        "address": pref_account.address,
                        "balance_eth": float(w3.from_wei(w3.eth.get_balance(pref_account.address), "ether")),
                    },
                    "ephemeral": [],
                }

                for acct, _ in ephemeral_accounts:
                    balance = w3.eth.get_balance(acct.address)
                    balances["ephemeral"].append(
                        {
                            "address": acct.address,
                            "balance_eth": float(w3.from_wei(balance, "ether")),
                        }
                    )

                report["account_balances"] = balances

            print("\n=== Prometheus Metrics Export ===")

            # Get the mode from latest test (default for now)
            mode = "default"
            prometheus_output = format_prometheus_metrics(report, mode=mode)
            print(prometheus_output)

            # Add system metrics if available
            if system_monitor.samples:
                sys_summary = system_monitor.get_summary()
                sys_metrics = add_system_metrics_prometheus(sys_summary)
                print("\n" + sys_metrics)

            # Optionally save to file
            save = input("\nSave to file? (y/n) [n]: ").strip().lower()
            if save == "y":
                filename = "metrics.prom"
                with open(filename, "w") as f:
                    f.write(prometheus_output)
                    if system_monitor.samples:
                        f.write("\n\n" + sys_metrics)
                print(f"Metrics saved to {filename}")
        elif choice == "6":
            # Show metrics URL
            url = metrics_server.get_url()
            print("\n=== Metrics Endpoint ===")
            print(f"View metrics at: {url}")
            print("\nTo curl metrics:")
            print(f"  curl {url}")
            print("\nFor Prometheus scraping:")
            print("  Add to prometheus.yml:")
            print("  scrape_configs:")
            print("    - job_name: 'eth-loadgen'")
            print("      static_configs:")
            print(f"        - targets: ['{METRICS_HOST}:{METRICS_PORT}']")
        elif choice == "7":
            # Show account balances
            print("\n=== Account Balances ===")

            # Prefunded account
            print("\nPrefunded Account:")
            print(f"  Address: {pref_account.address}")
            try:
                balance = w3.eth.get_balance(pref_account.address)
                balance_eth = w3.from_wei(balance, "ether")
                print(f"  Balance: {balance_eth:.6f} ETH")
            except Exception as e:
                print(f"  Error reading balance: {e}")

            # Ephemeral accounts
            if ephemeral_accounts:
                print(f"\nEphemeral Accounts ({len(ephemeral_accounts)}):")
                for i, (acct, _) in enumerate(ephemeral_accounts, 1):
                    try:
                        balance = w3.eth.get_balance(acct.address)
                        balance_eth = w3.from_wei(balance, "ether")
                        print(f"  [{i}] {acct.address}: {balance_eth:.6f} ETH")
                    except Exception as e:
                        print(f"  [{i}] {acct.address}: Error - {e}")
            else:
                print("\nNo ephemeral accounts created yet.")

        elif choice == "8":
            print("Exiting.")
            metrics_server.stop()
            break
        else:
            print("Unknown option")


if __name__ == "__main__":
    main()
