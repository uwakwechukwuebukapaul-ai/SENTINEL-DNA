"""
Sentinel DNA
Database Inspector

Displays:
- Database tables
- Latest case
- Evidence
- Timeline
- Notes
"""

import sqlite3


DATABASE = "soc.db"


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()


print("🧬 SENTINEL DNA DATABASE INSPECTOR")
print("=" * 50)


# =====================================
# SHOW TABLES
# =====================================

print("\nDATABASE TABLES")
print("-" * 50)

cursor.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """
)

tables = cursor.fetchall()

for table in tables:

    print(table["name"])



# =====================================
# LATEST CASE
# =====================================

print("\nLATEST CASE")
print("-" * 50)

try:

    cursor.execute(
        """
        SELECT *
        FROM cases
        ORDER BY id DESC
        LIMIT 1
        """
    )

    case = cursor.fetchone()

    if case:

        for key in case.keys():

            print(f"{key}: {case[key]}")

    else:

        print("No cases found.")

except sqlite3.Error as error:

    print(error)



# =====================================
# EVIDENCE
# =====================================

print("\nLATEST EVIDENCE")
print("-" * 50)

try:

    cursor.execute(
        """
        SELECT *
        FROM evidence
        ORDER BY id DESC
        LIMIT 5
        """
    )

    evidence = cursor.fetchall()

    if evidence:

        for item in evidence:

            print(dict(item))

    else:

        print("No evidence found.")

except sqlite3.Error as error:

    print(error)



# =====================================
# TIMELINE
# =====================================

print("\nLATEST TIMELINE EVENTS")
print("-" * 50)

try:

    cursor.execute(
        """
        SELECT *
        FROM timeline
        ORDER BY id DESC
        LIMIT 5
        """
    )

    events = cursor.fetchall()

    if events:

        for event in events:

            print(dict(event))

    else:

        print("No timeline events found.")

except sqlite3.Error as error:

    print(error)



# =====================================
# NOTES
# =====================================

print("\nLATEST NOTES")
print("-" * 50)

try:

    cursor.execute(
        """
        SELECT *
        FROM case_notes
        ORDER BY id DESC
        LIMIT 5
        """
    )

    notes = cursor.fetchall()

    if notes:

        for note in notes:

            print(dict(note))

    else:

        print("No notes found.")

except sqlite3.Error as error:

    print(error)



connection.close()

print("\n✅ Database inspection complete.")