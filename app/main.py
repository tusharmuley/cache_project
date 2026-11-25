from fastapi import FastAPI, HTTPException
from app.cache import UserCache
from app.database import USERS

app = FastAPI(title="Thread Safe LRU User Cache")

user_cache = UserCache(max_size=3, ttl=30)


@app.get("/")
def home():
    return {"message": "User Cache API is running"}


@app.get("/users")
def get_all_users():
    try:
        users = []

        for user_id in USERS.keys():
            user = user_cache.get_user(user_id)
            users.append(user)

        return {
            "success": True,
            "count": len(users),
            "data": users
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch users"
        )


@app.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        user = user_cache.get_user(user_id)
        return {"success": True, "data": user}

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception:
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/cache/stats")
def cache_stats():
    return user_cache.stats()