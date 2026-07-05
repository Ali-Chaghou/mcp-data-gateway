"""Load the Titanic demo dataset into PostgreSQL.

Idempotent: safe to run repeatedly. Creates the schema, loads the data, and
creates the SELECT-only role the gateway connects as.

Usage:
    python scripts/load_titanic.py
"""

# TODO(M2): implement:
#   1. connect with the admin credentials from DATABASE_URL
#   2. CREATE TABLE IF NOT EXISTS passengers (...canonical Titanic columns...)
#   3. load the CSV (vendored under data/ or downloaded from a pinned URL with a
#      checksum) via COPY
#   4. CREATE ROLE gateway_reader with LOGIN + SELECT-only grants on passengers
#   5. print a summary (row count, role name)


def main() -> None:
    raise NotImplementedError("TODO(M2): data loader not implemented yet")


if __name__ == "__main__":
    main()
