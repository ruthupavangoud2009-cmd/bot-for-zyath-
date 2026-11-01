import aiohttp
import asyncio
import time
import re
from typing import Optional, Dict, Any, List

# Regex patterns for Litecoin Mainnet addresses
LTC_LEGACY_REGEX = re.compile(r"^L[a-km-zA-HJ-NP-Z1-9]{26,34}$")
LTC_P2SH_REGEX = re.compile(r"^[M3][a-km-zA-HJ-NP-Z1-9]{26,34}$")
LTC_BECH32_REGEX = re.compile(r"^ltc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59}$", re.IGNORECASE)
LTC_TXID_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")

_price_cache = {"price": 0.0, "timestamp": 0.0}

def is_valid_ltc_address(address: str) -> bool:
    if not address or not isinstance(address, str):
        return False
    addr = address.strip()
    return bool(LTC_LEGACY_REGEX.match(addr) or LTC_P2SH_REGEX.match(addr) or LTC_BECH32_REGEX.match(addr))

def is_valid_txid(txid: str) -> bool:
    if not txid or not isinstance(txid, str):
        return False
    return bool(LTC_TXID_REGEX.match(txid.strip()))

def shorten_address(address: str, front: int = 6, back: int = 6) -> str:
    if not address:
        return ""
    addr = address.strip()
    if len(addr) <= front + back:
        return addr
    return f"{addr[:front]}...{addr[-back:]}"

def get_ltc_qr_url(address: str, amount: Optional[float] = None) -> str:
    addr = address.strip()
    if amount and amount > 0:
        data = f"litecoin:{addr}?amount={amount:.8f}"
    else:
        data = f"litecoin:{addr}"
    import urllib.parse
    encoded = urllib.parse.quote(data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}"

async def get_ltc_price() -> float:
    """Retrieve live LTC/USD price with 60-second caching and multiple fallbacks."""
    now = time.time()
    if _price_cache["price"] > 0 and (now - _price_cache["timestamp"]) < 60.0:
        return _price_cache["price"]

    # 1. CoinGecko
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    p = float(data.get("litecoin", {}).get("usd", 0.0))
                    if p > 0:
                        _price_cache["price"] = p
                        _price_cache["timestamp"] = now
                        return p
    except Exception:
        pass

    # 2. Binance
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=LTCUSDT",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    p = float(data.get("price", 0.0))
                    if p > 0:
                        _price_cache["price"] = p
                        _price_cache["timestamp"] = now
                        return p
    except Exception:
        pass

    # 3. Coinbase
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coinbase.com/v2/prices/LTC-USD/spot",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    p = float(data.get("data", {}).get("amount", 0.0))
                    if p > 0:
                        _price_cache["price"] = p
                        _price_cache["timestamp"] = now
                        return p
    except Exception:
        pass

    # If cache exists return it even if stale, else fallback default
    return _price_cache["price"] if _price_cache["price"] > 0 else 100.0

async def get_ltc_balance(address: str) -> Dict[str, Any]:
    """Fetch confirmed and unconfirmed LTC balance from blockchain APIs."""
    addr = address.strip()
    result = {
        "address": addr,
        "balance_ltc": 0.0,
        "unconfirmed_ltc": 0.0,
        "total_received_ltc": 0.0,
        "tx_count": 0,
        "success": False,
        "source": None
    }

    # Provider 1: litecoinspace.org (mempool instance for LTC)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://litecoinspace.org/api/address/{addr}",
                timeout=aiohttp.ClientTimeout(total=7)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    chain_stats = data.get("chain_stats", {})
                    mempool_stats = data.get("mempool_stats", {})

                    confirmed_sats = chain_stats.get("funded_txo_sum", 0) - chain_stats.get("spent_txo_sum", 0)
                    unconfirmed_sats = mempool_stats.get("funded_txo_sum", 0) - mempool_stats.get("spent_txo_sum", 0)
                    total_received_sats = chain_stats.get("funded_txo_sum", 0)

                    result["balance_ltc"] = max(0.0, confirmed_sats / 1e8)
                    result["unconfirmed_ltc"] = unconfirmed_sats / 1e8
                    result["total_received_ltc"] = total_received_sats / 1e8
                    result["tx_count"] = chain_stats.get("tx_count", 0) + mempool_stats.get("tx_count", 0)
                    result["success"] = True
                    result["source"] = "litecoinspace"
                    return result
    except Exception:
        pass

    # Provider 2: BlockCypher
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.blockcypher.com/v1/ltc/main/addrs/{addr}/balance",
                timeout=aiohttp.ClientTimeout(total=7)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balance_sats = data.get("balance", 0)
                    unconfirmed_sats = data.get("unconfirmed_balance", 0)
                    total_received_sats = data.get("total_received", 0)

                    result["balance_ltc"] = max(0.0, balance_sats / 1e8)
                    result["unconfirmed_ltc"] = unconfirmed_sats / 1e8
                    result["total_received_ltc"] = total_received_sats / 1e8
                    result["tx_count"] = data.get("final_n_tx", 0)
                    result["success"] = True
                    result["source"] = "blockcypher"
                    return result
    except Exception:
        pass

    # Provider 3: SoChain
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://sochain.com/api/v2/get_address_balance/LTC/{addr}",
                timeout=aiohttp.ClientTimeout(total=7)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "success":
                        d = data.get("data", {})
                        result["balance_ltc"] = float(d.get("confirmed_balance", 0.0))
                        result["unconfirmed_ltc"] = float(d.get("unconfirmed_balance", 0.0))
                        result["success"] = True
                        result["source"] = "sochain"
                        return result
    except Exception:
        pass

    return result

async def get_ltc_address_transactions(address: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve recent incoming and outgoing transactions for an address."""
    addr = address.strip()
    txs = []

    # Try litecoinspace.org
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://litecoinspace.org/api/address/{addr}/txs",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data[:limit]:
                        txid = item.get("txid", "")
                        status = item.get("status", {})
                        confirmed = status.get("confirmed", False)
                        block_time = status.get("block_time", int(time.time()))

                        # Calculate net amount for this address
                        received = sum(out.get("value", 0) for out in item.get("vout", []) if out.get("scriptpubkey_address") == addr)
                        sent = sum(inp.get("prevout", {}).get("value", 0) for inp in item.get("vin", []) if inp.get("prevout", {}).get("scriptpubkey_address") == addr)
                        net = (received - sent) / 1e8

                        txs.append({
                            "txid": txid,
                            "confirmed": confirmed,
                            "block_time": block_time,
                            "amount_ltc": abs(net),
                            "is_incoming": net >= 0,
                            "confirmations": 1 if confirmed else 0
                        })
                    return txs
    except Exception:
        pass

    # Try BlockCypher
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.blockcypher.com/v1/ltc/main/addrs/{addr}?limit={limit}",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    txrefs = data.get("txrefs", []) + data.get("unconfirmed_txrefs", [])
                    for item in txrefs[:limit]:
                        txid = item.get("tx_hash", "")
                        conf = item.get("confirmations", 0)
                        value = item.get("value", 0) / 1e8
                        is_incoming = item.get("tx_output_n", -1) >= 0

                        txs.append({
                            "txid": txid,
                            "confirmed": conf > 0,
                            "block_time": int(time.time()),
                            "amount_ltc": value,
                            "is_incoming": is_incoming,
                            "confirmations": conf
                        })
                    return txs
    except Exception:
        pass

    return txs

async def get_ltc_tx_status(txid: str) -> Dict[str, Any]:
    """Retrieve full transaction details, confirmations, and outputs."""
    tx_hash = txid.strip()
    result = {
        "txid": tx_hash,
        "found": False,
        "confirmed": False,
        "confirmations": 0,
        "block_height": 0,
        "timestamp": int(time.time()),
        "outputs": [],
        "total_value_ltc": 0.0,
        "source": None
    }

    # 1. litecoinspace.org
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://litecoinspace.org/api/tx/{tx_hash}",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["found"] = True
                    status = data.get("status", {})
                    result["confirmed"] = status.get("confirmed", False)
                    result["block_height"] = status.get("block_height", 0)
                    result["timestamp"] = status.get("block_time", int(time.time()))

                    # If confirmed, calculate confirmations using current block height
                    if result["confirmed"] and result["block_height"] > 0:
                        try:
                            async with session.get("https://litecoinspace.org/api/blocks/tip/height", timeout=3) as h_resp:
                                if h_resp.status == 200:
                                    tip_height = int(await h_resp.text())
                                    result["confirmations"] = max(1, tip_height - result["block_height"] + 1)
                        except Exception:
                            result["confirmations"] = 1
                    else:
                        result["confirmations"] = 0

                    outputs = []
                    total_val = 0
                    for out in data.get("vout", []):
                        val_sats = out.get("value", 0)
                        addr = out.get("scriptpubkey_address", "")
                        outputs.append({"address": addr, "amount_ltc": val_sats / 1e8})
                        total_val += val_sats
                    result["outputs"] = outputs
                    result["total_value_ltc"] = total_val / 1e8
                    result["source"] = "litecoinspace"
                    return result
    except Exception:
        pass

    # 2. BlockCypher
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.blockcypher.com/v1/ltc/main/txs/{tx_hash}",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["found"] = True
                    confs = data.get("confirmations", 0)
                    result["confirmations"] = confs
                    result["confirmed"] = confs > 0
                    result["block_height"] = data.get("block_height", 0)
                    outputs = []
                    total_val = 0
                    for out in data.get("outputs", []):
                        addrs = out.get("addresses", [])
                        addr = addrs[0] if addrs else ""
                        val = out.get("value", 0) / 1e8
                        outputs.append({"address": addr, "amount_ltc": val})
                        total_val += val
                    result["outputs"] = outputs
                    result["total_value_ltc"] = total_val
                    result["source"] = "blockcypher"
                    return result
    except Exception:
        pass

    return result

async def verify_ltc_payment(
    txid: str,
    expected_address: str,
    expected_amount_ltc: float,
    min_confirmations: int = 1
) -> Dict[str, Any]:
    """
    Verify payment independently against the Litecoin blockchain.
    Checks destination address, amount, and required confirmations.
    """
    if not is_valid_txid(txid):
        return {
            "verified": False,
            "paid": False,
            "confirmations": 0,
            "amount_received": 0.0,
            "expected_amount": expected_amount_ltc,
            "error": "Invalid Litecoin transaction ID format. Must be a 64-character hexadecimal string."
        }

    tx_info = await get_ltc_tx_status(txid)
    if not tx_info.get("found"):
        return {
            "verified": False,
            "paid": False,
            "confirmations": 0,
            "amount_received": 0.0,
            "expected_amount": expected_amount_ltc,
            "error": "Transaction not found on the Litecoin blockchain yet. Please wait a moment for propagation."
        }

    clean_target_addr = expected_address.strip().lower()
    amount_sent_to_target = 0.0

    for out in tx_info.get("outputs", []):
        out_addr = (out.get("address") or "").strip().lower()
        if out_addr == clean_target_addr:
            amount_sent_to_target += float(out.get("amount_ltc", 0.0))

    if amount_sent_to_target <= 0.0:
        return {
            "verified": False,
            "paid": False,
            "confirmations": tx_info.get("confirmations", 0),
            "amount_received": 0.0,
            "expected_amount": expected_amount_ltc,
            "error": f"Transaction destination does not match the shop wallet address ({shorten_address(expected_address)})."
        }

    # Allow a tiny float tolerance of 0.000005 LTC
    tolerance = 0.000005
    is_amount_sufficient = (amount_sent_to_target + tolerance) >= expected_amount_ltc
    confs = tx_info.get("confirmations", 0)
    has_enough_confirmations = confs >= min_confirmations

    if not is_amount_sufficient:
        return {
            "verified": False,
            "paid": False,
            "underpaid": True,
            "confirmations": confs,
            "amount_received": amount_sent_to_target,
            "expected_amount": expected_amount_ltc,
            "error": f"Underpayment detected: Received {amount_sent_to_target:.6f} LTC, but order requires {expected_amount_ltc:.6f} LTC."
        }

    if not has_enough_confirmations:
        return {
            "verified": True,
            "paid": False,
            "pending_confirmation": True,
            "confirmations": confs,
            "min_confirmations": min_confirmations,
            "amount_received": amount_sent_to_target,
            "expected_amount": expected_amount_ltc,
            "error": f"Transaction found with {confs}/{min_confirmations} confirmations. Awaiting blockchain confirmation."
        }

    return {
        "verified": True,
        "paid": True,
        "confirmations": confs,
        "min_confirmations": min_confirmations,
        "amount_received": amount_sent_to_target,
        "expected_amount": expected_amount_ltc,
        "block_height": tx_info.get("block_height"),
        "error": None
    }
