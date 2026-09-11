class CredentialManager:
    def __init__(self): self.refs={}
    def store(self,credential_id,connector_id,credential_type,encrypted_reference):
        if not isinstance(encrypted_reference, str) or not encrypted_reference.strip():
            raise ValueError("credential_reference_required")
        self.refs[credential_id]={"credential_id":credential_id,"connector_id":connector_id,"credential_type":credential_type,"encrypted_reference":encrypted_reference}
        return self.get_masked(credential_id)
    def rotate(self,credential_id,reference):
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("credential_reference_required")
        self.refs[credential_id]["encrypted_reference"]=reference
        return self.get_masked(credential_id)
    def get_masked(self,credential_id):
        x=dict(self.refs[credential_id]); x["encrypted_reference"]="***"; return x
