"""
Sentinel DNA Investigation Lineage Storage Schema.

Defines SQLite schema used for:

- investigation graph persistence
- provenance records
- replay events

Designed for forensic auditability.
"""

LINEAGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS investigation_graph_nodes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    case_id TEXT NOT NULL,

    node_id TEXT NOT NULL,

    node_type TEXT NOT NULL,

    value TEXT NOT NULL,

    metadata TEXT DEFAULT '{}',

    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS investigation_graph_edges (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    case_id TEXT NOT NULL,

    edge_id TEXT NOT NULL,

    source TEXT NOT NULL,

    target TEXT NOT NULL,

    relationship TEXT NOT NULL,

    metadata TEXT DEFAULT '{}',

    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS investigation_provenance (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    case_id TEXT NOT NULL,

    record_id TEXT NOT NULL,

    stage TEXT NOT NULL,

    action TEXT NOT NULL,

    source TEXT NOT NULL,

    details TEXT DEFAULT '{}',

    confidence REAL,

    timestamp TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS investigation_replay_events (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    case_id TEXT NOT NULL,

    replay_id TEXT NOT NULL,

    event_id TEXT NOT NULL,

    stage TEXT NOT NULL,

    message TEXT NOT NULL,

    details TEXT DEFAULT '{}',

    timestamp TEXT NOT NULL
);
"""