"""Environment configuration shared by development and later test fixtures."""

import os


def settings_from_environment() -> dict:
    return {
        "MONGODB_HOST": os.getenv("MONGODB_HOST", "mongodb://127.0.0.1:27017"),
        "MONGODB_DB": os.getenv("MONGODB_DB", "skipq_dev"),
        "TEST_MONGODB_DB": os.getenv("TEST_MONGODB_DB", "skipq_test"),
        "FRONTEND_ORIGIN": os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173"),
        "TOKEN_SECRET": os.getenv("TOKEN_SECRET"),
    }
