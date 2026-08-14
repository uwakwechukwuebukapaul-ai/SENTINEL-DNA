# AI event correlation and investigation trigger engine

This tenant-aware layer correlates normalized signals deterministically and
emits advisory investigation triggers. It does not replace the existing
correlation engine, bypass `InvestigationCoordinator`, execute SOAR, or mutate
detections. Trigger consumers remain responsible for approval and investigation
creation through the canonical coordinator.
