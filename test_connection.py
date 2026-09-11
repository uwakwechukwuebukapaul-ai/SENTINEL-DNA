from database.connection import database

print("=" * 50)
print("Sentinel DNA Database Test")
print("=" * 50)

with database.session() as conn:

    cursor = conn.cursor()

    cursor.execute("SELECT version();")

    row = cursor.fetchone()

    if isinstance(row, dict):
        version = row["version"]
    else:
        version = row[0]

    print("PostgreSQL Version :", version)

print("\nDatabase connection successful!")