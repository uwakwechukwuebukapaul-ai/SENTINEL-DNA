class InMemoryEventStorage:
    """Replaceable storage boundary for PostgreSQL/object-store implementations."""
    def __init__(self): self.events = []
    def append(self, event): self.events.append(event); return event
    def extend(self, events): self.events.extend(events); return events
