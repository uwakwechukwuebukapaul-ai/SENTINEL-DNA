# Continuous threat intelligence pipeline

This offline-safe pipeline collects placeholder feed data, normalizes indicators, enriches them for existing fusion/graph consumers, tracks freshness, and produces investigation correlation alerts. It does not call external feeds or replace Threat Fusion, Security Graph, or investigation ownership. Future adapters can support governed STIX/TAXII, MISP, and local intelligence sources.
