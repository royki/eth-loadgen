# block_monitor.py
import time
import threading
from typing import Optional
from web3 import Web3


class BlockMonitor:
    """Monitor block production time continuously from network."""

    def __init__(self, w3: Web3, poll_interval: float = 1.0):
        """
        Initialize block monitor.

        Args:
            w3: Web3 instance
            poll_interval: Seconds between RPC polls (default: 1.0)
        """
        self.w3 = w3
        self.poll_interval = poll_interval
        self.monitoring = False
        self.monitor_thread = None

        # Block tracking data
        self.last_block_number: Optional[int] = None
        self.last_block_timestamp: Optional[float] = None
        self.current_block_interval: Optional[float] = None  # Latest block interval
        self.total_intervals = 0  # Count of intervals tracked
        self.sum_intervals = 0.0  # Sum for running average calculation
        self.avg_block_time: Optional[float] = None

        # Thread safety
        self.lock = threading.Lock()

    def start(self):
        """Start monitoring blocks in background thread."""
        if self.monitoring:
            return

        self.monitoring = True
        # Initialize with current block
        try:
            current_block = self.w3.eth.get_block("latest", full_transactions=False)
            with self.lock:
                self.last_block_number = current_block.number
                self.last_block_timestamp = float(current_block.timestamp)
        except Exception as e:
            print(f"Warning: Failed to get initial block: {e}")

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Block monitoring started")

    def stop(self):
        """Stop monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("Block monitoring stopped")

    def _monitor_loop(self):
        """Background loop monitoring for new blocks."""
        while self.monitoring:
            try:
                # Poll for latest block
                current_block = self.w3.eth.get_block("latest", full_transactions=False)
                current_block_number = current_block.number
                current_block_timestamp = float(current_block.timestamp)

                with self.lock:
                    # Check if we have a new block
                    if self.last_block_number is not None and current_block_number > self.last_block_number:
                        # Calculate interval (time between blocks)
                        interval = current_block_timestamp - self.last_block_timestamp

                        # Update metrics
                        self.current_block_interval = interval
                        self.total_intervals += 1
                        self.sum_intervals += interval
                        self.avg_block_time = self.sum_intervals / self.total_intervals

                        # Print new block detection log
                        print(
                            f"🔷 New block detected: #{current_block_number} | Interval: {interval:.2f}s | Avg: {self.avg_block_time:.2f}s",
                            flush=True,
                        )

                    # Update last block info
                    if self.last_block_number is None or current_block_number > self.last_block_number:
                        self.last_block_number = current_block_number
                        self.last_block_timestamp = current_block_timestamp

            except Exception as e:
                print(f"Error monitoring blocks: {e}")

            # Wait before next poll
            time.sleep(self.poll_interval)

    def get_current_interval(self) -> Optional[float]:
        """Get current/last block production time in seconds."""
        with self.lock:
            return self.current_block_interval

    def get_average_interval(self) -> Optional[float]:
        """Get average block production time in seconds."""
        with self.lock:
            return self.avg_block_time

    def get_stats(self) -> dict:
        """Get current block statistics."""
        with self.lock:
            return {
                "current_block_number": self.last_block_number,
                "current_block_interval_seconds": self.current_block_interval,
                "average_block_interval_seconds": self.avg_block_time,
                "total_blocks_tracked": self.total_intervals,
            }
