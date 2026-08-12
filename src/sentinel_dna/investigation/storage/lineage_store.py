"""
Sentinel DNA Investigation Lineage Store.

Persistent storage layer for:

- Investigation graph
- Provenance records
- Replay events

Uses SQLite to provide:

- audit history
- investigation reconstruction
- compliance evidence
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from datetime import datetime, timezone

from sentinel_dna.investigation.storage.schema import (
    LINEAGE_SCHEMA,
)


class InvestigationLineageStore:
    """
    SQLite persistence layer for investigation lineage.

    Stores immutable investigation artifacts.
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
    ) -> None:

        self.data_dir = Path(data_dir)

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.database = (
            self.data_dir
            / "investigation_lineage.db"
        )

        self._initialize()


    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection


    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                LINEAGE_SCHEMA
            )


    def save_graph(
        self,
        case_id: str,
        graph: Any,
    ) -> None:
        """
        Persist investigation graph.
        """

        timestamp = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self._connect() as connection:

            for node in graph.nodes.values():

                connection.execute(
                    """
                    INSERT INTO investigation_graph_nodes
                    (
                        case_id,
                        node_id,
                        node_type,
                        value,
                        metadata,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        node.node_id,
                        node.node_type,
                        node.value,
                        json.dumps(
                            node.metadata
                        ),
                        timestamp,
                    ),
                )


            for edge in graph.edges:

                connection.execute(
                    """
                    INSERT INTO investigation_graph_edges
                    (
                        case_id,
                        edge_id,
                        source,
                        target,
                        relationship,
                        metadata,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        edge.edge_id,
                        edge.source,
                        edge.target,
                        edge.relationship,
                        json.dumps(
                            edge.metadata
                        ),
                        timestamp,
                    ),
                )


    def save_provenance(
        self,
        case_id: str,
        provenance: Any,
    ) -> None:
        """
        Persist investigation provenance.
        """

        with self._connect() as connection:

            for record in provenance.records:

                connection.execute(
                    """
                    INSERT INTO investigation_provenance
                    (
                        case_id,
                        record_id,
                        stage,
                        action,
                        source,
                        details,
                        confidence,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        record.record_id,
                        record.stage,
                        record.action,
                        record.source,
                        json.dumps(
                            record.details
                        ),
                        record.confidence,
                        record.timestamp,
                    ),
                )


    def save_replay(
        self,
        case_id: str,
        replay: Any,
    ) -> None:
        """
        Persist investigation replay events.
        """

        with self._connect() as connection:

            for event in replay.events:

                connection.execute(
                    """
                    INSERT INTO investigation_replay_events
                    (
                        case_id,
                        replay_id,
                        event_id,
                        stage,
                        message,
                        details,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        replay.replay_id,
                        event.event_id,
                        event.stage,
                        event.message,
                        json.dumps(
                            event.details
                        ),
                        event.timestamp,
                    ),
                )


    def save_context_lineage(
        self,
        context: Any,
    ) -> None:
        """
        Persist all investigation lineage artifacts.

        Single entry point used by orchestrator.
        """

        if context.graph:
            self.save_graph(
                context.case_id,
                context.graph,
            )

        if context.provenance:
            self.save_provenance(
                context.case_id,
                context.provenance,
            )

        if context.replay:
            self.save_replay(
                context.case_id,
                context.replay,
            )