import sys
import unittest
from utils.ltc_sender import (
    LitecoinKey,
    encrypt_wif,
    decrypt_wif,
    parse_payment_amount,
    convert_amount_to_sats,
    address_to_scriptpubkey,
    build_and_sign_p2pkh_tx,
    build_and_sign_segwit_tx
)

class TestLtcSender(unittest.TestCase):

    def test_key_generation_and_wif(self):
        key = LitecoinKey.generate()
        self.assertTrue(key.p2pkh_address.startswith("L"))
        self.assertTrue(key.bech32_address.startswith("ltc1"))
        self.assertTrue(key.p2sh_address.startswith("M") or key.p2sh_address.startswith("3"))
        self.assertTrue(key.wif.startswith("T") or key.wif.startswith("6"))

        # Reload from WIF
        reloaded = LitecoinKey.from_wif(key.wif)
        self.assertEqual(reloaded.p2pkh_address, key.p2pkh_address)
        self.assertEqual(reloaded.bech32_address, key.bech32_address)
        self.assertEqual(reloaded.p2sh_address, key.p2sh_address)

    def test_aes_encryption(self):
        key = LitecoinKey.generate()
        enc = encrypt_wif(key.wif)
        dec = decrypt_wif(enc)
        self.assertEqual(dec, key.wif)
        self.assertNotEqual(enc, key.wif)

    def test_amount_parsing(self):
        test_cases = [
            ("1$", 1.0, "USD"),
            ("$1", 1.0, "USD"),
            ("1$ ltc", 1.0, "USD"),
            ("$2.50 ltc", 2.50, "USD"),
            ("5 usd", 5.0, "USD"),
            ("0.05 ltc", 0.05, "LTC"),
            ("0.05", 0.05, "LTC"),
            ("1.25 LTC", 1.25, "LTC"),
            ("10$", 10.0, "USD"),
            ("$10", 10.0, "USD"),
        ]
        for raw, exp_val, exp_curr in test_cases:
            val, curr = parse_payment_amount(raw)
            self.assertAlmostEqual(val, exp_val, places=6)
            self.assertEqual(curr, exp_curr)

    def test_convert_to_sats(self):
        # 100 USD at 100 USD/LTC -> 1 LTC -> 100,000,000 sats
        sats, ltc, usd = convert_amount_to_sats(100.0, "USD", 100.0)
        self.assertEqual(sats, 100_000_000)
        self.assertAlmostEqual(ltc, 1.0)
        self.assertAlmostEqual(usd, 100.0)

        # 0.01 LTC -> 1,000,000 sats
        sats, ltc, usd = convert_amount_to_sats(0.01, "LTC", 80.0)
        self.assertEqual(sats, 1_000_000)
        self.assertAlmostEqual(ltc, 0.01)
        self.assertAlmostEqual(usd, 0.80)

    def test_address_to_scriptpubkey(self):
        key = LitecoinKey.generate()
        script_p2pkh = address_to_scriptpubkey(key.p2pkh_address)
        self.assertTrue(script_p2pkh.startswith(b"\x76\xa9\x14"))
        self.assertTrue(script_p2pkh.endswith(b"\x88\xac"))

        script_segwit = address_to_scriptpubkey(key.bech32_address)
        self.assertTrue(script_segwit.startswith(b"\x00\x14"))

        script_p2sh = address_to_scriptpubkey(key.p2sh_address)
        self.assertTrue(script_p2sh.startswith(b"\xa9\x14"))
        self.assertTrue(script_p2sh.endswith(b"\x87"))

    def test_p2pkh_tx_assembly(self):
        key = LitecoinKey.generate()
        mock_utxos = [{
            "txid": "0102030405060708091011121314151617181920212223242526272829303132",
            "vout": 0,
            "value": 10_000_000, # 0.1 LTC
            "confirmed": True
        }]
        res = build_and_sign_p2pkh_tx(key, mock_utxos, key.p2pkh_address, 1_000_000)
        self.assertTrue(len(res["raw_hex"]) > 100)
        self.assertEqual(res["amount_sats"], 1_000_000)
        self.assertTrue(res["fee_sats"] >= 200)
        self.assertEqual(len(res["txid"]), 64)

    def test_segwit_tx_assembly(self):
        key = LitecoinKey.generate()
        mock_utxos = [{
            "txid": "0102030405060708091011121314151617181920212223242526272829303132",
            "vout": 0,
            "value": 10_000_000, # 0.1 LTC
            "confirmed": True
        }]
        res = build_and_sign_segwit_tx(key, mock_utxos, key.bech32_address, 1_000_000)
        self.assertTrue(len(res["raw_hex"]) > 100)
        self.assertEqual(res["amount_sats"], 1_000_000)
        self.assertTrue(res["fee_sats"] >= 150)
        self.assertEqual(len(res["txid"]), 64)

if __name__ == "__main__":
    unittest.main()
