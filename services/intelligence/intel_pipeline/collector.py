class OfflineCollector:
 def collect(self,source,payload=None): return list(payload or [])
class STIXTAXIICollector(OfflineCollector): feed_type="stix_taxii"
class MISPCollector(OfflineCollector): feed_type="misp"
class LocalFileCollector(OfflineCollector): feed_type="local"
