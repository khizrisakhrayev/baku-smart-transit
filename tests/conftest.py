import os

# Tests must never touch backend/data.db: the app's startup opens DB_PATH.
os.environ["DB_PATH"] = ":memory:"
