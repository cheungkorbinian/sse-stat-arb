from __future__ import annotations

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from sse_data.config import Settings, get_settings

INSTRUMENTS = "instruments"
DAILY_BARS = "daily_bars"
INGEST_STATE = "ingest_state"
INGEST_RUNS = "ingest_runs"


def get_client(settings: Settings | None = None) -> MongoClient:
    settings = settings or get_settings()
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=8000)


def get_db(client: MongoClient | None = None, settings: Settings | None = None) -> Database:
    settings = settings or get_settings()
    client = client or get_client(settings)
    return client[settings.mongodb_db]


def ensure_indexes(db: Database) -> None:
    db[INSTRUMENTS].create_index("ticker", unique=True)
    db[INSTRUMENTS].create_index("sse_code", unique=True)
    db[DAILY_BARS].create_index(
        [("ticker", ASCENDING), ("date", ASCENDING)],
        unique=True,
        name="ticker_date_unique",
    )
    db[DAILY_BARS].create_index("date")
    db[INGEST_STATE].create_index("ticker", unique=True)
    db[INGEST_RUNS].create_index("started_at")


def bars_collection(db: Database) -> Collection:
    return db[DAILY_BARS]


def instruments_collection(db: Database) -> Collection:
    return db[INSTRUMENTS]


def ingest_state_collection(db: Database) -> Collection:
    return db[INGEST_STATE]


def ingest_runs_collection(db: Database) -> Collection:
    return db[INGEST_RUNS]
