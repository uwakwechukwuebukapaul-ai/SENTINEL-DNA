from collections import deque
from threading import RLock
class EventQueue:
    def __init__(self): self._items = deque(); self._lock = RLock()
    def publish(self, event):
        with self._lock: self._items.append(event)
        return event.id
    def consume(self, limit=100):
        with self._lock: return [self._items.popleft() for _ in range(min(limit, len(self._items)))]
    def depth(self): return len(self._items)
class RedisStreamsQueue(EventQueue):
    """Redis Streams-compatible boundary; deployers can replace methods with redis-py XADD/XREAD."""
    stream_name = "sentinel-dna-telemetry"
class KafkaCompatibleQueue(EventQueue):
    """Kafka-compatible producer/consumer boundary for future broker deployment."""
    topic = "sentinel-dna-telemetry"
