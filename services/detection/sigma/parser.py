class SigmaParser:
    def parse(self, document): return {"title": document.get("title", ""), "description": document.get("description", ""), "level": document.get("level", "medium"), "tags": document.get("tags", []), "detection": document.get("detection", {})}
