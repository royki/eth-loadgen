# block_monitor.py
import time
import threading
from typing import Optional
from datetime import datetime
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

        # Finality tracking
        self.finalized_block_number: Optional[int] = None
        self.finalized_block_timestamp: Optional[float] = None
        self.pending_blocks = {}  # Track blocks pending finalization: {block_number: (detection_time, finalized_num)}

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

    @staticmethod
    def _fmt_time(ts: float) -> str:
        """Convert UNIX timestamp to human-readable UTC string."""
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _verify_persistence(self, block_number: int, block_hash: bytes, block_detection_time: float):
        """Immediately verify block persistence (no delay)."""
        try:
            # Re-read the block to verify persistence immediately
            re_block = self.w3.eth.get_block(block_number)
            verify_end_time = time.time()
            persistence_duration = verify_end_time - block_detection_time

            if re_block.hash == block_hash:
                print(
                    f"✅ Block {block_number} persists in canonical chain (hash matches) (took {persistence_duration:.2f}s)",
                    flush=True,
                )
                return True
            else:
                print(
                    f"❌ Block {block_number} replaced (reorg detected) (took {persistence_duration:.2f}s)", flush=True
                )
                return False
        except Exception as e:
            print(f"⚠️  Error verifying block {block_number} persistence: {e}", flush=True)
            return False

    def _check_finality(self, block_number: int, block_detection_time: float):
        """Check if block is finalized and report immediately."""
        try:
            finalized = self.w3.eth.get_block("finalized")
            finalized_num = finalized.number
            finalized_ts = float(finalized.timestamp)

            # Update the stored finalized block
            with self.lock:
                self.finalized_block_number = finalized_num
                self.finalized_block_timestamp = finalized_ts

            finality_check_time = time.time()
            finality_duration = finality_check_time - block_detection_time

            if finalized_num >= block_number:
                print(
                    f"✅ Block {block_number} has been finalized (finalized block: {finalized_num}) (took {finality_duration:.2f}s)",
                    flush=True,
                )
                # Remove from pending blocks
                with self.lock:
                    self.pending_blocks.pop(block_number, None)
                return True
            else:
                # Add to pending blocks for continuous monitoring
                with self.lock:
                    self.pending_blocks[block_number] = (block_detection_time, finalized_num)
                print(f"⏳ Block {block_number} pending finalization (finalized block: {finalized_num})", flush=True)
                return False
        except Exception as e:
            print(f"ℹ️  Block {block_number} - Finality not supported or unavailable on this chain: {e}", flush=True)
            return False

    def _monitor_loop(self):
        """Background loop monitoring for new blocks."""
        while self.monitoring:
            try:
                # Poll for latest block
                current_block = self.w3.eth.get_block("latest", full_transactions=False)
                current_block_number = current_block.number
                current_block_timestamp = float(current_block.timestamp)
                current_block_hash = current_block.hash

                # Update finalized block continuously and check pending blocks
                try:
                    finalized = self.w3.eth.get_block("finalized")
                    finalized_num = finalized.number
                    finalized_ts = float(finalized.timestamp)

                    with self.lock:
                        # Only update if we got a valid finalized block (not 0 or None)
                        if finalized_num is not None and finalized_num > 0:
                            prev_finalized = self.finalized_block_number
                            self.finalized_block_number = finalized_num
                            self.finalized_block_timestamp = finalized_ts

                            # Check if finalized block advanced and report pending blocks that are now finalized
                            if prev_finalized is not None and finalized_num > prev_finalized:
                                # Finalized block advanced - check pending blocks
                                finalized_blocks = []
                                for pending_block_num, (detection_time, _) in list(self.pending_blocks.items()):
                                    if finalized_num >= pending_block_num:
                                        # This block is now finalized
                                        finality_duration = time.time() - detection_time
                                        print(
                                            f"✅ Block {pending_block_num} has been finalized (finalized block: {finalized_num}) (took {finality_duration:.2f}s)",
                                            flush=True,
                                        )
                                        finalized_blocks.append(pending_block_num)

                                # Remove finalized blocks from pending
                                for block_num in finalized_blocks:
                                    self.pending_blocks.pop(block_num, None)
                except Exception:
                    # Finality not supported or error - don't update, keep existing value
                    pass

                # Check if we have a new block (need to check inside lock)
                new_block_detected = False
                block_num = None
                block_hash = None
                detection_time = None
                interval = None
                prev_timestamp = None

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

                        # Store values we need outside lock
                        block_num = current_block_number
                        block_hash = current_block_hash
                        block_detection_time = time.time()
                        detection_time = block_detection_time
                        # Store previous block timestamp before updating
                        prev_timestamp = self.last_block_timestamp
                        new_block_detected = True

                        # Update last block info
                        self.last_block_number = current_block_number
                        self.last_block_timestamp = current_block_timestamp
                    else:
                        # Update last block info if needed (first block or same block)
                        if self.last_block_number is None or current_block_number > self.last_block_number:
                            self.last_block_number = current_block_number
                            self.last_block_timestamp = current_block_timestamp

                # Print and verify outside lock (only if new block detected)
                if new_block_detected and block_num is not None:
                    print(f"\n🔷 New block detected: #{block_num}", flush=True)
                    print(f"   Production Time: {interval:.2f}s", flush=True)
                    print(f"   🕒  Previous Block Time: {self._fmt_time(prev_timestamp)}", flush=True)
                    print(f"   🕒  Current  Block Time: {self._fmt_time(current_block_timestamp)}", flush=True)

                    # Immediate persistence check (no delay) - outside lock
                    self._verify_persistence(block_num, block_hash, detection_time)

                    # Immediate finality check (no delay) - outside lock
                    self._check_finality(block_num, detection_time)

            except Exception as e:
                print(f"Error monitoring blocks: {e}", flush=True)
                import traceback

                traceback.print_exc()

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
                "finalized_block_number": self.finalized_block_number,
                "finalized_block_timestamp": self.finalized_block_timestamp,
            }
