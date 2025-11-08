# metrics_server.py
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from src.prometheus_exporter import (
    format_prometheus_metrics,
    add_system_metrics_prometheus,
    add_block_metrics_prometheus,
    add_network_metrics_prometheus,
)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for /metrics endpoint."""

    def __init__(
        self,
        metrics_data,
        system_data,
        mode,
        w3,
        ephemeral_accounts,
        pref_account,
        block_monitor=None,
        *args,
        **kwargs,
    ):
        self.metrics_data = metrics_data
        self.system_data = system_data
        self.mode = mode
        self.w3 = w3
        self.ephemeral_accounts = ephemeral_accounts
        self.pref_account = pref_account
        self.block_monitor = block_monitor
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/metrics":
            # Re-read account balances from chain for fresh data
            fresh_report = self.metrics_data.copy()
            if self.ephemeral_accounts and self.w3:
                balances = {
                    "prefunded": {
                        "address": self.pref_account.address,
                        "balance_eth": float(
                            self.w3.from_wei(
                                self.w3.eth.get_balance(self.pref_account.address),
                                "ether",
                            )
                        ),
                    },
                    "ephemeral": [],
                }

                for acct, _ in self.ephemeral_accounts:
                    balance = self.w3.eth.get_balance(acct.address)
                    balances["ephemeral"].append(
                        {
                            "address": acct.address,
                            "balance_eth": float(self.w3.from_wei(balance, "ether")),
                        }
                    )

                fresh_report["account_balances"] = balances

            # Format metrics with fresh balances
            prom_output = format_prometheus_metrics(fresh_report, mode=self.mode)

            # Add system metrics if available
            if self.system_data:
                sys_metrics = add_system_metrics_prometheus(self.system_data)
                prom_output += "\n\n" + sys_metrics

            # Add block metrics if available
            block_metrics = add_block_metrics_prometheus(self.block_monitor)
            if block_metrics:
                prom_output += "\n\n" + block_metrics

            # Add network metrics if available
            network_metrics = add_network_metrics_prometheus(self.w3)
            if network_metrics:
                prom_output += "\n\n" + network_metrics

            # Send response
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(prom_output.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class MetricsServer:
    """HTTP server that exposes Prometheus metrics."""

    def __init__(self, host="localhost", port=9000):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.metrics_data = {}
        self.system_data = None
        self.mode = "default"
        self.w3 = None
        self.ephemeral_accounts = []
        self.pref_account = None
        self.block_monitor = None

    def start(self, w3, ephemeral_accounts, pref_account, block_monitor=None):
        """Start metrics server in background."""
        self.w3 = w3
        self.ephemeral_accounts = ephemeral_accounts
        self.pref_account = pref_account
        self.block_monitor = block_monitor

        def run_server():
            # Create handler with bound metrics and chain access
            def make_handler(*args, **kwargs):
                return MetricsHandler(
                    self.metrics_data,
                    self.system_data,
                    self.mode,
                    self.w3,
                    self.ephemeral_accounts,
                    self.pref_account,
                    self.block_monitor,
                    *args,
                    **kwargs,
                )

            self.server = HTTPServer((self.host, self.port), make_handler)
            self.server.serve_forever()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        print(f"Metrics server started at http://{self.host}:{self.port}/metrics")

    def stop(self):
        """Stop metrics server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Metrics server stopped")

    def update_metrics(self, metrics_data, system_data=None, mode="default"):
        """Update metrics data."""
        self.metrics_data = metrics_data
        self.system_data = system_data
        self.mode = mode

    def get_url(self):
        """Get the metrics URL."""
        return f"http://{self.host}:{self.port}/metrics"
