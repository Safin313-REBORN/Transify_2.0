#!/usr/bin/env python3
"""
Zero-Downtime SQLite Online Restore/Rollback Utility for Transify 2.0.
Restores a verified point-in-time snapshot safely into the target database.
"""

import os
import sys
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("transify.restore")


def perform_online_restore(backup_file: str, target_db: str = None) -> bool:
    """
    Restores the database from a backup snapshot using the SQLite backup API.
    Performs integrity checks on both the source backup and the restored database.
    """
    backup_path = os.path.abspath(backup_file)
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found at: {backup_path}")

    # Verify backup integrity first
    src_conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    try:
        cur = src_conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        check = cur.fetchone()
        if not check or check[0] != "ok":
            raise RuntimeError(f"Source backup file failed integrity check: {check}")
    finally:
        src_conn.close()

    if not target_db:
        try:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from src.database.db import get_db_path
            target_db = get_db_path()
        except Exception:
            target_db = os.environ.get("TRANSIFY_DB_PATH", os.path.join(os.path.dirname(__file__), "../data/transify.db"))

    target_path = os.path.abspath(target_db)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    logger.info(f"Restoring database from '{backup_path}' to '{target_path}'...")

    src_conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(target_path)

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)

        cur = dst_conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        restored_check = cur.fetchone()
        if restored_check and restored_check[0] == "ok":
            logger.info(f"Database restored and integrity verified successfully: {target_path}")
            return True
        else:
            raise RuntimeError(f"Restored database integrity check failed: {restored_check}")
    finally:
        dst_conn.close()
        src_conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_db.py <path_to_backup_file> [target_db_path]")
        sys.exit(1)
    backup_f = sys.argv[1]
    target_f = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        perform_online_restore(backup_f, target_f)
        print("SUCCESS: Database restored.")
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        sys.exit(1)
