import sqlite3

from observatoire.config import DATABASE_FILE

with sqlite3.connect(DATABASE_FILE) as conn:
    cursor = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    print("Tables présentes :")
    for (name,) in cursor:
        print("-", name)