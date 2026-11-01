import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(line_buffering=True)
import asyncio
from utils.database import db
import utils.ltc as ltc

async def run_tests():
    print("Initializing DB...")
    await db.init()
    print("1. DB initialized successfully")

    # Test LTC address validation
    assert ltc.is_valid_ltc_address("ltc1qg66j4j37v7vgshnly0v44e053k8h05828v94q3")
    assert ltc.is_valid_ltc_address("LdP8Qox1VAic7rABvi8CXpWwN97A5eE1zZ")
    assert ltc.is_valid_ltc_address("MNfD37y9u1v23jR5YfXF3j7n1F6d1Y7z8u")
    assert not ltc.is_valid_ltc_address("invalid_ltc_address")
    print("2. LTC address validation passed")

    # Test LTC price retrieval
    price = await ltc.get_ltc_price()
    assert price > 0
    print(f"3. Live LTC price fetched: ${price:,.2f}")

    # Test Shop Config
    test_gid = 999123
    await db.set_shop_config(test_gid, shop_name="Jack's Shop")
    cfg = await db.get_shop_config(test_gid)
    assert cfg["shop_name"] == "Jack's Shop"
    await db.set_shop_config(test_gid, shop_name="Jack's Premium Shop", ltc_address="ltc1qg66j4j37v7vgshnly0v44e053k8h05828v94q3")
    cfg2 = await db.get_shop_config(test_gid)
    assert cfg2["shop_name"] == "Jack's Premium Shop"
    print("4. Shop config CRUD passed")

    # Test User LTC link/unlink
    await db.link_user_ltc(999, "ltc1qg66j4j37v7vgshnly0v44e053k8h05828v94q3")
    user_ltc = await db.get_user_ltc(999)
    assert user_ltc == "ltc1qg66j4j37v7vgshnly0v44e053k8h05828v94q3"
    await db.unlink_user_ltc(999)
    assert await db.get_user_ltc(999) is None
    print("5. User LTC wallet link/unlink passed")

    # Test Shop Orders and Lifetime Spend
    order = await db.create_shop_order(
        guild_id=123456,
        user_id=888,
        product_name="Custom website",
        quantity=1,
        total_usd=7.50,
        total_ltc=0.08,
        payment_method="Litecoin",
        ltc_address="ltc1qg66j4j37v7vgshnly0v44e053k8h05828v94q3"
    )
    assert order["status"] == "pending_payment"
    assert order["total_usd"] == 7.50

    # Claim and Complete Order
    await db.claim_order(order["order_id"], 777)
    completed = await db.complete_order(order["order_id"], staff_id=777, txid="a"*64)
    assert completed["status"] == "completed"

    # Lifetime spend
    spend = await db.get_customer_lifetime_spend(123456, 888)
    assert spend >= 7.50
    print(f"6. Shop orders and lifetime spend calculation passed (${spend:.2f})")

    # Test Used TXID prevention
    import os
    random_tx = os.urandom(32).hex()
    recorded = await db.record_used_txid(random_tx, order["order_id"], 123456, 0.08, 1)
    assert recorded is True
    duplicate = await db.record_used_txid(random_tx, "ORD-999999", 123456, 0.08, 1)
    assert duplicate is False
    print("7. Duplicate transaction reuse prevention passed")

    # Test Legit Vouch Toggle
    added, count = await db.toggle_legit_vouch(123456, 555)
    assert added is True
    assert count >= 1
    removed, count2 = await db.toggle_legit_vouch(123456, 555)
    assert removed is False
    print("8. Legit vouch toggle passed")

    # Test Customer Feedback
    fid = await db.add_customer_feedback(123456, order["order_id"], 888, 5, "Exceptional service and quick delivery!")
    assert fid > 0
    feedback_list = await db.get_customer_feedback(123456, order_id=order["order_id"])
    assert len(feedback_list) == 1
    assert feedback_list[0]["stars"] == 5
    print("9. Customer feedback 5-star rating passed")

    # Test Coupons
    coupon_code = f"SAVE_{os.urandom(3).hex().upper()}"
    cid = await db.create_coupon(123456, coupon_code, 20.0, max_uses=5)
    assert cid > 0
    coupon = await db.get_coupon(123456, coupon_code)
    assert coupon["discount_percent"] == 20.0
    used = await db.use_coupon(123456, coupon_code)
    assert used is True
    print("10. Store discount coupons passed")

    # Test Digital Stock Dispense
    test_prod = f"Nitro_{os.urandom(3).hex()}"
    await db.add_stock_batch(123456, test_prod, ["code_123", "code_456"])
    dispensed = await db.dispense_stock(123456, test_prod, 1)
    assert len(dispensed) == 1
    assert dispensed[0] == "code_123"
    remaining = await db.get_item_stock_count(123456, test_prod)
    assert remaining == 1
    print("11. Digital stock atomic deduction and delivery passed")

    # Test Customer Profile
    profile = await db.get_customer_profile(123456, 888)
    assert profile["completed_orders"] >= 1
    assert profile["lifetime_spend"] >= 7.50
    print("12. Customer CRM profile passed")

    if db.is_postgres and db.pool:
        await db.pool.close()

    print("\n=======================================================")
    print(" ALL 12 SHOP UPGRADE UNIT TESTS PASSED WITH 100% SUCCESS! ")
    print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
