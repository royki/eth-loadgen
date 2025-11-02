# accounts.py
import json
from pathlib import Path
from eth_account import Account
from web3 import Web3
from src.config import UTC_FILE_PATH, UTC_PASSWORD, PRIVATE_KEY, RPC_URL


def load_prefunded_account_via_rpc():
    """
    Get prefunded account via RPC call - validates that the UTC account exists on chain.
    Returns (Account object, private_key_hex) or None if not available.
    """
    try:
        print(f"Attempting to connect to RPC: {RPC_URL}")
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            print("ERROR: RPC is not connected")
            return None

        print("RPC connected successfully")
        return None  # Don't try to get key from RPC - use UTC file instead
    except Exception as e:
        print(f"RPC method failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return None


def load_prefunded_account():
    """
    Load prefunded account from UTC keystore file or private key.
    Returns (Account object, private_key_hex)
    Priority: 1. UTC file, 2. Private key from env var
    """
    # Try UTC file first
    if UTC_FILE_PATH and Path(UTC_FILE_PATH).exists():
        try:
            print(f"Loading account from UTC keystore file: {UTC_FILE_PATH}")
            with open(UTC_FILE_PATH, "r") as f:
                keystore = json.load(f)

            # Try decrypting with password, or empty string if None
            try:
                private_key_bytes = Account.decrypt(keystore, UTC_PASSWORD or "")
            except ValueError:
                print("Decryption failed with password. Trying empty string...")
                private_key_bytes = Account.decrypt(keystore, "")

            private_key_hex = private_key_bytes.hex()
            account = Account.from_key(private_key_hex)
            print(f"Successfully loaded account: {account.address}")

            # Validate the address matches what's in the keystore
            keystore_addr = keystore.get("address", "")
            if keystore_addr and not keystore_addr.startswith("0x"):
                keystore_addr = "0x" + keystore_addr

            if keystore_addr and account.address.lower() != keystore_addr.lower():
                print(f"WARNING: Address mismatch! Keystore: {keystore_addr}, Decrypted: {account.address}")

            return account, private_key_hex
        except FileNotFoundError:
            raise Exception(f"UTC keystore file not found: {UTC_FILE_PATH}")
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise Exception(f"Failed to load account from UTC file: {e}")

    # Fallback to private key if UTC file not available
    if PRIVATE_KEY:
        try:
            # Remove '0x' prefix if present
            private_key_hex = PRIVATE_KEY.strip()
            if private_key_hex.startswith("0x"):
                private_key_hex = private_key_hex[2:]

            account = Account.from_key(private_key_hex)
            print(f"Loading account from private key: {account.address}")
            return account, private_key_hex
        except Exception as e:
            raise Exception(f"Failed to load account from private key: {e}")

    # Neither UTC nor private key available
    raise Exception(
        "UTC_FILE_PATH not found and PRIVATE_KEY not set. Please place UTC keystore file in current directory, parent, or parent of parent, or set PRIVATE_KEY in .env file."
    )


def create_and_fund_ephemeral_accounts(w3: Web3, pref_account, pref_key_hex, num: int, fund_each_eth: float):
    """
    Create ephemeral LocalAccount objects and fund each immediately from prefunded account.
    Returns list of (account_object, private_key_hex) tuples.
    """
    ephemeral = []
    ephemeral_keys = []
    amount_wei = w3.to_wei(fund_each_eth, "ether")
    gas_price = w3.eth.gas_price
    # load starting nonce for prefunded account and manage locally
    pref_nonce = w3.eth.get_transaction_count(pref_account.address)

    for i in range(num):
        acct = Account.create()  # LocalAccount
        # Extract private key explicitly and reliably
        private_key_hex = acct.key.hex()
        ephemeral.append(acct)
        ephemeral_keys.append(private_key_hex)

        tx = {
            "from": pref_account.address,
            "to": acct.address,
            "value": amount_wei,
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": pref_nonce,
            "chainId": w3.eth.chain_id,
        }
        signed = w3.eth.account.sign_transaction(tx, pref_key_hex)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"[{i+1}/{num}] Created {acct.address} and funded (tx={tx_hash.hex()})")
        pref_nonce += 1

    # Return list of tuples: [(account, private_key), ...]
    return list(zip(ephemeral, ephemeral_keys))
