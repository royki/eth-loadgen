import time
import threading
from collections import defaultdict


class Metrics:
    def __init__(self):
        self.sent = 0
        self.success = 0
        self.fail = 0
        self.total_latency = 0
        self.total_gas_used = 0
        self.total_eth_sent = 0  # Total ETH sent in transactions
        self.tx_value_config = None  # Store TX value configuration
        self.account_balances = {}  # Store account addresses and balances
        self.log = []
        self.start_time = None
        self.end_time = None
        self.requested_tps = None  # Store requested TPS target

        # Time-series tracking: bucket by time window
        self.time_buckets = defaultdict(
            lambda: {
                "sent": 0,
                "success": 0,
                "fail": 0,
                "total_latency": 0,
                "total_gas_used": 0,
                "total_eth_sent": 0,
                "latencies": [],
            }
        )

        self.reporting_active = False
        self.report_thread = None
        self.window_period = 5
        self.report_start_time = None

    def record(
        self,
        latency,
        success=True,
        sender=None,
        recipient=None,
        tx_hash=None,
        gas_used=None,
        eth_value=None,
    ):
        self.sent += 1
        if success:
            self.success += 1
        else:
            self.fail += 1
        self.total_latency += latency
        if gas_used:
            self.total_gas_used += gas_used
        if eth_value:
            self.total_eth_sent += eth_value
        self.log.append(
            {
                "sender": sender,
                "recipient": recipient,
                "tx_hash": tx_hash,
                "success": success,
                "latency_sec": latency,
                "gas_used": gas_used or 0,
                "eth_value": eth_value or 0,
                "timestamp": time.time(),
            }
        )

        # Add to time-series bucket (bucket by second)
        if self.start_time is not None:
            bucket_key = int(time.time() - self.start_time)
            bucket = self.time_buckets[bucket_key]
            bucket["sent"] += 1
            if success:
                bucket["success"] += 1
            else:
                bucket["fail"] += 1
            bucket["total_latency"] += latency
            bucket["latencies"].append(latency)
            if gas_used:
                bucket["total_gas_used"] += gas_used
            if eth_value:
                bucket["total_eth_sent"] += eth_value

    def start_test(self, requested_tps=None):
        """Mark the start of a test run."""
        self.start_time = time.time()
        self.requested_tps = requested_tps  # Store requested TPS target

    def end_test(self):
        """Mark the end of a test run."""
        self.end_time = time.time()

    def start(self, window_period=5):
        """
        Start periodic time-series metrics reporting (like BlockMonitor.start()).
        Independent of test lifecycle - runs continuously in background.

        Args:
            window_period: Seconds between reports (default: 5)
        """
        if self.reporting_active:
            print("Warning: Metrics reporting already active")
            return

        self.report_start_time = time.time()
        self.reporting_active = True
        self.window_period = window_period
        print(
            f"DEBUG: About to start thread, reporting_active={self.reporting_active}, window_period={window_period}",
            flush=True,
        )
        self.report_thread = threading.Thread(target=self._report_loop, daemon=True)
        self.report_thread.start()
        print(f"DEBUG: Thread started, thread.is_alive()={self.report_thread.is_alive()}", flush=True)
        print(
            f"Time-series metrics reporting started (window_period={window_period}s) - independent and continuous",
            flush=True,
        )

    def stop(self):
        """Stop periodic reporting (only called on server shutdown)."""
        if not self.reporting_active:
            print("DEBUG: stop() called but reporting_active is already False", flush=True)
            return

        # print(f"DEBUG: stop() called", flush=True)
        self.reporting_active = False
        if self.report_thread:
            self.report_thread.join(timeout=2)
        self.report_start_time = None
        print("Time-series metrics reporting stopped", flush=True)

    def _report_loop(self):
        """
        Background loop for periodic reporting (like BlockMonitor._monitor_loop()).
        Independent of test lifecycle - runs continuously.
        Uses rolling window based on current time, not test start_time.
        """
        if self.report_start_time is None:
            print("Error in _report_loop: report_start_time is None", flush=True)
            return

        next_report_time = self.report_start_time + self.window_period
        print(
            f"DEBUG: _report_loop started, report_start_time={self.report_start_time}, next_report_time={next_report_time}, reporting_active={self.reporting_active}",
            flush=True,
        )

        loop_count = 0
        while self.reporting_active:
            loop_count += 1
            if loop_count == 1:
                print(f"DEBUG: Entered while loop, reporting_active={self.reporting_active}", flush=True)
            current_time = time.time()

            # Runs continuously regardless of test state
            if current_time >= next_report_time:
                print(
                    f"DEBUG: Reached report time: current={current_time}, next={next_report_time}, reporting_uptime={current_time - self.report_start_time:.1f}s",
                    flush=True,
                )
                try:
                    # Use rolling window from current time (last N seconds), not test start_time
                    window_metrics = self.get_time_window_metrics(window_seconds=self.window_period)

                    # Always print metrics (even if zeros) to show periodic updates
                    if window_metrics is None:
                        window_metrics = {
                            "tps": 0,
                            "rps": 0,
                            "mgas_per_sec": 0,
                            "avg_latency_sec": 0,
                            "p50_latency_sec": 0,
                            "p95_latency_sec": 0,
                            "success_rate_%": 0,
                            "fail_rate_%": 0,
                        }

                    # Show reporting uptime (how long reporting has been active), not test elapsed time
                    reporting_uptime = int(current_time - self.report_start_time)
                    print(
                        f"\n📈 [{reporting_uptime}s] Time-Series Metrics (last {self.window_period}s):",
                        flush=True,
                    )
                    print(
                        f"   TPS: {window_metrics['tps']} | RPS: {window_metrics['rps']} | MGas/s: {window_metrics['mgas_per_sec']}",
                        flush=True,
                    )
                    print(
                        f"   Latency: avg={window_metrics['avg_latency_sec']:.4f}s, p50={window_metrics['p50_latency_sec']:.4f}s, p95={window_metrics['p95_latency_sec']:.4f}s",
                        flush=True,
                    )
                    print(
                        f"   Success: {window_metrics['success_rate_%']}% | Fail: {window_metrics['fail_rate_%']}%",
                        flush=True,
                    )

                    next_report_time += self.window_period
                    # print(f"DEBUG: Advanced next_report_time to {next_report_time} (next report in {next_report_time - current_time:.2f}s)", flush=True)
                except Exception as e:
                    print(f"Error in metrics reporter: {e}", flush=True)
                    import traceback

                    traceback.print_exc()
                    # Still advance next_report_time to avoid getting stuck
                    next_report_time += self.window_period
                    # print(f"DEBUG: Advanced next_report_time to {next_report_time} (after exception)", flush=True)

            # Sleep until next check (0.5s granularity)
            time.sleep(0.5)

            # Debug: Check if reporting_active changed (but don't print every iteration)
            if not self.reporting_active:
                if loop_count % 10 == 0:  # Only print every 10th iteration to avoid spam
                    print(f"DEBUG: reporting_active became False (loop_count={loop_count})", flush=True)
                break  # Exit immediately if reporting_active is False

        print(
            f"DEBUG: _report_loop exiting, reporting_active={self.reporting_active}, loop_count={loop_count}",
            flush=True,
        )

    def set_tx_value_config(self, config):
        """Store TX value configuration for reporting."""
        self.tx_value_config = config

    def set_account_balances(self, balances):
        """Store account balances for reporting."""
        self.account_balances = balances

    def reset(self):
        """Reset all metrics for a new test run."""
        # NOTE: Don't stop periodic reporting - it runs independently
        # Reporting continues regardless of test resets

        # Preserve account_balances - don't reset them
        preserved_balances = self.account_balances.copy()

        self.sent = 0
        self.success = 0
        self.fail = 0
        self.total_latency = 0
        self.total_gas_used = 0
        self.total_eth_sent = 0
        self.tx_value_config = None
        self.account_balances = preserved_balances  # Restore balances
        self.log = []
        self.start_time = None
        self.end_time = None
        self.requested_tps = None
        # Reset time-series buckets
        self.time_buckets = defaultdict(
            lambda: {
                "sent": 0,
                "success": 0,
                "fail": 0,
                "total_latency": 0,
                "total_gas_used": 0,
                "total_eth_sent": 0,
                "latencies": [],
            }
        )

    def _calculate_percentile(self, latencies, percentile):
        """Calculate percentile from latencies list."""
        if not latencies:
            return 0
        sorted_latencies = sorted(latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    def report(self):
        """Generate comprehensive metrics report."""
        avg_latency = self.total_latency / self.sent if self.sent else 0
        latency_list = [entry["latency_sec"] for entry in self.log if entry.get("latency_sec")]
        p50_latency = self._calculate_percentile(latency_list, 50)
        p95_latency = self._calculate_percentile(latency_list, 95)

        # Calculate test duration
        duration_sec = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0

        # Calculate RPS (Requests Per Second)
        rps = self.sent / duration_sec if duration_sec > 0 else 0

        # Calculate actual TPS (Transactions Per Second) - same as RPS
        actual_tps = self.sent / duration_sec if duration_sec > 0 else 0

        # Calculate TPS variance (difference between requested and actual)
        tps_variance = None
        tps_accuracy_percent = None
        if self.requested_tps is not None and self.requested_tps > 0:
            tps_variance = actual_tps - self.requested_tps
            tps_accuracy_percent = (actual_tps / self.requested_tps * 100) if self.requested_tps > 0 else 0

        # Calculate MGas/s (Million Gas per second)
        # total_gas_used is in gas units, convert to mega-gas by dividing by 1e6
        total_mgas = self.total_gas_used / 1e6  # Convert gas units to million gas
        mgas_per_sec = total_mgas / duration_sec if duration_sec > 0 else 0

        # Calculate success rate
        success_rate = (self.success / self.sent * 100) if self.sent > 0 else 0
        fail_rate = (self.fail / self.sent * 100) if self.sent > 0 else 0

        result = {
            "total_sent": self.sent,
            "success": self.success,
            "fail": self.fail,
            "success_rate_%": round(success_rate, 2),
            "fail_rate_%": round(fail_rate, 2),
            "avg_latency_sec": round(avg_latency, 6),
            "p50_latency_sec": round(p50_latency, 6),
            "p95_latency_sec": round(p95_latency, 6),
            "rps": round(rps, 2),
            "requested_tps": self.requested_tps,
            "actual_tps": round(actual_tps, 2),
            "tps_variance": round(tps_variance, 2) if tps_variance is not None else None,
            "tps_accuracy_%": round(tps_accuracy_percent, 2) if tps_accuracy_percent is not None else None,
            "duration_sec": round(duration_sec, 2),
            "total_gas_used": self.total_gas_used,
            "mgas_per_sec": round(mgas_per_sec, 4) if mgas_per_sec > 0 else 0,
            "total_eth_sent": round(self.total_eth_sent, 6),
        }

        # Add TX value configuration if available
        if self.tx_value_config:
            result["tx_value_config"] = self.tx_value_config

        # Add account balances if available
        if self.account_balances:
            result["account_balances"] = self.account_balances

        return result

    def get_time_window_metrics(self, window_seconds=5):
        """
        Get metrics for the last N seconds (rolling window).
        Independent of test start_time - uses current time for rolling window.

        Args:
            window_seconds: Number of seconds to look back

        Returns:
            dict with time-series metrics for the window
        """
        if not self.log:
            # No transactions recorded yet - return zeros
            return {
                "tps": 0,
                "rps": 0,
                "mgas_per_sec": 0,
                "avg_latency_sec": 0,
                "p50_latency_sec": 0,
                "p95_latency_sec": 0,
                "success_rate_%": 0,
                "fail_rate_%": 0,
            }

        # Use rolling window from current time (last N seconds)
        # Get all transactions from log within the window
        current_time = time.time()
        window_start_time = current_time - window_seconds

        window_log = [entry for entry in self.log if entry.get("timestamp", 0) >= window_start_time]

        if not window_log:
            # No transactions in window - return zeros
            return {
                "tps": 0,
                "rps": 0,
                "mgas_per_sec": 0,
                "avg_latency_sec": 0,
                "p50_latency_sec": 0,
                "p95_latency_sec": 0,
                "success_rate_%": 0,
                "fail_rate_%": 0,
            }

        # Calculate metrics from window_log
        window_sent = len(window_log)
        window_success = sum(1 for entry in window_log if entry.get("success", False))
        window_fail = window_sent - window_success
        window_total_latency = sum(entry.get("latency_sec", 0) for entry in window_log)
        window_total_gas = sum(entry.get("gas_used", 0) for entry in window_log)
        # window_total_eth = sum(entry.get("eth_value", 0) for entry in window_log)
        window_latencies = [entry.get("latency_sec", 0) for entry in window_log if entry.get("latency_sec")]

        use_bucket_method = False
        if self.start_time is not None:
            try:
                current_bucket = int(current_time - self.start_time)
                start_bucket = max(0, current_bucket - window_seconds + 1)
                use_bucket_method = True
            except Exception as e:
                print(f"Error in get_time_window_metrics: {e}", flush=True)
                import traceback

                traceback.print_exc()
                pass
                return {
                    "tps": 0,
                    "rps": 0,
                    "mgas_per_sec": 0,
                    "avg_latency_sec": 0,
                    "p50_latency_sec": 0,
                    "p95_latency_sec": 0,
                    "success_rate_%": 0,
                    "fail_rate_%": 0,
                }
        if use_bucket_method:
            bucket_window_sent = 0
            bucket_window_success = 0
            bucket_window_fail = 0
            bucket_window_total_latency = 0
            bucket_window_total_gas = 0
            # bucket_window_total_eth = 0
            bucket_window_latencies = []

            for bucket_key in range(start_bucket, current_bucket + 1):
                if bucket_key in self.time_buckets:
                    bucket = self.time_buckets[bucket_key]
                    bucket_window_sent += bucket["sent"]
                    bucket_window_success += bucket["success"]
                    bucket_window_fail += bucket["fail"]
                    bucket_window_total_latency += bucket["total_latency"]
                    bucket_window_total_gas += bucket["total_gas_used"]
                    # bucket_window_total_eth += bucket["total_eth_sent"]
                    bucket_window_latencies.extend(bucket["latencies"])

            # Use bucket data if it has more transactions (more accurate for recent data)
            if bucket_window_sent > window_sent:
                window_sent = bucket_window_sent
                window_success = bucket_window_success
                window_fail = bucket_window_fail
                window_total_latency = bucket_window_total_latency
                window_total_gas = bucket_window_total_gas
                # window_total_eth = bucket_window_total_eth
                window_latencies = bucket_window_latencies

        # Calculate final metrics
        if window_sent == 0:
            return {
                "tps": 0,
                "rps": 0,
                "mgas_per_sec": 0,
                "avg_latency_sec": 0,
                "p50_latency_sec": 0,
                "p95_latency_sec": 0,
                "success_rate_%": 0,
                "fail_rate_%": 0,
            }

        # Calculate metrics for window
        window_tps = window_sent / window_seconds
        window_rps = window_sent / window_seconds
        window_mgas = (window_total_gas / 1e6) / window_seconds

        avg_latency = window_total_latency / window_sent if window_sent > 0 else 0
        p50_latency = self._calculate_percentile(window_latencies, 50) if window_latencies else 0
        p95_latency = self._calculate_percentile(window_latencies, 95) if window_latencies else 0

        success_rate = (window_success / window_sent * 100) if window_sent > 0 else 0
        fail_rate = (window_fail / window_sent * 100) if window_sent > 0 else 0

        return {
            "tps": round(window_tps, 2),
            "rps": round(window_rps, 2),
            "mgas_per_sec": round(window_mgas, 4),
            "avg_latency_sec": round(avg_latency, 6),
            "p50_latency_sec": round(p50_latency, 6),
            "p95_latency_sec": round(p95_latency, 6),
            "success_rate_%": round(success_rate, 2),
            "fail_rate_%": round(fail_rate, 2),
        }
