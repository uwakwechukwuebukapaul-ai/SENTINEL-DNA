import sqlite3


DATABASE = "soc.db"


conn = sqlite3.connect(DATABASE)

cursor = conn.cursor()


# Keep production investigation cases only
cursor.execute("""
DELETE FROM cases
WHERE case_id NOT IN (
    'INC-20260731-1B5374'
)
""")


cursor.execute("""
DELETE FROM evidence
WHERE case_id NOT IN (
    'INC-20260731-1B5374'
)
""")


cursor.execute("""
DELETE FROM timeline
WHERE case_id NOT IN (
    'INC-20260731-1B5374'
)
""")


conn.commit()


print("🧬 Sentinel DNA test data cleaned")


conn.close()