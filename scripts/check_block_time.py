#!/usr/bin/env python3
"""
Ethereum Block Production & Persistence & Finality Monitor
- Tracks block persistence (canonical)
- Tracks block finality
"""

import sys
import time
from datetime import datetime
from web3 import Web3

def fmt_time(ts):
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

def check_block_time(rpc_url, target_interval=12, max_blocks=None, continuous=False):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"❌ Cannot connect to RPC at {rpc_url}")
        sys.exit(1)

    # --- Network info ---
    chain_id = w3.eth.chain_id
    current_block = w3.eth.block_number
    sync_status = w3.eth.syncing

    print(f"✅ Connected to RPC at {rpc_url}")
    print(f"🌐 Chain ID: {chain_id}")
    print(f"📏 Current block height: {current_block}")

    if sync_status:
        print(f"🟠 Node syncing: {sync_status}")
    else:
        print(f"🟢 Node is fully synced")

    # --- Start monitoring ---
    latest = w3.eth.get_block("latest")
    prev_number = latest.number
    prev_ts = latest.timestamp
    print(f"⏱️ Starting monitoring from block {prev_number} @ {fmt_time(prev_ts)}")

    checked_blocks = 0
    block_timestamps = {}  # blk_num -> first seen timestamp

    try:
        while True:
            latest = w3.eth.get_block("latest")
            if latest.number > prev_number:
                for blk_num in range(prev_number + 1, latest.number + 1):
                    curr_blk = w3.eth.get_block(blk_num)
                    interval = curr_blk.timestamp - prev_ts

                    print("\n" + "="*100)
                    print(f"📦 BLOCK {prev_number} → {blk_num}")
                    print("="*100)
                    print(f"⏱️ Production Time: {interval:.2f}s (target: ~{target_interval:.1f}s)")
                    if abs(interval - target_interval) > target_interval * 0.5:
                        print("⚠️ Block interval deviates from expected target.")
                    else:
                        print("✅ Block interval within expected range.")
                    print(f"🕒 Previous Block Time: {fmt_time(prev_ts)}")
                    print(f"🕒 Current Block Time:  {fmt_time(curr_blk.timestamp)}")

                    block_timestamps[blk_num] = time.time()

                    # --- Block persistence check
                    re_blk = w3.eth.get_block(blk_num)
                    if re_blk.hash == curr_blk.hash:
                        print(f"✅ Block {blk_num} persists in canonical chain (hash matches).")
                    else:
                        print(f"❌ Block {blk_num} replaced (reorg detected).")

                    # --- Block finality check
                    try:
                        finalized = w3.eth.get_block("finalized")
                        finalized_num = finalized.number
                        for f_blk_num in list(block_timestamps.keys()):
                            if finalized_num >= f_blk_num:
                                duration = time.time() - block_timestamps[f_blk_num]
                                print(f"✅ Block {f_blk_num} finalized (finalized block: {finalized_num}, duration: {duration:.2f}s)")
                                del block_timestamps[f_blk_num]
                            else:
                                lag = f_blk_num - finalized_num
                                print(f"⏳ Block {f_blk_num} pending finalization (finalized block: {finalized_num}, lag: {lag} blocks)")
                    except Exception:
                        print("ℹ️ Finality not supported or unavailable on this chain.")

                    print("-"*100)
                    prev_number = blk_num
                    prev_ts = curr_blk.timestamp
                    checked_blocks += 1

                    if not continuous:
                        if max_blocks and checked_blocks >= max_blocks:
                            print(f"✅ Completed monitoring {max_blocks} blocks. Exiting.")
                            return
                        elif not max_blocks:
                            return

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Graceful shutdown requested. Exiting monitor.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ethereum Block Production & Finality Monitor")
    parser.add_argument("-r", "--rpc-url", default="http://localhost:8545", help="RPC URL")
    parser.add_argument("-t", "--target", type=float, default=6, help="Expected block time in seconds")
    parser.add_argument("-c", "--continuous", action="store_true", help="Keep monitoring continuously")
    parser.add_argument("-n", "--num-blocks", type=int, help="Number of blocks to monitor before exit (ignored in continuous mode)")
    args = parser.parse_args()

    check_block_time(
        args.rpc_url,
        target_interval=args.target,
        max_blocks=args.num_blocks,
        continuous=args.continuous
    )
