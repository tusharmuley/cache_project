import time

# Dummy database
USERS = {
    1: {"id": 1, "name": "Tushar", "email": "tushar@gmail.com"},
    2: {"id": 2, "name": "Rahul", "email": "rahul@gmail.com"},
    3: {"id": 3, "name": "Amit", "email": "amit@gmail.com"},
    4: {"id": 4, "name": "Priya", "email": "priya@gmail.com"},
    5: {"id": 5, "name": "Sneha", "email": "sneha@gmail.com"},
    6: {"id": 6, "name": "Vijay", "email": "vijay@gmail.com"},
}


def fetch_user_from_database(user_id):
    """Simulate a slow database lookup."""

    time.sleep(0.2)

    user = USERS.get(user_id)

    if user is None:
        raise ValueError(f"User {user_id} not found")

    return user