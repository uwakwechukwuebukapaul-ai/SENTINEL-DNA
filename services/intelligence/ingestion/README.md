# Real-time security data ingestion fabric

This tenant-aware layer collects and normalizes telemetry for downstream
intelligence. Existing connector and evidence ownership remains unchanged.
Processing is read-only: ingestion stores normalized observations and never
executes response actions or mutates detections.
