import time
import threading

from collections import OrderedDict
from concurrent.futures import Future

from app.database import fetch_user_from_database


class UserCache:

    def __init__(self, max_size=3, ttl=30):

        self.max_size = max_size
        self.ttl = ttl

        # Stores users in LRU order
        self.cache = OrderedDict()

        # Thread safety
        self.lock = threading.Lock()

        # Prevent duplicate database calls
        self.inflight = {}

        # Statistics
        self.hits = 0
        self.misses = 0
        self.db_calls = 0

        self.total_db_latency = 0
        self.max_db_latency = 0

    def get_user(self, user_id):

        # Step 1: Check cache
        with self.lock:

            entry = self.cache.get(user_id)

            if entry:

                user, expiry = entry

                # Check expiration
                if time.monotonic() < expiry:

                    self.cache.move_to_end(user_id)

                    self.hits += 1

                    return user

                # Remove expired entry
                del self.cache[user_id]

            self.misses += 1

            # Step 2: Check whether another thread
            # is already fetching this user

            if user_id in self.inflight:

                future = self.inflight[user_id]
                is_owner = False

            else:

                future = Future()
                self.inflight[user_id] = future
                is_owner = True

                self.db_calls += 1

        # Step 3: Wait for the existing database request
        if not is_owner:

            return future.result()

        # Step 4: Fetch from database
        start = time.perf_counter()

        try:

            user = fetch_user_from_database(user_id)

            latency = time.perf_counter() - start

            # Step 5: Store successful result
            with self.lock:

                self.total_db_latency += latency

                self.max_db_latency = max(
                    self.max_db_latency,
                    latency
                )

                self.cache[user_id] = (
                    user,
                    time.monotonic() + self.ttl
                )

                self.cache.move_to_end(user_id)

                # Step 6: LRU eviction
                if len(self.cache) > self.max_size:

                    self.cache.popitem(last=False)

            future.set_result(user)

            return user

        except Exception as error:

            latency = time.perf_counter() - start

            with self.lock:

                self.total_db_latency += latency

                self.max_db_latency = max(
                    self.max_db_latency,
                    latency
                )

            # Share the failure with waiting threads
            future.set_exception(error)

            raise

        finally:

            with self.lock:

                self.inflight.pop(user_id, None)

    def stats(self):

        with self.lock:

            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "cache_hits": self.hits,
                "cache_misses": self.misses,
                "database_calls": self.db_calls,
                "average_db_latency": (
                    self.total_db_latency / self.db_calls
                    if self.db_calls else 0
                ),
                "max_db_latency": self.max_db_latency,
                "cached_user_ids": list(self.cache.keys())
            }