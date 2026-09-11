import sqlite3

conn = sqlite3.connect("soc.db")

cursor = conn.cursor()

cursor.execute("""
PRAGMA table_info(iocs)
""")

for column in cursor.fetchall():
    print(column)

conn.close()