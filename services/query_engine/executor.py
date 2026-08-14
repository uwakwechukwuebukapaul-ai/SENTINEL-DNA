from .parser import QueryParser
class SecurityQueryExecutor:
    def __init__(self, query_engine): self.query_engine=query_engine; self.parser=QueryParser(); self.history=[]; self.saved=[]
    def run(self, org, query): result=self.query_engine.search(org,self.parser.parse(query)); self.history.append({"organization_id":org,"query":query,"result_count":result["count"]}); return result
