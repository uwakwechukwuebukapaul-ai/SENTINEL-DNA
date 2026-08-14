class CredentialManager:
    def __init__(self): self.refs={}
    def store(self,credential_id,connector_id,credential_type,encrypted_reference): self.refs[credential_id]={"credential_id":credential_id,"connector_id":connector_id,"credential_type":credential_type,"encrypted_reference":encrypted_reference}; return self.refs[credential_id]
    def rotate(self,credential_id,reference): self.refs[credential_id]["encrypted_reference"]=reference; return self.refs[credential_id]
    def get_masked(self,credential_id):
        x=dict(self.refs[credential_id]); x["encrypted_reference"]="***"; return x
