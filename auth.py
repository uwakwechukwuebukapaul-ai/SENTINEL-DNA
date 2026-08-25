import secrets

from werkzeug.security import generate_password_hash, check_password_hash


# Demo analyst account
DEMO_PASSWORD = secrets.token_urlsafe(32)
users = {

    "analyst": generate_password_hash(DEMO_PASSWORD)

}



def login(username, password):

    if username in users:

        if check_password_hash(users[username], password):

            return True


    return False



if __name__ == "__main__":


    print(f"Demo analyst password for this run: {DEMO_PASSWORD}")
    username = input("Username: ")

    password = input("Password: ")


    if login(username, password):

        print("✅ Login successful")

    else:

        print("❌ Invalid credentials")
