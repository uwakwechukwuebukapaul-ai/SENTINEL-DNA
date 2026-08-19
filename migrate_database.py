"""
Sentinel DNA
Database Migration Tool

Updates:
- Adds analyst column
- Adds notes column
- Repairs IOC table structure
- Fixes old records
"""


import sqlite3
from database.connection import resolve_database_path



DATABASE = resolve_database_path()



conn = sqlite3.connect(DATABASE)

cursor = conn.cursor()



# =====================================
# INCIDENT TABLE UPDATES
# =====================================


try:

    cursor.execute(
        """
        ALTER TABLE incidents
        ADD COLUMN analyst TEXT DEFAULT 'None'
        """
    )

    print("✅ Added analyst column")

except sqlite3.Error:

    pass





try:

    cursor.execute(
        """
        ALTER TABLE incidents
        ADD COLUMN notes TEXT DEFAULT 'No investigation notes'
        """
    )

    print("✅ Added notes column")

except sqlite3.Error:

    pass






# =====================================
# FIX OLD INCIDENT RECORDS
# =====================================


try:

    cursor.execute(
        """
        UPDATE incidents

        SET 
        analyst='None',
        notes='No investigation notes'

        WHERE analyst IS NULL
        """
    )

except sqlite3.Error:

    pass







# =====================================
# REBUILD IOC TABLE
# =====================================


cursor.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    AND name='iocs'
    """
)


ioc_table = cursor.fetchone()



if ioc_table:


    cursor.execute(
        """
        PRAGMA table_info(iocs)
        """
    )


    columns = [
        column[1]
        for column in cursor.fetchall()
    ]



    if "type" not in columns:

        raise RuntimeError(
            "Canonical or unsupported IOC schema detected. "
            "Run database/migrations/migrate_ioc_contract.py explicitly."
        )


        print("⚠️ Old IOC table detected")

        cursor.execute(
            """
            DROP TABLE iocs
            """
        )


        cursor.execute(
            """
            CREATE TABLE iocs
            (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT,

            type TEXT,

            value TEXT,

            created TEXT

            )
            """
        )


        print("✅ IOC table rebuilt")



else:

    raise RuntimeError(
        "IOC table is missing. Run database/migrations/migrate_ioc_contract.py "
        "after provisioning the legacy IOC table."
    )


    cursor.execute(
        """
        CREATE TABLE iocs
        (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        case_id TEXT,

        type TEXT,

        value TEXT,

        created TEXT

        )
        """
    )


    print("✅ IOC table created")







# =====================================
# COMMIT
# =====================================


conn.commit()

conn.close()



print("\n🧬 Sentinel DNA database migration completed successfully")
