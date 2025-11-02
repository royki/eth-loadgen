# load_generator.py
import time
import random
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3
from src.metrics import Metrics
from src.system_monitor import SystemMonitor

# from src.config import METRICS_WINDOW_PERIOD


class IncrementalValueGenerator:
    """Generate incremental transaction values based on mode."""

    def __init__(self, min_value, max_value, increment, mode="ascending"):
        self.min_value = min_value
        self.max_value = max_value
        self.increment = increment
        self.mode = mode
        self.current_index = 0
        self._generate_value_list()

    def _generate_value_list(self):
        """Generate all possible values in range."""
        self.value_list = []
        val = self.min_value
        while val <= self.max_value:
            self.value_list.append(val)
            val += self.increment

        # Warn if only one value generated
        if len(self.value_list) == 1:
            print(f"WARNING: Only 1 value generated ({self.value_list[0]} ETH)")
            print(
                f"  Adjust increment. Suggested increment for range [{self.min_value} to {self.max_value}]: {(self.max_value - self.min_value) / 10}"
            )
        else:
            print(f"Generated {len(self.value_list)} values from {self.min_value} to {self.max_value}")

    def next(self):
        """Get next value based on mode."""
        if self.mode == "ascending":
            value = self.value_list[self.current_index % len(self.value_list)]
            self.current_index += 1
            return value
        elif self.mode == "descending":
            index = len(self.value_list) - 1 - (self.current_index % len(self.value_list))
            value = self.value_list[index]
            self.current_index += 1
            return value
        else:  # random
            return random.choice(self.value_list)

    def reset(self):
        """Reset the generator."""
        self.current_index = 0


def send_transaction(
    w3,
    sender_addr,
    sender_key,
    recipient_addr,
    tx_value,
    gas,
    nonce,
    gas_price,
    metrics,
    nonces,
    nonce_locks,
    eth_value,
):
    """
    Send a single transaction - thread-safe version for concurrent execution.
    Updates shared nonces dict with lock protection.
    Returns tx_hash (success) or None (failure)
    """
    nonce_locks[sender_addr].acquire()
    try:
        # Check balance before sending
        balance = w3.eth.get_balance(sender_addr)
        tx_value_wei = w3.to_wei(tx_value, "ether")  # Convert ETH to wei
        required_wei = tx_value_wei + (gas * gas_price)
        if balance < required_wei:
            print("\n❌ ACCOUNT OUT OF BALANCE")
            print(f"   Account: {sender_addr}")
            print(f"   Current balance: {w3.from_wei(balance, 'ether')} ETH")
            print(
                f"   Required: {w3.from_wei(required_wei, 'ether')} ETH (tx: {tx_value} ETH + gas: {(gas * gas_price)/1e18} ETH)"
            )
            print(f"   Missing: {w3.from_wei(required_wei - balance, 'ether')} ETH")
            print("   Transaction skipped - load test continues with other accounts\n")
            metrics.record(
                0,
                success=False,
                sender=sender_addr,
                recipient=recipient_addr,
                tx_hash=None,
            )
            return None

        current_nonce = nonces.get(sender_addr, w3.eth.get_transaction_count(sender_addr))
        nonce = current_nonce  # Use the latest nonce

        tx = _build_tx(w3, sender_addr, recipient_addr, tx_value, gas, nonce, gas_price)
        t0 = time.time()

        try:
            signed = w3.eth.account.sign_transaction(tx, sender_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            elapsed = time.time() - t0
            print(
                f"TX from {sender_addr[:10]}... -> {recipient_addr[:10]}..., value={tx_value} ETH, tx: {tx_hash.hex()}"
            )
            metrics.record(
                elapsed,
                success=True,
                sender=sender_addr,
                recipient=recipient_addr,
                tx_hash=tx_hash.hex(),
                gas_used=gas,
                eth_value=eth_value,
            )
            nonces[sender_addr] = nonce + 1
            return tx_hash
        except Exception as e:
            elapsed = time.time() - t0
            error_str = str(e).lower()

            if "nonce too low" in error_str or "nonce too high" in error_str:
                print(f"Nonce mismatch for {sender_addr}, refreshing...")
                nonces[sender_addr] = w3.eth.get_transaction_count(sender_addr)
            elif "replacement underpriced" in error_str or "already known" in error_str:
                print(f"TX already in mempool for {sender_addr}, incrementing nonce")
                nonces[sender_addr] = nonce + 1
            elif "insufficient funds" in error_str:
                print(f"Insufficient funds for {sender_addr}")
            else:
                pass

            print(f"Failed TX from {sender_addr[:10]}... -> {recipient_addr[:10]}...: {e}")
            metrics.record(
                elapsed,
                success=False,
                sender=sender_addr,
                recipient=recipient_addr,
                tx_hash=None,
            )
            return None
    finally:
        nonce_locks[sender_addr].release()


def _build_tx(
    w3,
    sender_address,
    recipient_address,
    value_eth,
    gas,
    nonce,
    gas_price,
    use_eip1559=False,
):
    """
    Build a transaction dict. Using legacy gasPrice for simplicity.
    gas_price: cached gas price to avoid per-transaction RPC calls
    """
    tx = {
        "from": sender_address,
        "to": recipient_address,
        "value": w3.to_wei(value_eth, "ether"),
        "gas": gas,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gasPrice": gas_price,
    }
    return tx


def apply_tps_load(
    w3: Web3,
    prefunded_account,
    prefunded_key_hex,
    ephemeral_accounts,
    tps: int,
    duration_sec: int,
    gas: int,
    tx_value,
    mode: str,
    metrics: Metrics,
    system_monitor: SystemMonitor = None,
):
    """
    Apply total tps transactions per second for duration_sec seconds.
    mode: "default" (all tx from prefunded), "random", "round-robin"
    metrics: Metrics object to record per-tx stats
    ephemeral_accounts: list of (account_obj, private_key) tuples
    """
    # Prepare sender pools:
    # prefunded is a LocalAccount-like dict (prefunded_account)
    # ephemeral_accounts: list of (account_obj, private_key_hex) tuples
    start = time.time()
    end = start + duration_sec
    total_sent = 0

    # Nonce tracking per account (prefunded + ephemeral)
    nonces = {}
    nonces[prefunded_account.address] = w3.eth.get_transaction_count(prefunded_account.address)
    for acct, _ in ephemeral_accounts:
        nonces[acct.address] = w3.eth.get_transaction_count(acct.address)

    rr_index = 0
    num_ephemeral = len(ephemeral_accounts)
    if num_ephemeral == 0 and mode in ("random", "round-robin"):
        print("No ephemeral accounts available for random/round-robin mode.")
        return

    # Start metrics tracking with requested TPS (for test-specific metrics)
    metrics.start_test(requested_tps=tps)

    # Start system monitoring
    if system_monitor:
        system_monitor.start()

    # Setup value generator for incremental values
    if isinstance(tx_value, tuple):
        # Incremental mode: tx_value is (min, max, increment, mode)
        value_min, value_max, value_inc, value_mode = tx_value
        value_generator = IncrementalValueGenerator(value_min, value_max, value_inc, value_mode)
        print(f"Using incremental values: {value_min} to {value_max} ETH, mode={value_mode}")
    else:
        # Fixed value mode
        value_generator = None
        print(f"Using fixed value: {tx_value} ETH")

    # Cache gas price once at the start to avoid per-transaction RPC calls
    try:
        cached_gas_price = w3.eth.gas_price
        print(
            f"Starting load: mode={mode}, tps={tps}, duration={duration_sec}s, gas={gas}, gas_price={cached_gas_price}"
        )
    except Exception as e:
        print(f"Failed to get gas price: {e}")
        metrics.end_test()
        return

    # Create nonce locks for thread safety
    all_addrs = [prefunded_account.address]
    for acct, _ in ephemeral_accounts:
        all_addrs.append(acct.address)
    nonce_locks = {addr: Lock() for addr in all_addrs}

    # Create thread pool for concurrent transactions
    max_workers = min(tps, len(ephemeral_accounts) + 1, 20)  # Cap at 20 workers
    executor = ThreadPoolExecutor(max_workers=max_workers)

    # Timer-based TPS enforcement with concurrency
    next_second_start = start

    while time.time() < end:
        current_second_start = next_second_start
        next_second_start = current_second_start + 1.0
        futures = []

        # Prepare tps transactions to send concurrently in this second
        for i in range(tps):
            if time.time() >= end:
                break

            # choose sender and recipient
            if mode == "default":
                sender_addr = prefunded_account.address
                sender_key = prefunded_key_hex
            elif mode == "random":
                sender, sender_key = random.choice(ephemeral_accounts)
                sender_addr = sender.address
            else:  # round-robin
                sender, sender_key = ephemeral_accounts[rr_index % num_ephemeral]
                rr_index += 1
                sender_addr = sender.address

            # choose recipient: avoid same address
            if num_ephemeral > 0:
                r_idx = random.randint(0, num_ephemeral - 1)
                r, _ = ephemeral_accounts[r_idx]
                recipient_addr = r.address
                if recipient_addr == sender_addr:
                    # pick next one in the list
                    next_idx = (r_idx + 1) % num_ephemeral
                    recipient, _ = ephemeral_accounts[next_idx]
                    recipient_addr = recipient.address
            else:
                # if no ephemeral, just send to prefunded self (not useful)
                recipient_addr = prefunded_account.address

            # Get tx value (incremental or fixed)
            if value_generator is not None:
                current_tx_value = value_generator.next()
            else:
                current_tx_value = tx_value

            # Submit transaction to thread pool for concurrent execution
            future = executor.submit(
                send_transaction,
                w3,
                sender_addr,
                sender_key,
                recipient_addr,
                current_tx_value,
                gas,
                0,
                cached_gas_price,
                metrics,
                nonces,
                nonce_locks,
                current_tx_value,
            )
            futures.append(future)

        # Wait for all transactions in this second to complete
        tx_count = 0
        for future in futures:
            try:
                result = future.result(timeout=1.0)
                if result is not None:
                    tx_count += 1
                    total_sent += 1
            except Exception as e:
                print(f"Future execution error: {e}")

        # If we haven't met the TPS target this second, it means transactions are too slow
        if tx_count < len(futures):
            print(f"Warning: Only completed {tx_count}/{len(futures)} transactions in this second")

        # Ensure we don't move to next second too early (respect timer)
        wait_until = min(next_second_start, end)
        if time.time() < wait_until:
            time.sleep(wait_until - time.time())

    executor.shutdown(wait=True)
    metrics.end_test()

    # Stop system monitoring
    if system_monitor:
        system_monitor.stop()

    print(f"Load complete. Total sent: {total_sent}", flush=True)
