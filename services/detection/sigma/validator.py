class SigmaValidator:
    def validate(self, document): return {"valid": bool(document.get("title") and document.get("detection")), "errors": [] if document.get("title") and document.get("detection") else ["title_and_detection_required"]}
