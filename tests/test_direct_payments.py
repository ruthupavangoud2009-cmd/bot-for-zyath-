import unittest
import asyncio
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
from utils.database import db

class TestDirectPayments(unittest.TestCase):

    def test_wif_and_address_derivations(self):
        key = LitecoinKey.generate()
        self.assertTrue(key.p2pkh_address.startswith("L"), f"Invalid P2PKH: {key.p2pkh_address}")
        self.assertTrue(key.bech32_address.startswith("ltc1"), f"Invalid Bech32: {key.bech32_address}")
        self.assertTrue(key.p2sh_address.startswith("M") or key.p2sh_address.startswith("3"))
        self.assertTrue(key.wif.startswith("T") or key.wif.startswith("6"))

        reloaded = LitecoinKey.from_wif(key.wif)
        self.assertEqual(reloaded.p2pkh_address, key.p2pkh_address)
        self.assertEqual(reloaded.bech32_address, key.bech32_address)
        self.assertEqual(reloaded.p2sh_address, key.p2sh_address)

    def test_key_encryption(self):
        key = LitecoinKey.generate()
        enc = encrypt_wif(key.wif)
        self.assertNotEqual(enc, key.wif)
        dec = decrypt_wif(enc)
        self.assertEqual(dec, key.wif)

    def test_user_requested_amount_syntax(self):
        # 1$ ltc
        val, curr = parse_payment_amount("1$ ltc")
        self.assertEqual(val, 1.0)
        self.assertEqual(curr, "USD")

        # 1$
        val, curr = parse_payment_amount("1$")
        self.assertEqual(val, 1.0)
        self.assertEqual(curr, "USD")

        # $1
        val, curr = parse_payment_amount("$1")
        self.assertEqual(val, 1.0)
        self.assertEqual(curr, "USD")

        # 0.05 ltc
        val, curr = parse_payment_amount("0.05 ltc")
        self.assertEqual(val, 0.05)
        self.assertEqual(curr, "LTC")

        # 0.05
        val, curr = parse_payment_amount("0.05")
        self.assertEqual(val, 0.05)
        self.assertEqual(curr, "LTC")

        # 2.50$ ltc
        val, curr = parse_payment_amount("2.50$ ltc")
        self.assertEqual(val, 2.50)
        self.assertEqual(curr, "USD")

    def test_sats_conversion_at_rate(self):
        ltc_price = 100.0 # $100 per LTC
        sats, ltc, usd = convert_amount_to_sats(1.0, "USD", ltc_price)
        self.assertEqual(sats, 1_000_000) # $1 / $100 = 0.01 LTC = 1,000,000 sats
        self.assertAlmostEqual(ltc, 0.01)
        self.assertAlmostEqual(usd, 1.0)

        sats, ltc, usd = convert_amount_to_sats(0.05, "LTC", ltc_price)
        self.assertEqual(sats, 5_000_000)
        self.assertAlmostEqual(ltc, 0.05)
        self.assertAlmostEqual(usd, 5.0)

    def test_scriptpubkey_converters(self):
        key = LitecoinKey.generate()
        p2pkh_script = address_to_scriptpubkey(key.p2pkh_address)
        self.assertTrue(p2pkh_script.startswith(b"\x76\xa9\x14"))

        segwit_script = address_to_scriptpubkey(key.bech32_address)
        self.assertTrue(segwit_script.startswith(b"\x00\x14"))

        p2sh_script = address_to_scriptpubkey(key.p2sh_address)
        self.assertTrue(p2sh_script.startswith(b"\xa9\x14"))

    def test_tx_signing_both_p2pkh_and_segwit(self):
        key = LitecoinKey.generate()
        utxos = [{
            "txid": "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            "vout": 0,
            "value": 20_000_000,
            "confirmed": True
        }]
        res_p2pkh = build_and_sign_p2pkh_tx(key, utxos, key.p2pkh_address, 1_000_000)
        self.assertEqual(len(res_p2pkh["txid"]), 64)
        self.assertEqual(res_p2pkh["amount_sats"], 1_000_000)

        res_segwit = build_and_sign_segwit_tx(key, utxos, key.bech32_address, 1_000_000)
        self.assertEqual(len(res_segwit["txid"]), 64)
        self.assertEqual(res_segwit["amount_sats"], 1_000_000)

    def test_database_wallet_operations(self):
        async def _run():
            await db.init()
            test_uid = 888777666
            key = LitecoinKey.generate()

            info = await db.set_user_wallet_account(test_uid, key.wif)
            self.assertEqual(info["bech32"], key.bech32_address)

            acc = await db.get_user_wallet_account(test_uid)
            self.assertTrue(acc["has_key"])

            signing_key = await db.get_user_signing_key(test_uid)
            self.assertEqual(signing_key.wif, key.wif)

            bal = await db.update_user_deposit_balance(test_uid, 0.25)
            self.assertTrue(bal >= 0.25)

            peer_uid = 888777667
            xfer = await db.transfer_internal_balance(test_uid, peer_uid, 0.10)
            self.assertTrue(xfer)

            peer_bal = await db.get_user_deposit_balance(peer_uid)
            self.assertTrue(peer_bal >= 0.10)

            await db.remove_user_wallet_key(test_uid)
            acc2 = await db.get_user_wallet_account(test_uid)
            self.assertFalse(acc2["has_key"])

        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
