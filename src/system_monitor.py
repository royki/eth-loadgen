# system_monitor.py
import time
import psutil
import threading
from typing import Dict


class SystemMonitor:
    """Monitor system metrics during load tests (CPU, memory, network)."""

    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.samples = []
        self.baseline_sample = None  # Baseline metrics before test starts
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start monitoring in background thread."""
        self.monitoring = True
        self.start_time = time.time()
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("System monitoring started")

    def capture_baseline(self):
        """Capture baseline metrics before test starts."""
        self.baseline_sample = self._collect_sample()
        if self.baseline_sample:
            print(
                f"System baseline captured: CPU={self.baseline_sample['cpu_percent']:.1f}%, Memory={self.baseline_sample['memory_percent']:.1f}%"
            )

    def stop(self):
        """Stop monitoring."""
        self.monitoring = False
        self.end_time = time.time()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        print("System monitoring stopped")

    def _monitor_loop(self):
        """Monitor loop running in background thread."""
        while self.monitoring:
            sample = self._collect_sample()
            if sample:
                self.samples.append(sample)
            time.sleep(0.5)  # Sample every 500ms

    def _collect_sample(self):
        """Collect a single system sample."""
        try:
            timestamp = time.time()
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            return {
                "timestamp": timestamp,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
                "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
                "network_bytes_sent": network_io.bytes_sent if network_io else 0,
                "network_bytes_recv": network_io.bytes_recv if network_io else 0,
            }
        except Exception as e:
            print(f"Error collecting system sample: {e}")
            return None

    def get_summary(self) -> Dict:
        """Get summary statistics of collected samples."""
        if not self.samples:
            baseline_info = {}
            if self.baseline_sample:
                baseline_info = {
                    "cpu_baseline_percent": round(self.baseline_sample["cpu_percent"], 2),
                    "memory_baseline_percent": round(self.baseline_sample["memory_percent"], 2),
                    "memory_baseline_used_gb": round(self.baseline_sample["memory_used_gb"], 4),
                }
            return {
                "cpu_avg_percent": 0,
                "cpu_max_percent": 0,
                "memory_avg_percent": 0,
                "memory_max_percent": 0,
                "total_memory_used_gb": 0,
                "network_bytes_sent_total": 0,
                "network_bytes_recv_total": 0,
                **baseline_info,
            }

        cpu_values = [s["cpu_percent"] for s in self.samples if s]
        memory_values = [s["memory_percent"] for s in self.samples if s]
        memory_used = [s["memory_used_gb"] for s in self.samples if s]

        if not self.samples:
            return {}

        # Get first and last network samples
        first_sample = self.samples[0] if self.samples else None
        last_sample = self.samples[-1] if self.samples else None

        network_sent_delta = 0
        network_recv_delta = 0

        if first_sample and last_sample:
            network_sent_delta = last_sample["network_bytes_sent"] - first_sample["network_bytes_sent"]
            network_recv_delta = last_sample["network_bytes_recv"] - first_sample["network_bytes_recv"]

        summary = {
            "cpu_avg_percent": round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0,
            "cpu_max_percent": round(max(cpu_values), 2) if cpu_values else 0,
            "cpu_min_percent": round(min(cpu_values), 2) if cpu_values else 0,
            "memory_avg_percent": round(sum(memory_values) / len(memory_values), 2) if memory_values else 0,
            "memory_max_percent": round(max(memory_values), 2) if memory_values else 0,
            "memory_avg_used_gb": round(sum(memory_used) / len(memory_used), 4) if memory_used else 0,
            "network_bytes_sent_total": network_sent_delta,
            "network_bytes_recv_total": network_recv_delta,
            "num_samples": len(self.samples),
        }

        # Add baseline metrics if available
        if self.baseline_sample:
            summary["cpu_baseline_percent"] = round(self.baseline_sample["cpu_percent"], 2)
            summary["memory_baseline_percent"] = round(self.baseline_sample["memory_percent"], 2)
            summary["memory_baseline_used_gb"] = round(self.baseline_sample["memory_used_gb"], 4)

        return summary
