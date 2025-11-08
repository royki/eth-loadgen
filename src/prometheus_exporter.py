# prometheus_exporter.py
"""
Export metrics in Prometheus exposition format.
Formats metrics for scraping by Prometheus/Grafana.
"""


def format_prometheus_metrics(metrics_data, mode="default"):
    """
    Format metrics in Prometheus exposition format.

    Args:
        metrics_data: Dict from metrics.report()
        mode: Transaction mode (default/random/round-robin)

    Returns:
        str: Prometheus-formatted metrics
    """
    lines = []

    # Transaction counter
    lines.append("# HELP eth_tx_total Total transactions sent")
    lines.append("# TYPE eth_tx_total counter")
    lines.append(f'eth_tx_total{{mode="{mode}"}} {metrics_data.get("total_sent", 0)}')

    # Success/Fail counts
    lines.append("# HELP eth_tx_success_total Successful transactions")
    lines.append("# TYPE eth_tx_success_total counter")
    lines.append(f'eth_tx_success_total{{mode="{mode}"}} {metrics_data.get("success", 0)}')

    lines.append("# HELP eth_tx_fail_total Failed transactions")
    lines.append("# TYPE eth_tx_fail_total counter")
    lines.append(f'eth_tx_fail_total{{mode="{mode}"}} {metrics_data.get("fail", 0)}')

    # Success rate gauge
    lines.append("# HELP eth_tx_success_rate_percent Success rate percentage")
    lines.append("# TYPE eth_tx_success_rate_percent gauge")
    lines.append(f'eth_tx_success_rate_percent{{mode="{mode}"}} {metrics_data.get("success_rate_%", 0)}')

    # Latency metrics (as histogram-like)
    lines.append("# HELP eth_tx_latency_seconds Transaction latency in seconds")
    lines.append("# TYPE eth_tx_latency_seconds summary")
    lines.append(f'eth_tx_latency_seconds{{mode="{mode}",quantile="0.5"}} {metrics_data.get("p50_latency_sec", 0)}')
    lines.append(f'eth_tx_latency_seconds{{mode="{mode}",quantile="0.95"}} {metrics_data.get("p95_latency_sec", 0)}')
    lines.append(
        f'eth_tx_latency_seconds_sum{{mode="{mode}"}} {metrics_data.get("avg_latency_sec", 0) * metrics_data.get("total_sent", 0)}'
    )
    lines.append(f'eth_tx_latency_seconds_count{{mode="{mode}"}} {metrics_data.get("total_sent", 0)}')

    # RPS
    lines.append("# HELP eth_tx_rps Requests per second")
    lines.append("# TYPE eth_tx_rps gauge")
    lines.append(f'eth_tx_rps{{mode="{mode}"}} {metrics_data.get("rps", 0)}')

    # TPS metrics (requested vs actual)
    requested_tps = metrics_data.get("requested_tps")
    if requested_tps is not None:
        lines.append("# HELP eth_tx_requested_tps Requested transactions per second (target)")
        lines.append("# TYPE eth_tx_requested_tps gauge")
        lines.append(f'eth_tx_requested_tps{{mode="{mode}"}} {requested_tps}')

    actual_tps = metrics_data.get("actual_tps")
    if actual_tps is not None:
        lines.append("# HELP eth_tx_actual_tps Actual transactions per second (achieved)")
        lines.append("# TYPE eth_tx_actual_tps gauge")
        lines.append(f'eth_tx_actual_tps{{mode="{mode}"}} {actual_tps}')

    tps_variance = metrics_data.get("tps_variance")
    if tps_variance is not None:
        lines.append("# HELP eth_tx_tps_variance Difference between actual and requested TPS (actual - requested)")
        lines.append("# TYPE eth_tx_tps_variance gauge")
        lines.append(f'eth_tx_tps_variance{{mode="{mode}"}} {tps_variance}')

    tps_accuracy = metrics_data.get("tps_accuracy_%")
    if tps_accuracy is not None:
        lines.append("# HELP eth_tx_tps_accuracy_percent TPS accuracy percentage (actual/requested * 100)")
        lines.append("# TYPE eth_tx_tps_accuracy_percent gauge")
        lines.append(f'eth_tx_tps_accuracy_percent{{mode="{mode}"}} {tps_accuracy}')

    # Gas metrics
    lines.append("# HELP eth_tx_gas_total Total gas used")
    lines.append("# TYPE eth_tx_gas_total counter")
    lines.append(f'eth_tx_gas_total{{mode="{mode}"}} {metrics_data.get("total_gas_used", 0)}')

    lines.append("# HELP eth_tx_mgas_per_sec Million gas per second")
    lines.append("# TYPE eth_tx_mgas_per_sec gauge")
    lines.append(f'eth_tx_mgas_per_sec{{mode="{mode}"}} {metrics_data.get("mgas_per_sec", 0)}')

    # Duration
    lines.append("# HELP eth_test_duration_seconds Test duration in seconds")
    lines.append("# TYPE eth_test_duration_seconds gauge")
    lines.append(f'eth_test_duration_seconds{{mode="{mode}"}} {metrics_data.get("duration_sec", 0)}')

    # ETH sent
    lines.append("# HELP eth_tx_value_total_ether Total ETH sent in transactions")
    lines.append("# TYPE eth_tx_value_total_ether counter")
    lines.append(f'eth_tx_value_total_ether{{mode="{mode}"}} {metrics_data.get("total_eth_sent", 0)}')

    # Account balances
    if "account_balances" in metrics_data:
        account_balances = metrics_data["account_balances"]

        lines.append("# HELP eth_account_balance_ether Account balance in ETH")
        lines.append("# TYPE eth_account_balance_ether gauge")

        # Prefunded account
        if "prefunded" in account_balances:
            prefunded = account_balances["prefunded"]
            lines.append(
                f'eth_account_balance_ether{{account="{prefunded["address"]}",account_type="prefunded",mode="{mode}"}} {prefunded["balance_eth"]}'
            )

        # Ephemeral accounts
        if "ephemeral" in account_balances:
            for i, acct in enumerate(account_balances["ephemeral"]):
                lines.append(
                    f'eth_account_balance_ether{{account="{acct["address"]}",account_type="ephemeral",account_index="{i}",mode="{mode}"}} {acct["balance_eth"]}'
                )

    # TX value configuration
    if "tx_value_config" in metrics_data:
        tx_config = metrics_data["tx_value_config"]
        if "TX_VALUE_FIXED" in tx_config:
            lines.append("# HELP eth_tx_value_fixed_ether Fixed transaction value in ETH")
            lines.append("# TYPE eth_tx_value_fixed_ether gauge")
            lines.append(f'eth_tx_value_fixed_ether{{mode="{mode}"}} {tx_config["TX_VALUE_FIXED"]}')
        else:
            lines.append("# HELP eth_tx_value_min_ether Minimum transaction value in ETH")
            lines.append("# TYPE eth_tx_value_min_ether gauge")
            lines.append(f'eth_tx_value_min_ether{{mode="{mode}"}} {tx_config.get("TX_VALUE_MIN", 0)}')

            lines.append("# HELP eth_tx_value_max_ether Maximum transaction value in ETH")
            lines.append("# TYPE eth_tx_value_max_ether gauge")
            lines.append(f'eth_tx_value_max_ether{{mode="{mode}"}} {tx_config.get("TX_VALUE_MAX", 0)}')

            lines.append("# HELP eth_tx_value_increment_ether Transaction value increment in ETH")
            lines.append("# TYPE eth_tx_value_increment_ether gauge")
            lines.append(f'eth_tx_value_increment_ether{{mode="{mode}"}} {tx_config.get("TX_VALUE_INCREMENT", 0)}')

    return "\n".join(lines)


def add_system_metrics_prometheus(sys_summary):
    """
    Add system metrics to Prometheus format.
    """
    lines = []

    lines.append("# HELP system_cpu_percent CPU usage percentage")
    lines.append("# TYPE system_cpu_percent gauge")
    lines.append(f'system_cpu_percent{{metric="avg"}} {sys_summary.get("cpu_avg_percent", 0)}')
    lines.append(f'system_cpu_percent{{metric="max"}} {sys_summary.get("cpu_max_percent", 0)}')

    lines.append("# HELP system_memory_percent Memory usage percentage")
    lines.append("# TYPE system_memory_percent gauge")
    lines.append(f'system_memory_percent{{metric="avg"}} {sys_summary.get("memory_avg_percent", 0)}')
    lines.append(f'system_memory_percent{{metric="max"}} {sys_summary.get("memory_max_percent", 0)}')

    lines.append("# HELP system_memory_used_gb Memory used in GB")
    lines.append("# TYPE system_memory_used_gb gauge")
    lines.append(f'system_memory_used_gb {{metric="avg"}} {sys_summary.get("memory_avg_used_gb", 0)}')

    lines.append("# HELP system_network_bytes_total Network bytes transferred")
    lines.append("# TYPE system_network_bytes_total counter")
    lines.append(f'system_network_bytes_total{{direction="sent"}} {sys_summary.get("network_bytes_sent_total", 0)}')
    lines.append(f'system_network_bytes_total{{direction="recv"}} {sys_summary.get("network_bytes_recv_total", 0)}')

    return "\n".join(lines)


def add_block_metrics_prometheus(block_monitor):
    """
    Add block production time metrics to Prometheus format.

    Args:
        block_monitor: BlockMonitor instance (can be None)

    Returns:
        str: Prometheus-formatted block metrics
    """
    lines = []

    if block_monitor is None:
        return "\n".join(lines)

    stats = block_monitor.get_stats()
    current_interval = stats.get("current_block_interval_seconds")
    avg_interval = stats.get("average_block_interval_seconds")

    lines.append("# HELP eth_block_production_time_seconds Current block production time in seconds")
    lines.append("# TYPE eth_block_production_time_seconds gauge")
    if current_interval is not None:
        lines.append(f"eth_block_production_time_seconds {current_interval}")
    else:
        lines.append("eth_block_production_time_seconds 0")

    lines.append("# HELP eth_block_production_time_avg_seconds Average block production time in seconds")
    lines.append("# TYPE eth_block_production_time_avg_seconds gauge")
    if avg_interval is not None:
        lines.append(f"eth_block_production_time_avg_seconds {avg_interval}")
    else:
        lines.append("eth_block_production_time_avg_seconds 0")

    lines.append("# HELP eth_block_total_blocks_tracked Total blocks tracked by monitor")
    lines.append("# TYPE eth_block_total_blocks_tracked counter")
    lines.append(f'eth_block_total_blocks_tracked {stats.get("total_blocks_tracked", 0)}')

    # Finalized block metrics
    finalized_block_number = stats.get("finalized_block_number")
    finalized_block_timestamp = stats.get("finalized_block_timestamp")

    lines.append("# HELP eth_finalized_block_number Finalized block number")
    lines.append("# TYPE eth_finalized_block_number gauge")
    if finalized_block_number is not None:
        lines.append(f"eth_finalized_block_number {finalized_block_number}")
    else:
        lines.append("eth_finalized_block_number 0")

    lines.append("# HELP eth_finalized_block_timestamp Finalized block timestamp (UNIX)")
    lines.append("# TYPE eth_finalized_block_timestamp gauge")
    if finalized_block_timestamp is not None:
        lines.append(f"eth_finalized_block_timestamp {finalized_block_timestamp}")
    else:
        lines.append("eth_finalized_block_timestamp 0")

    return "\n".join(lines)


def add_network_metrics_prometheus(w3):
    """
    Add network information metrics to Prometheus format.

    Args:
        w3: Web3 instance (can be None)

    Returns:
        str: Prometheus-formatted network metrics
    """
    lines = []

    if w3 is None:
        return "\n".join(lines)

    try:
        chain_id = w3.eth.chain_id
        network_id = w3.net.version
        current_block = w3.eth.block_number
        sync_status = w3.eth.syncing

        lines.append("# HELP eth_chain_id Ethereum chain ID")
        lines.append("# TYPE eth_chain_id gauge")
        lines.append(f"eth_chain_id {chain_id}")

        lines.append("# HELP eth_network_id Ethereum network ID")
        lines.append("# TYPE eth_network_id gauge")
        lines.append(f"eth_network_id {network_id}")

        lines.append("# HELP eth_current_block_number Current block number")
        lines.append("# TYPE eth_current_block_number gauge")
        lines.append(f"eth_current_block_number {current_block}")

        lines.append("# HELP eth_node_syncing Node sync status (1=syncing, 0=synced)")
        lines.append("# TYPE eth_node_syncing gauge")
        syncing_value = 1 if sync_status else 0
        lines.append(f"eth_node_syncing {syncing_value}")
    except Exception:
        # If network info cannot be fetched, return empty lines
        pass

    return "\n".join(lines)
