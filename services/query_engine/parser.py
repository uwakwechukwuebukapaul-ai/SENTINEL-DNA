import re
class QueryParser:
    def parse(self, query): return {k.lower():v for k,v in re.findall(r'(user|asset|ioc|severity|source|technique)\s*=\s*["\']?([\w.-]+)',query,re.I)}
