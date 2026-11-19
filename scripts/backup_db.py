#!/usr/bin/env python3
"""
Zero-Downtime SQLite Online Backup Utility for Transify 2.0.
Performs an atomic, non-blocking online snapshot using SQLite's backup API.
Safe to run in production under concurrent writes.
"""

import os
import sys
import sqlite3
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("transify.backup")


def perform_online_backup(source_db: str = None, backup_dir: str = None) -> str:
    """
    Creates an atomic point-in-time snapshot of the SQLite database.
    Does not hold an exclusive lock; safe for production WAL mode.
    """
    if not source_db:
        try:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from src.database.db import get_db_path
            source_db = get_db_path()
        except Exception:
            source_db = os.environ.get("TRANSIFY_DB_PATH", os.path.join(os.path.dirname(__file__), "../src/database/transify.db"))
    if not backup_dir:
        backup_dir = os.environ.get("TRANSIFY_BACKUP_DIR", "backups")

    source_path = os.path.abspath(source_db)
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source database not found at: {source_path}")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_filename = f"transify_backup_{timestamp}.db"
    target_path = os.path.abspath(os.path.join(backup_dir, target_filename))

    logger.info(f"Initiating online backup from '{source_path}' to '{target_path}'...")

    # Connect to source in read-only mode to prevent write locks during initialization
    src_conn = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(target_path)

    try:
        with dst_conn:
            # Transfer pages incrementally (100 pages per batch)
            src_conn.backup(dst_conn, pages=100)
        
        # Verify backup integrity
        cursor = dst_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        check_result = cursor.fetchone()
        if check_result and check_result[0] == "ok":
            file_size_kb = os.path.getsize(target_path) / 1024
            logger.info(f"Backup completed and verified successfully ({file_size_kb:.1f} KB): {target_path}")
            return target_path
        else:
            raise RuntimeError(f"Backup integrity check failed: {check_result}")
    finally:
        dst_conn.close()
        src_conn.close()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        result = perform_online_backup(src, out)
        print(f"SUCCESS: {result}")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)
