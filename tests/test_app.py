import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId

import app as application


class FakeCursor:
    def __init__(self, records):
        self.records = records

    def sort(self, *_args):
        return self

    def limit(self, count):
        self.records = self.records[:count]
        return self

    def __iter__(self):
        return iter(self.records)


class FakeCollection:
    def __init__(self):
        self.records = []

    def create_index(self, *_args, **_kwargs):
        return None

    def find(self, query=None):
        query = query or {}
        records = [
            record for record in self.records
            if all(record.get(key) == value for key, value in query.items())
        ]
        return FakeCursor(records)

    def find_one(self, query):
        return next(
            (
                record for record in self.records
                if all(record.get(key) == value for key, value in query.items())
            ),
            None,
        )

    def insert_one(self, record):
        saved = dict(record)
        saved["_id"] = ObjectId()
        self.records.append(saved)
        return type("InsertResult", (), {"inserted_id": saved["_id"]})()


class FakeDatabase:
    def __init__(self):
        self.users = FakeCollection()
        self.orders = FakeCollection()
        self.products = FakeCollection()
        self.crop_listings = FakeCollection()


class AgriConnectRoutesTest(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        application.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-key",
            WTF_CSRF_ENABLED=False,
        )
        self.account_storage = tempfile.TemporaryDirectory()
        application.app.config["ACCOUNT_DB_PATH"] = os.path.join(self.account_storage.name, "accounts.sqlite3")
        self.database_patch = patch.object(application, "get_database", return_value=self.database)
        self.database_patch.start()
        self.client = application.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.account_storage.cleanup()

    def create_account(self):
        return self.client.post(
            "/register",
            data={
                "name": "Test Farmer",
                "email": "farmer@example.com",
                "password": "secure-password",
                "role": "farmer",
            },
        )

    def delivery_address(self):
        return {
            "delivery_name": "Test Farmer",
            "delivery_phone": "+919876543210",
            "delivery_address": "12 Farm Road",
            "delivery_city": "Dharwad",
            "delivery_state": "Karnataka",
            "delivery_postal_code": "580001",
        }

    def test_home_shows_simulated_quotes_products_and_language_selector(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Simulated market quotes", response.data)
        self.assertIn(b"Hybrid Tomato Seeds", response.data)
        self.assertIn(b'id="cropCategoryFilter"', response.data)
        for category in (b"Cereals", b"Fruits", b"Oilseeds", b"Pulses"):
            self.assertIn(category, response.data)
        self.assertIn(b'data-crop-category="fruits"', response.data)
        self.assertIn(b'src="/static/images/mango.svg"', response.data)
        self.assertIn(b"Soybeans", response.data)
        self.assertIn(b"Chickpeas", response.data)
        self.assertIn(b"Hybrid Okra Seeds", response.data)
        self.assertIn(b"Mango Grafted Sapling", response.data)
        self.assertIn(b'src="/static/images/seeds.svg"', response.data)
        self.assertIn(b'id="supplyCategoryFilter"', response.data)
        self.assertIn(b"Seeds, electric kits, irrigation &amp; sowing", response.data)
        self.assertIn(b'value="fertilizers"', response.data)
        self.assertIn(b'value="agro-items"', response.data)
        self.assertEqual(response.data.count(b'data-supply-category="seeds-equipment"'), 6)
        self.assertEqual(response.data.count(b'data-supply-category="fertilizers"'), 4)
        self.assertEqual(response.data.count(b'data-supply-category="agro-items"'), 5)
        self.assertIn(b"Electric Water Pump Kit", response.data)
        self.assertIn(b"Hand Seed Sower", response.data)
        self.assertIn(b"Balanced NPK Fertilizer", response.data)
        self.assertIn(b"Farm Soil Testing Kit", response.data)
        self.assertIn(b"languageSelect", response.data)
        self.assertNotIn(b"Create a farmer account", response.data)
        self.assertIn(b"Ask anything", response.data)

    def test_existing_sample_catalog_records_keep_images_and_gain_new_items(self):
        self.database.products.records = [{
            "name": "Hybrid Tomato Seeds",
            "category": "Seeds",
            "price": 180,
            "status": "active",
        }]
        self.database.crop_listings.records = [{
            "crop_name": "Fresh mangoes",
            "price": 65,
            "status": "active",
        }]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'src="/static/images/mango.svg"', response.data)
        self.assertIn(b'data-crop-category="fruits"', response.data)
        self.assertIn(b"Groundnuts", response.data)
        self.assertIn(b"Organic Vermicompost", response.data)
    def test_farmer_home_shows_assistant_safety_and_chat(self):
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = "farmer-id"
            browser_session["user_name"] = "Test Farmer"
            browser_session["user_role"] = "farmer"
        with patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="farmerAssistant"', response.data)
        self.assertIn(b"confirm chemical use", response.data)

    def test_customer_home_does_not_show_assistant_chat(self):
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = "customer-id"
            browser_session["user_name"] = "Test Customer"
            browser_session["user_role"] = "customer"
        with patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'id="farmerAssistant"', response.data)
        self.assertIn(b"Sign in with a farmer account", response.data)
        self.assertNotIn(b"Create a farmer account", response.data)

    def test_registration_shows_account_created_confirmation(self):
        response = self.create_account()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account-created")
        confirmation = self.client.get(response.headers["Location"])
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Account created successfully!", confirmation.data)
        self.assertIn(b"Open Farmer Assist", confirmation.data)

    def test_registration_cart_and_cash_on_delivery_order(self):
        response = self.create_account()
        self.assertEqual(response.status_code, 302)
        self.client.post("/cart/add/hybrid-tomato-seeds")
        checkout = self.client.get("/checkout")
        self.assertEqual(checkout.status_code, 200)
        self.assertIn(b'id="deliveryFields"', checkout.data)
        self.assertIn(b'name="delivery_postal_code"', checkout.data)
        self.assertIn(b"checkout.js", checkout.data)
        placed = self.client.post(
            "/checkout",
            data={"payment_method": "cod", **self.delivery_address()},
        )
        self.assertEqual(placed.status_code, 302)
        confirmation = self.client.get(placed.headers["Location"])
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Your order is confirmed!", confirmation.data)
        self.assertIn(b"order-success-animation", confirmation.data)
        self.assertIn(b"aria-live=\"polite\"", confirmation.data)
        self.assertEqual(self.database.orders.records[0]["payment_method"], "cash_on_delivery")
        self.assertEqual(self.database.orders.records[0]["delivery_address"]["postal_code"], "580001")
        self.assertIn(b"Delivering to", confirmation.data)
        self.assertIn(b"12 Farm Road", confirmation.data)
        self.assertIn(b"Order tracking", confirmation.data)
        self.assertIn(b"Order confirmed", confirmation.data)
        self.assertIn(b"Live GPS location is not available", confirmation.data)
        self.assertIn(b"Track this order", confirmation.data)
        self.assertIn("📦 My Orders".encode(), confirmation.data)

    def test_my_orders_lists_only_the_signed_in_users_orders(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        placed = self.client.post(
            "/checkout",
            data={"payment_method": "cod", **self.delivery_address()},
        )
        response = self.client.get("/orders")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hybrid Tomato Seeds", response.data)
        self.assertIn(b"Track order", response.data)
        self.assertIn(b"Order confirmed", response.data)
        self.assertIn(placed.headers["Location"].rsplit("/", 1)[-1].encode(), response.data)
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = "different-user"
        other_account_orders = self.client.get("/orders")
        self.assertEqual(other_account_orders.status_code, 200)
        self.assertIn(b"No orders yet", other_account_orders.data)
        self.assertNotIn(b"Hybrid Tomato Seeds", other_account_orders.data)

    def test_my_orders_migrates_existing_local_order_table(self):
        self.create_account()
        with self.client.session_transaction() as browser_session:
            user_id = browser_session["user_id"]
        database_path = application.app.config["ACCOUNT_DB_PATH"]
        with closing(sqlite3.connect(database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE orders (
                        order_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        items_json TEXT NOT NULL,
                        total INTEGER NOT NULL,
                        payment_method TEXT NOT NULL,
                        status TEXT NOT NULL,
                        delivery_address_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO orders (
                        order_id, user_id, items_json, total, payment_method,
                        status, delivery_address_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "local-legacy",
                        user_id,
                        json.dumps([{"name": "Legacy seeds", "quantity": 1, "subtotal": 10}]),
                        10,
                        "cash_on_delivery",
                        "pending",
                        "{}",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

        response = self.client.get("/orders")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Legacy seeds", response.data)
        self.assertIn(b"Confirmed", response.data)

    def test_order_tracking_page_reflects_latest_fulfillment_status(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        placed = self.client.post(
            "/checkout",
            data={"payment_method": "cod", **self.delivery_address()},
        )
        self.database.orders.records[0]["fulfillment_status"] = "shipped"

        tracking = self.client.get(f"{placed.headers['Location']}/track")

        self.assertEqual(tracking.status_code, 200)
        self.assertIn(b"Shipped", tracking.data)
        self.assertIn(b"Preparing your order", tracking.data)
        self.assertIn(b"Live GPS location is not available", tracking.data)

    def test_order_sms_uses_twilio_and_does_not_block_order_confirmation(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        sms_response = unittest.mock.Mock()
        sms_response.raise_for_status.return_value = None
        with (
            patch.dict(
                "os.environ",
                {
                    "TWILIO_ACCOUNT_SID": "AC-test",
                    "TWILIO_AUTH_TOKEN": "token-test",
                    "TWILIO_FROM_NUMBER": "+15550001111",
                    "PUBLIC_BASE_URL": "https://agriconnect.example",
                },
            ),
            patch.object(application.requests, "post", return_value=sms_response) as sms_post,
        ):
            placed = self.client.post(
                "/checkout",
                data={"payment_method": "cod", **self.delivery_address()},
            )

        self.assertEqual(placed.status_code, 302)
        self.assertIn("/orders/", placed.headers["Location"])
        self.assertEqual(
            sms_post.call_args.args[0],
            "https://api.twilio.com/2010-04-01/Accounts/AC-test/Messages.json",
        )
        self.assertEqual(sms_post.call_args.kwargs["auth"], ("AC-test", "token-test"))
        self.assertEqual(sms_post.call_args.kwargs["data"]["To"], "+919876543210")
        self.assertIn("Order", sms_post.call_args.kwargs["data"]["Body"])
        self.assertIn(
            "https://agriconnect.example/orders/",
            sms_post.call_args.kwargs["data"]["Body"],
        )
        self.assertIn("/track", sms_post.call_args.kwargs["data"]["Body"])

    def test_twilio_sms_failure_does_not_undo_saved_order(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        sms_response = unittest.mock.Mock()
        http_error = application.requests.HTTPError(response=SimpleNamespace(status_code=503))
        sms_response.raise_for_status.side_effect = http_error
        with (
            patch.dict(
                "os.environ",
                {
                    "TWILIO_ACCOUNT_SID": "AC-test",
                    "TWILIO_AUTH_TOKEN": "token-test",
                    "TWILIO_FROM_NUMBER": "+15550001111",
                },
            ),
            patch.object(application.requests, "post", return_value=sms_response),
        ):
            placed = self.client.post(
                "/checkout",
                data={"payment_method": "cod", **self.delivery_address()},
            )
            confirmation = self.client.get(placed.headers["Location"])

        self.assertEqual(placed.status_code, 302)
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Your order is confirmed!", confirmation.data)
        self.assertIn(b"Twilio could not send the SMS", confirmation.data)

    def test_cash_on_delivery_order_works_when_mongodb_is_unavailable(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        with patch.object(application, "get_database", return_value=None):
            placed = self.client.post(
                "/checkout",
                data={"payment_method": "cod", **self.delivery_address()},
            )
            self.assertEqual(placed.status_code, 302)
            self.assertIn("/orders/local-", placed.headers["Location"])
            confirmation = self.client.get(placed.headers["Location"])

        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Your order is confirmed!", confirmation.data)
        self.assertIn(b"order-success-animation", confirmation.data)
        self.assertIn(b"no SMS was sent", confirmation.data)
        self.assertIn(b"TWILIO_ACCOUNT_SID", confirmation.data)
        self.assertIn(b"12 Farm Road", confirmation.data)
        self.assertIn(b"Hybrid Tomato Seeds", confirmation.data)
        self.assertIn(b"Cash on delivery", confirmation.data)
        self.assertIn(b"Order tracking", confirmation.data)
        local_orders = self.client.get("/orders")
        self.assertEqual(local_orders.status_code, 200)
        self.assertIn(b"Hybrid Tomato Seeds", local_orders.data)
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("cart", browser_session)
            browser_session["user_id"] = "another-user"
        unauthorized = self.client.get(placed.headers["Location"])
        self.assertEqual(unauthorized.status_code, 302)
        self.assertEqual(unauthorized.headers["Location"], "/")

    def test_cash_on_delivery_order_falls_back_when_mongodb_write_fails(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        with (
            patch.object(self.database.orders, "insert_one", side_effect=application.PyMongoError("database unavailable")),
            patch.object(application, "get_database", return_value=self.database),
        ):
            placed = self.client.post(
                "/checkout",
                data={"payment_method": "cod", **self.delivery_address()},
            )
            self.assertEqual(placed.status_code, 302)
            self.assertIn("/orders/local-", placed.headers["Location"])
            confirmation = self.client.get(placed.headers["Location"])

        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Your order is confirmed!", confirmation.data)
        self.assertIn(b"12 Farm Road", confirmation.data)

    def test_failed_local_order_save_keeps_cart_and_does_not_confirm(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        with (
            patch.object(application, "get_database", return_value=None),
            patch.object(application, "create_local_order", side_effect=sqlite3.OperationalError("disk unavailable")),
        ):
            placed = self.client.post(
                "/checkout",
                data={"payment_method": "cod", **self.delivery_address()},
            )
            self.assertEqual(placed.status_code, 302)
            self.assertEqual(placed.headers["Location"], "/checkout")
            checkout = self.client.get(placed.headers["Location"])

        self.assertEqual(checkout.status_code, 200)
        self.assertNotIn(b"Your order is confirmed!", checkout.data)
        with self.client.session_transaction() as browser_session:
            self.assertIn("hybrid-tomato-seeds", browser_session["cart"])

    def test_checkout_rejects_missing_delivery_address(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        response = self.client.post("/checkout", data={"payment_method": "cod"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Enter a valid delivery address", response.data)
        self.assertEqual(self.database.orders.records, [])

    def test_checkout_requires_valid_six_digit_postal_code(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        address = self.delivery_address()
        address["delivery_postal_code"] = "58001"
        response = self.client.post("/checkout", data={"payment_method": "cod", **address})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.database.orders.records, [])

    def test_checkout_requires_sign_in(self):
        self.client.post("/cart/add/hybrid-tomato-seeds")
        response = self.client.get("/checkout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_registered_user_can_sign_in(self):
        self.create_account()
        self.client.post("/logout")
        response = self.client.post(
            "/login",
            data={"email": "farmer@example.com", "password": "secure-password"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account-created?signed_in=1")
        self.assertIn(b"Signed in successfully", self.client.get(response.headers["Location"]).data)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_name"], "Test Farmer")

    def test_registration_and_sign_in_work_when_mongodb_is_unavailable(self):
        with patch.object(application, "get_database", return_value=None):
            created = self.client.post(
                "/register",
                data={
                    "name": "Local Farmer",
                    "email": "local@example.com",
                    "password": "secure-password",
                    "role": "farmer",
                },
            )
            self.assertEqual(created.status_code, 302)
            self.assertEqual(created.headers["Location"], "/account-created")
            self.assertIn(b"Account created successfully", self.client.get(created.headers["Location"]).data)
            self.client.post("/logout")

            second_client = application.app.test_client()
            signed_in = second_client.post(
                "/login",
                data={"email": "LOCAL@example.com", "password": "secure-password"},
            )
            self.assertEqual(signed_in.status_code, 302)
            self.assertEqual(signed_in.headers["Location"], "/account-created?signed_in=1")
            confirmation = second_client.get(signed_in.headers["Location"])

        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Signed in successfully!", confirmation.data)
        with second_client.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_role"], "farmer")

    def test_local_registration_rejects_duplicate_email_without_mongodb(self):
        with patch.object(application, "get_database", return_value=None):
            first = self.client.post(
                "/register",
                data={
                    "name": "Local Farmer",
                    "email": "local@example.com",
                    "password": "secure-password",
                    "role": "farmer",
                },
            )
            self.assertEqual(first.status_code, 302)
            self.client.post("/logout")
            duplicate = self.client.post(
                "/register",
                data={
                    "name": "Another Farmer",
                    "email": "LOCAL@example.com",
                    "password": "another-password",
                    "role": "farmer",
                },
            )
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn(b"An account with that email already exists.", duplicate.data)

    def test_csrf_blocks_post_without_token(self):
        application.app.config["WTF_CSRF_ENABLED"] = True
        try:
            response = self.client.post("/login", data={"email": "farmer@example.com", "password": "password"})
            self.assertEqual(response.status_code, 400)
        finally:
            application.app.config["WTF_CSRF_ENABLED"] = False

    def test_account_registration_rejects_duplicate_email(self):
        self.create_account()
        self.client.get("/logout")
        self.client.post("/logout")
        self.client.post(
            "/register",
            data={
                "name": "Another Farmer",
                "email": "farmer@example.com",
                "password": "secure-password",
                "role": "farmer",
            },
        )
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("user_id", browser_session)
        self.assertEqual(len(self.database.users.records), 1)

    def test_card_checkout_requires_stripe_configuration(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        with patch.object(application.stripe, "api_key", None):
            response = self.client.post(
                "/checkout",
                data={"payment_method": "card", **self.delivery_address()},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/checkout")

    def test_paid_stripe_checkout_creates_an_order(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        with self.client.session_transaction() as browser_session:
            user_id = browser_session["user_id"]
        paid_session = SimpleNamespace(
            payment_status="paid",
            metadata={
                "user_id": user_id,
                "delivery_name": "Test Farmer",
                "delivery_phone": "+919876543210",
                "delivery_address": "12 Farm Road",
                "delivery_city": "Dharwad",
                "delivery_state": "Karnataka",
                "delivery_postal_code": "580001",
            },
            amount_total=18000,
        )
        with (
            patch.object(application.stripe, "api_key", "sk_test_checkout"),
            patch.object(application.stripe.checkout.Session, "retrieve", return_value=paid_session),
        ):
            response = self.client.get("/checkout/success?session_id=cs_test_checkout")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.database.orders.records[0]["payment_method"], "card")
        confirmation = self.client.get(response.headers["Location"])
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Paid online", confirmation.data)
        self.assertIn(b"12 Farm Road", confirmation.data)
        self.assertEqual(self.database.orders.records[0]["delivery_address"]["postal_code"], "580001")

    def test_card_checkout_passes_delivery_details_to_stripe_metadata(self):
        self.create_account()
        self.client.post("/cart/add/hybrid-tomato-seeds")
        checkout_session = SimpleNamespace(url="https://checkout.stripe.test/session")
        with (
            patch.object(application.stripe, "api_key", "sk_test_checkout"),
            patch.object(application.stripe.checkout.Session, "create", return_value=checkout_session) as create_session,
        ):
            response = self.client.post(
                "/checkout",
                data={"payment_method": "card", **self.delivery_address()},
            )
        self.assertEqual(response.status_code, 303)
        metadata = create_session.call_args.kwargs["metadata"]
        self.assertEqual(metadata["delivery_name"], "Test Farmer")
        self.assertEqual(metadata["delivery_postal_code"], "580001")

    def test_customer_cannot_use_farmer_assistant(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Test Customer",
                "email": "customer@example.com",
                "password": "secure-password",
                "role": "customer",
            },
        )
        self.assertEqual(response.status_code, 302)
        denied = self.client.post("/api/farmer-assistant", json={"message": "How do I grow tomatoes?"})
        self.assertEqual(denied.status_code, 403)

    def test_farmer_assistant_requires_nvidia_configuration(self):
        self.create_account()
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.post("/api/farmer-assistant", json={"message": "How are my tomato leaves?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("NVIDIA_KEY", response.json["error"])

    def test_farmer_assistant_calls_nvidia_and_returns_answer(self):
        self.create_account()
        nvidia_response = unittest.mock.Mock()
        nvidia_response.status_code = 200
        nvidia_response.ok = True
        nvidia_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Check watering and share a leaf photo with an extension officer."}}]
        }
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key", "NVIDIA_MODEL": "meta/test-model"}),
            patch.object(application.requests, "post", return_value=nvidia_response) as nvidia_post,
        ):
            response = self.client.post(
                "/api/farmer-assistant",
                json={
                    "message": "My leaves are curling.",
                    "language": "en",
                    "history": [{"role": "user", "text": "I grow tomatoes."}],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Check watering", response.json["answer"])
        args, kwargs = nvidia_post.call_args
        self.assertEqual(args[0], "https://integrate.api.nvidia.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "meta/test-model")
        self.assertEqual(kwargs["json"]["messages"][-1], {"role": "user", "content": "My leaves are curling."})
        self.assertEqual(kwargs["json"]["messages"][1], {"role": "user", "content": "I grow tomatoes."})
        self.assertIn("English", kwargs["json"]["messages"][0]["content"])
        self.assertIn("general-purpose AI assistant", kwargs["json"]["messages"][0]["content"])
        self.assertIn("everyday knowledge", kwargs["json"]["messages"][0]["content"])

    def test_farmer_assistant_accepts_nvidia_api_key_name_and_model_history(self):
        self.create_account()
        nvidia_response = unittest.mock.Mock(status_code=200, ok=True)
        nvidia_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Here is an answer."}}]
        }
        with (
            patch.dict("os.environ", {"NVIDIA_API_KEY": "api-key-test"}, clear=True),
            patch.object(application.requests, "post", return_value=nvidia_response) as nvidia_post,
        ):
            response = self.client.post(
                "/api/farmer-assistant",
                json={
                    "message": "Continue.",
                    "history": [{"role": "model", "text": "Earlier answer."}],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(nvidia_post.call_args.kwargs["headers"]["Authorization"], "Bearer api-key-test")
        self.assertEqual(nvidia_post.call_args.kwargs["json"]["messages"][1], {
            "role": "assistant",
            "content": "Earlier answer.",
        })
        self.assertEqual(
            nvidia_post.call_args.kwargs["json"]["model"],
            "deepseek-ai/deepseek-v4-flash",
        )

    def test_farmer_assistant_continues_after_long_answer(self):
        self.create_account()
        answers = [("Helpful detailed answer. " * 120).strip() for _ in range(6)]
        provider_responses = []
        for answer in answers:
            provider_response = unittest.mock.Mock(status_code=200, ok=True)
            provider_response.json.return_value = {
                "choices": [{"message": {"role": "assistant", "content": answer}}]
            }
            provider_responses.append(provider_response)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}),
            patch.object(application.requests, "post", side_effect=provider_responses) as nvidia_post,
        ):
            history = []
            for turn_number, answer in enumerate(answers):
                question = f"Question {turn_number + 1}"
                response = self.client.post(
                    "/api/farmer-assistant",
                    json={"message": question, "history": history[-8:]},
                )
                self.assertEqual(response.status_code, 200, response.json)
                self.assertEqual(response.json["answer"], answer)
                history.extend([
                    {"role": "user", "text": question},
                    {"role": "model", "text": response.json["answer"]},
                ])

        self.assertEqual(nvidia_post.call_count, 6)
        last_messages = nvidia_post.call_args.kwargs["json"]["messages"]
        self.assertEqual(last_messages[-1]["content"], "Question 6")
        self.assertEqual(last_messages[-2]["content"], answers[-2])

    def test_farmer_assistant_retries_with_fallback_after_nvidia_410(self):
        self.create_account()
        retired_model_response = unittest.mock.Mock(status_code=410, ok=False)
        fallback_response = unittest.mock.Mock(status_code=200, ok=True)
        fallback_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Here is an answer."}}]
        }
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}, clear=True),
            patch.object(
                application.requests,
                "post",
                side_effect=[retired_model_response, fallback_response],
            ) as nvidia_post,
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "Here is an answer.")
        self.assertEqual(
            [call.kwargs["json"]["model"] for call in nvidia_post.call_args_list],
            ["deepseek-ai/deepseek-v4-flash", "meta/llama-3.3-70b-instruct"],
        )

    def test_farmer_assistant_explains_nvidia_410_model_retirement(self):
        self.create_account()
        gone_response = unittest.mock.Mock(status_code=410, ok=False)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key", "NVIDIA_MODEL": "meta/old-model"}),
            patch.object(application.requests, "post", return_value=gone_response),
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("HTTP 410 Gone", response.json["error"])
        self.assertIn("meta/old-model", response.json["error"])
        self.assertIn("meta/llama-3.3-70b-instruct", response.json["error"])

    def test_farmer_assistant_rejects_oversized_question(self):
        self.create_account()
        with patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}):
            response = self.client.post("/api/farmer-assistant", json={"message": "x" * 2001})
        self.assertEqual(response.status_code, 400)

    def test_farmer_assistant_uses_selected_language(self):
        self.create_account()
        nvidia_response = unittest.mock.Mock()
        nvidia_response.status_code = 200
        nvidia_response.ok = True
        nvidia_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "गेहूँ की फसल की अवस्था बताएँ।"}}]
        }
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}),
            patch.object(application.requests, "post", return_value=nvidia_response) as nvidia_post,
        ):
            response = self.client.post(
                "/api/farmer-assistant",
                json={"message": "मेरी फसल पीली हो रही है।", "language": "hi"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("गेहूँ", response.json["answer"])
        system_instruction = nvidia_post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("in Hindi", system_instruction)

    def test_farmer_assistant_reports_unavailable_nvidia_model(self):
        self.create_account()
        missing_model = unittest.mock.Mock(status_code=404, ok=False)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key", "NVIDIA_MODEL": "retired-model"}),
            patch.object(application.requests, "post", return_value=missing_model) as nvidia_post,
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "Explain photosynthesis simply."})
        self.assertEqual(response.status_code, 503)
        self.assertIn("NVIDIA_MODEL", response.json["error"])
        self.assertEqual(nvidia_post.call_count, 1)

    def test_farmer_assistant_explains_rejected_nvidia_model_configuration(self):
        self.create_account()
        rejected_response = unittest.mock.Mock(status_code=422, ok=False)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key", "NVIDIA_MODEL": "meta/unavailable-model"}),
            patch.object(application.requests, "post", return_value=rejected_response),
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("NVIDIA_MODEL", response.json["error"])
        self.assertIn("meta/unavailable-model", response.json["error"])

    def test_farmer_assistant_reports_nvidia_api_key_access_error(self):
        self.create_account()
        denied_response = unittest.mock.Mock(status_code=403, ok=False)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}),
            patch.object(application.requests, "post", return_value=denied_response),
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("API key or account access", response.json["error"])

    def test_farmer_assistant_reports_quota_error(self):
        self.create_account()
        limited_response = unittest.mock.Mock(status_code=429, ok=False)
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}),
            patch.object(application.requests, "post", return_value=limited_response),
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("quota limit", response.json["error"])

    def test_farmer_assistant_handles_malformed_provider_response(self):
        self.create_account()
        malformed_response = unittest.mock.Mock(status_code=200, ok=True)
        malformed_response.json.return_value = []
        with (
            patch.dict("os.environ", {"NVIDIA_KEY": "test-key"}),
            patch.object(application.requests, "post", return_value=malformed_response),
        ):
            response = self.client.post("/api/farmer-assistant", json={"message": "What is photosynthesis?"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("could not produce an answer", response.json["error"])

    def test_registration_requires_an_account_role(self):
        response = self.client.post(
            "/register",
            data={"name": "No Role", "email": "norole@example.com", "password": "secure-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.database.users.records), 0)


if __name__ == "__main__":
    unittest.main()
