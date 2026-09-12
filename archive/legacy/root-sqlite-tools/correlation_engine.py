import sqlite3
from datetime import datetime


DATABASE = "soc.db"


def find_existing_case(ioc):

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT case_id
        FROM evidence
        WHERE data = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (ioc,)
    )


    result = cursor.fetchone()

    conn.close()


    if result:
        return result[0]

    return None



def correlate_alert(ioc):

    existing_case = find_existing_case(ioc)


    if existing_case:

        return {
            "action": "ATTACH_TO_EXISTING_CASE",
            "case_id": existing_case
        }


    return {
        "action": "CREATE_NEW_CASE",
        "case_id": None
    }



if __name__ == "__main__":

    test_ioc = "https://micr0soft-login.xyz/verify"


    result = correlate_alert(test_ioc)


    print("=" * 50)
    print("SENTINEL DNA CORRELATION ENGINE")
    print("=" * 50)

    print(result)