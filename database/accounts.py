"""Persistent local account storage used when MongoDB is unavailable."""

import os
import sqlite3
from contextlib import contextmanager


class DuplicateLocalAccountError(Exception):
    """Raised when a local account already uses the email address."""


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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def find_user(database_path, email):
    with _connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, name, email, role, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def create_user(database_path, user):
    try:
        with _connection(database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (name, email, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user["name"],
                    user["email"],
                    user["role"],
                    user["password_hash"],
                    user["created_at"].isoformat(),
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        if "users.email" in str(error).lower():
            raise DuplicateLocalAccountError from error
        raise
    return {
        "id": user_id,
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "password_hash": user["password_hash"],
    }
