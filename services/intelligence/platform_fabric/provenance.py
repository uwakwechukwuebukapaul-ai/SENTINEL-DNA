class ProvenanceIndex:
    def collect(self,records): return [r.provenance for r in records]
