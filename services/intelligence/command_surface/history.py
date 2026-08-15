class HistoryContext:
    def compare(self, current, previous=None):
        if not previous: return {"current": current, "previous": None, "trend": "UNKNOWN"}
        return {"current": current, "previous": previous, "trend": "stable" if current == previous else "changed"}
