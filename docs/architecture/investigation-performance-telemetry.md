# Investigation Performance Telemetry

Sentinel DNA now records an additive performance trace for each coordinator
investigation. The trace measures end-to-end coordinator latency and these
component boundaries:

- coordinator (the end-to-end envelope)
- orchestrator
- evidence retrieval and normalization
- IOC enrichment
- MITRE mapping
- historical memory retrieval
- evidence reasoning
- report generation

Measurements use `time.perf_counter()` and are reported in milliseconds. The
coordinator value intentionally overlaps child components; it is the total
envelope, not an additive sum.

## Security boundary

`InvestigationPerformanceTelemetry` is observational only. It does not call
authorization services, select verdicts, authorize responses, or alter
`InvestigationResult` fields. It adds a `performance_telemetry` object under
the existing result `metadata` dictionary. Missing tenant context prevents
persistent telemetry evidence, and telemetry persistence failures are captured
in the summary without changing investigation execution.

For tenant-scoped investigations, the summary is appended through the existing
`AuditService` as `investigation_performance_telemetry`. The audit table is
append-only and retains tenant, case, investigation, resource, outcome,
latency, and sanitized structured details. No raw provider payloads or
evidence contents are copied into telemetry.

## Benchmark

Generate a synthetic benchmark report with:

```text
python scripts/benchmark_investigation_performance.py --iterations 10 --output artifacts/investigation-performance-benchmark.json
```

The benchmark exercises attribution boundaries without external providers or
authorization changes. It reports p50, p95, and maximum timings for every
component. Timing values are host-dependent; the benchmark replay digest covers
only the fixture inputs and component contract, so replay validation is not
coupled to machine load.
