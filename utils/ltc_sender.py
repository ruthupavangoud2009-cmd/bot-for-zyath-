import os
import re
import struct
import hashlib
import base64
import aiohttp
import asyncio
from typing import Optional, Tuple, Dict, Any, List
from cryptography.fernet import Fernet
import ecdsa
from ecdsa import SECP256k1
from ecdsa.util import sigdecode_der, sigencode_der

# -------------------------------------------------------------
# Base58 and Bech32 Encoding Primitives
# -------------------------------------------------------------
B58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def b58decode(v: str) -> bytes:
    num = 0
    for c in v:
        num = num * 58 + B58_CHARS.index(c)
    res = num.to_bytes((num.bit_length() + 7) // 8, "big")
    pad = 0
    for c in v:
        if c == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + res

def b58encode(b: bytes) -> str:
    num = int.from_bytes(b, "big")
    res = ""
    while num > 0:
        num, rem = divmod(num, 58)
        res = B58_CHARS[rem] + res
    pad = 0
    for byte in b:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + res

def b58check_encode(payload: bytes) -> str:
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return b58encode(payload + chk)

def b58check_decode(v: str) -> bytes:
    raw = b58decode(v)
    if len(raw) < 4:
        raise ValueError("Invalid Base58Check data: too short")
    payload, chk = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != chk:
        raise ValueError("Invalid Base58Check checksum")
    return payload

def bech32_polymod(values: List[int]) -> int:
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def convertbits(data, frombits: int, tobits: int, pad: bool = True) -> Optional[List[int]]:
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    data = [witver] + convertbits(list(witprog), 8, 5)
    checksum = bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([BECH32_CHARSET[d] for d in data + checksum])

def bech32_decode(bech: str) -> Tuple[Optional[str], Optional[List[int]]]:
    if any(ord(x) < 33 or ord(x) > 126 for x in bech):
        return None, None
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return None, None
    hrp = bech[:pos]
    data = [BECH32_CHARSET.find(x) for x in bech[pos + 1 :]]
    if any(x == -1 for x in data):
        return None, None
    if bech32_polymod(bech32_hrp_expand(hrp) + data) != 1:
        return None, None
    return hrp, data[:-6]

def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def hash160(b: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()

def varint(n: int) -> bytes:
    if n < 0xFD:
        return struct.pack("<B", n)
    elif n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    elif n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    else:
        return b"\xff" + struct.pack("<Q", n)

# -------------------------------------------------------------
# Address ScriptPubKey Resolution
# -------------------------------------------------------------
def address_to_scriptpubkey(addr: str) -> bytes:
    """Convert any standard Litecoin address (P2PKH, P2SH, or Bech32) into scriptPubKey."""
    addr = addr.strip()
    if addr.lower().startswith("ltc1"):
        hrp, data = bech32_decode(addr)
        if not hrp or hrp != "ltc" or not data:
            raise ValueError(f"Invalid Bech32 Litecoin address: {addr}")
        witver = data[0]
        witprog = bytes(convertbits(data[1:], 5, 8, False))
        if witver == 0 and len(witprog) == 20: # P2WPKH
            return bytes([0x00, 0x14]) + witprog
        elif witver == 0 and len(witprog) == 32: # P2WSH
            return bytes([0x00, 0x20]) + witprog
        else:
            return bytes([witver, len(witprog)]) + witprog

    decoded = b58check_decode(addr)
    version = decoded[0]
    payload = decoded[1:]

    # Litecoin Mainnet P2PKH: 0x30 ('L')
    if version == 0x30:
        return b"\x76\xa9\x14" + payload + b"\x88\xac"
    # Litecoin Mainnet P2SH: 0x32 ('M') or 0x05 ('3')
    elif version in (0x32, 0x05):
        return b"\xa9\x14" + payload + b"\x87"

    raise ValueError(f"Unsupported Litecoin address prefix version: {hex(version)} for {addr}")

# -------------------------------------------------------------
# Litecoin Key Wrapper
# -------------------------------------------------------------
class LitecoinKey:
    """Represents a Litecoin private key with multiple address derivations."""

    def __init__(self, signing_key: ecdsa.SigningKey, compressed: bool = True):
        self.sk = signing_key
        self.compressed = compressed
        self.privkey_bytes = self.sk.to_string()
        self.vk = self.sk.verifying_key
        pub_raw = self.vk.to_string()
        x = pub_raw[:32]
        y = pub_raw[32:]
        prefix = b"\x02" if y[-1] % 2 == 0 else b"\x03"
        self.pubkey_bytes = prefix + x if compressed else b"\x04" + pub_raw
        self.h160 = hash160(self.pubkey_bytes)

        # Addresses
        self.p2pkh_address = b58check_encode(b"\x30" + self.h160)
        self.bech32_address = bech32_encode("ltc", 0, self.h160)
        # P2SH-P2WPKH address ('M...')
        redeem_script = b"\x00\x14" + self.h160
        self.p2sh_address = b58check_encode(b"\x32" + hash160(redeem_script))

        # WIF string
        wif_payload = b"\xb0" + self.privkey_bytes
        if self.compressed:
            wif_payload += b"\x01"
        self.wif = b58check_encode(wif_payload)

    @classmethod
    def from_wif(cls, wif_str: str) -> "LitecoinKey":
        clean = wif_str.strip()
        payload = b58check_decode(clean)
        prefix = payload[0]
        # Litecoin Mainnet WIF prefix is 0xB0 (176)
        if prefix != 0xB0:
            raise ValueError(f"Invalid Litecoin WIF prefix (expected 0xB0, got {hex(prefix)})")

        key_data = payload[1:]
        compressed = False
        if len(key_data) == 33 and key_data[-1] == 0x01:
            compressed = True
            raw_key = key_data[:-1]
        elif len(key_data) == 32:
            compressed = False
            raw_key = key_data
        else:
            raise ValueError("Invalid WIF key payload length")

        sk = ecdsa.SigningKey.from_string(raw_key, curve=SECP256k1)
        return cls(sk, compressed=compressed)

    @classmethod
    def generate(cls) -> "LitecoinKey":
        sk = ecdsa.SigningKey.generate(curve=SECP256k1)
        return cls(sk, compressed=True)

# -------------------------------------------------------------
# AES-256 Fernet Encryption For Stored WIF Keys
# -------------------------------------------------------------
_KEY_SALT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", ".wallet_secret")

def _get_encryption_cipher() -> Fernet:
    os.makedirs(os.path.dirname(_KEY_SALT_FILE), exist_ok=True)
    env_secret = os.getenv("KYOKA_WALLET_KEY")
    if env_secret:
        seed = env_secret.encode("utf-8")
    elif os.path.exists(_KEY_SALT_FILE):
        with open(_KEY_SALT_FILE, "rb") as f:
            seed = f.read().strip()
    else:
        seed = base64.urlsafe_b64encode(os.urandom(32))
        try:
            with open(_KEY_SALT_FILE, "wb") as f:
                f.write(seed)
        except Exception:
            pass

    key = base64.urlsafe_b64encode(hashlib.sha256(seed + b"_kyoka_ltc_engine_2026").digest())
    return Fernet(key)

def encrypt_wif(wif: str) -> str:
    """Encrypt a Litecoin WIF key with AES-256 for secure database storage."""
    cipher = _get_encryption_cipher()
    return cipher.encrypt(wif.strip().encode("utf-8")).decode("utf-8")

def decrypt_wif(encrypted_str: str) -> str:
    """Decrypt a Litecoin WIF key from the database."""
    cipher = _get_encryption_cipher()
    return cipher.decrypt(encrypted_str.strip().encode("utf-8")).decode("utf-8")

# -------------------------------------------------------------
# Flexible Payment Input Parsing
# -------------------------------------------------------------
def parse_payment_amount(amount_raw: str, currency_hint: Optional[str] = None) -> Tuple[float, str]:
    """
    Parses user amount input flexibly.
    Supports:
      '1$', '$1', '1$ ltc', '$1 ltc', '1.50$', '$2.25', '5 usd' -> (val, 'USD')
      '0.05 ltc', '0.05ltc', '0.05', '1 ltc' -> (val, 'LTC')
    """
    s = amount_raw.strip().lower()
    if currency_hint:
        hint = currency_hint.strip().lower()
        if "usd" in hint or "$" in hint:
            s += " usd"
        elif "ltc" in hint:
            s += " ltc"

    is_usd = False
    if "$" in s or "usd" in s:
        is_usd = True

    # Extract digits and decimal
    clean_num = re.sub(r"[^0-9\.]", "", s)
    if not clean_num:
        raise ValueError(f"Could not parse numerical amount from '{amount_raw}'")

    try:
        val = float(clean_num)
    except ValueError:
        raise ValueError(f"Invalid numeric value '{clean_num}'")

    if val <= 0:
        raise ValueError("Payment amount must be greater than zero")

    currency = "USD" if is_usd else "LTC"
    return val, currency

def convert_amount_to_sats(amount: float, currency: str, ltc_usd_price: float) -> Tuple[int, float, float]:
    """
    Converts amount to satoshis, LTC float, and USD float.
    Returns: (amount_sats, amount_ltc, amount_usd)
    """
    if currency.upper() == "USD":
        if ltc_usd_price <= 0:
            raise ValueError("Invalid live LTC price feed for conversion")
        amount_ltc = amount / ltc_usd_price
        amount_usd = amount
    else:
        amount_ltc = amount
        amount_usd = amount * ltc_usd_price

    sats = int(round(amount_ltc * 1e8))
    if sats < 1000: # Below 0.00001 LTC (dust limit)
        raise ValueError(f"Amount {amount_ltc:.8f} LTC is below the network minimum dust limit (0.00001 LTC)")

    return sats, amount_ltc, amount_usd

# -------------------------------------------------------------
# Blockchain UTXO Fetcher & Fee Estimation
# -------------------------------------------------------------
async def fetch_utxos(address: str) -> List[Dict[str, Any]]:
    """Fetch unspent transaction outputs (UTXOs) from public LTC nodes."""
    clean_addr = address.strip()
    utxos = []

    # 1. litecoinspace.org (mempool instance)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://litecoinspace.org/api/address/{clean_addr}/utxo",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data:
                        status = item.get("status", {})
                        # Accept confirmed or unconfirmed mempool UTXOs
                        utxos.append({
                            "txid": item.get("txid"),
                            "vout": int(item.get("vout", 0)),
                            "value": int(item.get("value", 0)),
                            "confirmed": status.get("confirmed", False)
                        })
                    return utxos
    except Exception:
        pass

    # 2. BlockCypher fallback
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.blockcypher.com/v1/ltc/main/addrs/{clean_addr}?unspentOnly=true",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("txrefs", []) + data.get("unconfirmed_txrefs", []):
                        if item.get("tx_output_n", -1) >= 0:
                            utxos.append({
                                "txid": item.get("tx_hash"),
                                "vout": int(item.get("tx_output_n")),
                                "value": int(item.get("value", 0)),
                                "confirmed": item.get("confirmations", 0) > 0
                            })
                    return utxos
    except Exception:
        pass

    return utxos

async def get_recommended_feerate() -> int:
    """Fetch recommended sat/vB fee rate with a safe default of 1-2 sat/vB."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://litecoinspace.org/api/v1/fees/recommended",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fastest = int(data.get("fastestFee", 1))
                    return max(1, min(fastest, 5)) # Cap at 5 sat/vB to avoid overpaying
    except Exception:
        pass
    return 1

# -------------------------------------------------------------
# Raw Transaction Assembly & ECDSA Signing
# -------------------------------------------------------------
def build_and_sign_p2pkh_tx(
    key: LitecoinKey,
    utxos: List[Dict[str, Any]],
    recipient_address: str,
    amount_sats: int,
    sat_per_vb: int = 1
) -> Dict[str, Any]:
    """
    Constructs and signs a standard Legacy P2PKH transaction with change.
    Outputs raw transaction hex ready for broadcast.
    """
    recipient_script = address_to_scriptpubkey(recipient_address)
    sender_script = address_to_scriptpubkey(key.p2pkh_address)

    # Sort UTXOs largest first
    sorted_utxos = sorted(utxos, key=lambda u: u["value"], reverse=True)

    # Coin selection
    selected_utxos = []
    total_input_sats = 0
    dust_threshold = 546

    # Estimate size: 148 bytes per P2PKH vin + 34 bytes per vout + 10 header bytes
    fee_sats = 0
    for u in sorted_utxos:
        selected_utxos.append(u)
        total_input_sats += u["value"]

        # Calculate estimated size (assuming 2 outputs: recipient + change)
        est_vbytes = 10 + len(selected_utxos) * 148 + 2 * 34
        fee_sats = max(250, est_vbytes * sat_per_vb)

        if total_input_sats >= amount_sats + fee_sats:
            break

    if total_input_sats < amount_sats + fee_sats:
        missing = (amount_sats + fee_sats) - total_input_sats
        raise ValueError(
            f"Insufficient wallet balance! Available: {total_input_sats / 1e8:.6f} LTC. "
            f"Required (amount + fee): {(amount_sats + fee_sats) / 1e8:.6f} LTC (Short by {missing / 1e8:.6f} LTC)."
        )

    change_sats = total_input_sats - amount_sats - fee_sats
    has_change = change_sats >= dust_threshold

    # Build outputs
    version = struct.pack("<I", 1)
    locktime = struct.pack("<I", 0)
    vin_count = varint(len(selected_utxos))

    outputs_bytes = b""
    # 1. Recipient output
    outputs_bytes += struct.pack("<Q", amount_sats) + varint(len(recipient_script)) + recipient_script
    output_count = 1

    # 2. Change output
    if has_change:
        outputs_bytes += struct.pack("<Q", change_sats) + varint(len(sender_script)) + sender_script
        output_count += 1
    else:
        # Give dust change to miners fee
        fee_sats += change_sats
        change_sats = 0

    vout_count = varint(output_count)

    # Sign each input
    signed_inputs = b""
    for i, utxo in enumerate(selected_utxos):
        # Create preimage where input `i` has sender_script and other inputs have empty scripts
        preimage_inputs = b""
        for j, u in enumerate(selected_utxos):
            txid_bytes = bytes.fromhex(u["txid"])[::-1]
            vout_bytes = struct.pack("<I", u["vout"])
            seq_bytes = b"\xff\xff\xff\xff"
            if j == i:
                preimage_inputs += txid_bytes + vout_bytes + varint(len(sender_script)) + sender_script + seq_bytes
            else:
                preimage_inputs += txid_bytes + vout_bytes + b"\x00" + seq_bytes

        sighash_type = struct.pack("<I", 1) # SIGHASH_ALL
        preimage = version + vin_count + preimage_inputs + vout_count + outputs_bytes + locktime + sighash_type
        h = dsha256(preimage)

        # Sign digest
        sig_der = key.sk.sign_digest(h, sigencode=sigencode_der)
        r, s = sigdecode_der(sig_der, SECP256k1.order)
        if s > SECP256k1.order // 2:
            s = SECP256k1.order - s
            sig_der = sigencode_der(r, s, SECP256k1.order)
        sig_with_type = sig_der + b"\x01"

        # scriptSig: <len(sig)> <sig> <len(pub)> <pub>
        scriptsig = varint(len(sig_with_type)) + sig_with_type + varint(len(key.pubkey_bytes)) + key.pubkey_bytes

        txid_bytes = bytes.fromhex(utxo["txid"])[::-1]
        vout_bytes = struct.pack("<I", utxo["vout"])
        signed_inputs += txid_bytes + vout_bytes + varint(len(scriptsig)) + scriptsig + b"\xff\xff\xff\xff"

    raw_tx = version + vin_count + signed_inputs + vout_count + outputs_bytes + locktime
    raw_hex = raw_tx.hex()
    computed_txid = dsha256(raw_tx)[::-1].hex()

    return {
        "raw_hex": raw_hex,
        "txid": computed_txid,
        "amount_sats": amount_sats,
        "amount_ltc": amount_sats / 1e8,
        "fee_sats": fee_sats,
        "fee_ltc": fee_sats / 1e8,
        "change_sats": change_sats,
        "change_ltc": change_sats / 1e8,
        "recipient": recipient_address,
        "sender": key.p2pkh_address,
        "inputs_count": len(selected_utxos),
        "total_input_sats": total_input_sats
    }

def build_and_sign_segwit_tx(
    key: LitecoinKey,
    utxos: List[Dict[str, Any]],
    recipient_address: str,
    amount_sats: int,
    sat_per_vb: int = 1
) -> Dict[str, Any]:
    """
    Constructs and signs a Native SegWit (v0 P2WPKH `ltc1...`) transaction.
    Uses BIP143 sighash calculation and witness serialization.
    """
    recipient_script = address_to_scriptpubkey(recipient_address)
    sender_script = address_to_scriptpubkey(key.bech32_address)
    script_code = b"\x19\x76\xa9\x14" + key.h160 + b"\x88\xac"

    sorted_utxos = sorted(utxos, key=lambda u: u["value"], reverse=True)
    selected_utxos = []
    total_input_sats = 0
    dust_threshold = 546

    # Native SegWit has lower vBytes (~68 vB per vin + 31 vB per vout + 11 header)
    fee_sats = 0
    for u in sorted_utxos:
        selected_utxos.append(u)
        total_input_sats += u["value"]
        est_vbytes = 11 + len(selected_utxos) * 68 + 2 * 31
        fee_sats = max(180, est_vbytes * sat_per_vb)
        if total_input_sats >= amount_sats + fee_sats:
            break

    if total_input_sats < amount_sats + fee_sats:
        missing = (amount_sats + fee_sats) - total_input_sats
        raise ValueError(
            f"Insufficient SegWit wallet balance! Available: {total_input_sats / 1e8:.6f} LTC. "
            f"Required: {(amount_sats + fee_sats) / 1e8:.6f} LTC (Short by {missing / 1e8:.6f} LTC)."
        )

    change_sats = total_input_sats - amount_sats - fee_sats
    has_change = change_sats >= dust_threshold

    version = struct.pack("<I", 2)
    locktime = struct.pack("<I", 0)
    sighash_type = struct.pack("<I", 1) # SIGHASH_ALL

    # Outputs
    outputs_bytes = struct.pack("<Q", amount_sats) + varint(len(recipient_script)) + recipient_script
    output_count = 1
    if has_change:
        outputs_bytes += struct.pack("<Q", change_sats) + varint(len(sender_script)) + sender_script
        output_count += 1
    else:
        fee_sats += change_sats
        change_sats = 0

    vout_count = varint(output_count)

    # BIP143 precomputations
    all_outpoints = b"".join([bytes.fromhex(u["txid"])[::-1] + struct.pack("<I", u["vout"]) for u in selected_utxos])
    hash_prevouts = dsha256(all_outpoints)
    n_sequences = b"\xff\xff\xff\xff" * len(selected_utxos)
    hash_sequence = dsha256(n_sequences)
    hash_outputs = dsha256(outputs_bytes)

    # Build inputs and witnesses
    inputs_bytes = b""
    witnesses_bytes = b""

    for u in selected_utxos:
        outpoint = bytes.fromhex(u["txid"])[::-1] + struct.pack("<I", u["vout"])
        n_sequence = b"\xff\xff\xff\xff"
        inputs_bytes += outpoint + b"\x00" + n_sequence # empty scriptSig in SegWit

        # BIP143 preimage
        preimage = (
            version +
            hash_prevouts +
            hash_sequence +
            outpoint +
            script_code +
            struct.pack("<Q", u["value"]) +
            n_sequence +
            hash_outputs +
            locktime +
            sighash_type
        )
        h = dsha256(preimage)

        # Sign digest
        sig_der = key.sk.sign_digest(h, sigencode=sigencode_der)
        r, s = sigdecode_der(sig_der, SECP256k1.order)
        if s > SECP256k1.order // 2:
            s = SECP256k1.order - s
            sig_der = sigencode_der(r, s, SECP256k1.order)
        sig_with_type = sig_der + b"\x01"

        # Witness item: 2 items (signature and compressed pubkey)
        witnesses_bytes += (
            struct.pack("<B", 2) +
            varint(len(sig_with_type)) + sig_with_type +
            varint(len(key.pubkey_bytes)) + key.pubkey_bytes
        )

    # SegWit serialization: version + marker(00) + flag(01) + vin + vout + witness + locktime
    raw_tx = (
        version +
        b"\x00\x01" +
        varint(len(selected_utxos)) +
        inputs_bytes +
        vout_count +
        outputs_bytes +
        witnesses_bytes +
        locktime
    )

    # For SegWit txid: computed over legacy serialization without witness
    legacy_serialization = version + varint(len(selected_utxos)) + inputs_bytes + vout_count + outputs_bytes + locktime
    computed_txid = dsha256(legacy_serialization)[::-1].hex()

    return {
        "raw_hex": raw_tx.hex(),
        "txid": computed_txid,
        "amount_sats": amount_sats,
        "amount_ltc": amount_sats / 1e8,
        "fee_sats": fee_sats,
        "fee_ltc": fee_sats / 1e8,
        "change_sats": change_sats,
        "change_ltc": change_sats / 1e8,
        "recipient": recipient_address,
        "sender": key.bech32_address,
        "inputs_count": len(selected_utxos),
        "total_input_sats": total_input_sats
    }

# -------------------------------------------------------------
# Transaction Broadcaster
# -------------------------------------------------------------
async def broadcast_raw_tx(raw_hex: str) -> Dict[str, Any]:
    """Broadcasts a signed raw transaction to the Litecoin network."""
    clean_hex = raw_hex.strip()

    # 1. Primary: litecoinspace.org (mempool broadcast)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://litecoinspace.org/api/tx",
                data=clean_hex,
                headers={"Content-Type": "text/plain"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp_text = (await resp.text()).strip()
                if resp.status == 200 and len(resp_text) == 64:
                    return {"success": True, "txid": resp_text, "source": "litecoinspace"}
                elif resp.status != 200:
                    last_error = f"litecoinspace error {resp.status}: {resp_text}"
                else:
                    last_error = f"litecoinspace unexpected response: {resp_text}"
    except Exception as e:
        last_error = f"litecoinspace request failed: {e}"

    # 2. Fallback: BlockCypher push endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.blockcypher.com/v1/ltc/main/txs/push",
                json={"tx": clean_hex},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200 or resp.status == 201:
                    data = await resp.json()
                    tx_hash = data.get("tx", {}).get("hash") or data.get("hash")
                    if tx_hash:
                        return {"success": True, "txid": tx_hash, "source": "blockcypher"}
                else:
                    data = await resp.text()
                    last_error += f" | blockcypher error {resp.status}: {data}"
    except Exception as e:
        last_error += f" | blockcypher request failed: {e}"

    return {"success": False, "error": last_error, "txid": None}

# -------------------------------------------------------------
# High-Level Payment Pipeline
# -------------------------------------------------------------
async def execute_onchain_payment(
    key: LitecoinKey,
    recipient_address: str,
    amount_sats: int,
    sat_per_vb: Optional[int] = None
) -> Dict[str, Any]:
    """
    Full automated pipeline:
    1. Checks UTXOs for both P2PKH and Bech32 address.
    2. Builds and signs transaction using the funded address.
    3. Broadcasts raw transaction to network.
    4. Returns confirmation dictionary with explorer link.
    """
    if sat_per_vb is None:
        sat_per_vb = await get_recommended_feerate()

    # Check P2PKH address UTXOs
    p2pkh_utxos = await fetch_utxos(key.p2pkh_address)
    total_p2pkh = sum(u["value"] for u in p2pkh_utxos)

    # Check SegWit address UTXOs
    segwit_utxos = await fetch_utxos(key.bech32_address)
    total_segwit = sum(u["value"] for u in segwit_utxos)

    # Pick whichever has sufficient funds
    if total_p2pkh >= amount_sats:
        tx_data = build_and_sign_p2pkh_tx(key, p2pkh_utxos, recipient_address, amount_sats, sat_per_vb)
    elif total_segwit >= amount_sats:
        tx_data = build_and_sign_segwit_tx(key, segwit_utxos, recipient_address, amount_sats, sat_per_vb)
    elif (total_p2pkh + total_segwit) >= amount_sats:
        # If split between both, prefer the larger one or raise notice
        if total_p2pkh >= total_segwit:
            tx_data = build_and_sign_p2pkh_tx(key, p2pkh_utxos, recipient_address, amount_sats, sat_per_vb)
        else:
            tx_data = build_and_sign_segwit_tx(key, segwit_utxos, recipient_address, amount_sats, sat_per_vb)
    else:
        raise ValueError(
            f"Insufficient wallet funds! Your account balance is {(total_p2pkh + total_segwit) / 1e8:.6f} LTC "
            f"({total_p2pkh / 1e8:.6f} LTC legacy, {total_segwit / 1e8:.6f} LTC segwit). "
            f"Required: {amount_sats / 1e8:.6f} LTC."
        )

    # Broadcast
    broadcast_res = await broadcast_raw_tx(tx_data["raw_hex"])
    if not broadcast_res.get("success"):
        return {
            "success": False,
            "error": broadcast_res.get("error", "Broadcast failed"),
            "txid": None,
            "tx_data": tx_data
        }

    real_txid = broadcast_res.get("txid") or tx_data["txid"]
    return {
        "success": True,
        "txid": real_txid,
        "explorer_url": f"https://litecoinspace.org/tx/{real_txid}",
        "amount_sats": tx_data["amount_sats"],
        "amount_ltc": tx_data["amount_ltc"],
        "fee_sats": tx_data["fee_sats"],
        "fee_ltc": tx_data["fee_ltc"],
        "sender": tx_data["sender"],
        "recipient": tx_data["recipient"],
        "change_ltc": tx_data["change_ltc"]
    }
