CREATE TABLE app_user (
    chat_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES app_user (chat_id),
    trip_type TEXT NOT NULL,
    origins TEXT NOT NULL,
    destinations TEXT NOT NULL,
    origin_label TEXT NOT NULL,
    destination_label TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    return_date TEXT,
    target_price TEXT NOT NULL,
    status TEXT NOT NULL,
    last_notified_price TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_watch_status ON watch (status);
CREATE INDEX idx_watch_chat_status ON watch (chat_id, status);

CREATE TABLE price_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    return_date TEXT,
    min_price TEXT NOT NULL,
    airline TEXT NOT NULL,
    departure TEXT NOT NULL,
    stops INTEGER NOT NULL,
    checked_at TEXT NOT NULL
);

CREATE INDEX idx_snapshot_route ON price_snapshot (origin, destination, departure_date, return_date, checked_at);

CREATE TABLE check_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    routes_total INTEGER NOT NULL DEFAULT 0,
    routes_failed INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE search_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES app_user (chat_id),
    requested_at TEXT NOT NULL
);

CREATE INDEX idx_search_request_chat ON search_request (chat_id, requested_at);
