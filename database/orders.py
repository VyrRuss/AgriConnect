"""SQLite order storage used when MongoDB is unavailable."""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager


@contextmanager
def _connection(database_path):
    directory = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL,
                fulfillment_status TEXT NOT NULL DEFAULT 'confirmed',
                delivery_address_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "fulfillment_status" not in columns:
            connection.execute(
                "ALTER TABLE orders ADD COLUMN fulfillment_status TEXT NOT NULL DEFAULT 'confirmed'"
            )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_order(database_path, order):
    order_id = f"local-{uuid.uuid4().hex}"
    with _connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO orders (
                order_id, user_id, items_json, total, payment_method, status,
                fulfillment_status,
                delivery_address_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                str(order["user_id"]),
                json.dumps(order["items"]),
                order["total"],
                order["payment_method"],
                order["status"],
                order.get("fulfillment_status", "confirmed"),
                json.dumps(order.get("delivery_address", {})),
                order["created_at"].isoformat(),
            ),
        )
    return {"_id": order_id}


def find_order(database_path, order_id, user_id):
    if not order_id.startswith("local-"):
        return None
    if not os.path.exists(database_path):
        return None
    with _connection(database_path) as connection:
        try:
            row = connection.execute(
                """
                SELECT order_id, user_id, items_json, total, payment_method, status,
                       fulfillment_status, delivery_address_json, created_at
                FROM orders
                WHERE order_id = ? AND user_id = ?
                """,
                (order_id, str(user_id)),
            ).fetchone()
        except sqlite3.OperationalError as error:
            if "no such table: orders" in str(error).lower():
                return None
            raise
    if row is None:
        return None
    return {
        "_id": row["order_id"],
        "user_id": row["user_id"],
        "items": json.loads(row["items_json"]),
        "total": row["total"],
        "payment_method": row["payment_method"],
        "status": row["status"],
        "fulfillment_status": row["fulfillment_status"],
        "delivery_address": json.loads(row["delivery_address_json"]),
        "created_at": row["created_at"],
    }


def list_orders(database_path, user_id, limit=100):
    if not os.path.exists(database_path):
        return []
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT order_id, user_id, items_json, total, payment_method, status,
                   fulfillment_status, delivery_address_json, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (str(user_id), limit),
        ).fetchall()
    return [
        {
            "_id": row["order_id"],
            "user_id": row["user_id"],
            "items": json.loads(row["items_json"]),
            "total": row["total"],
            "payment_method": row["payment_method"],
            "status": row["status"],
            "fulfillment_status": row["fulfillment_status"],
            "delivery_address": json.loads(row["delivery_address_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
