from dataclasses import dataclass, field
@dataclass
class SavedQuery:
    organization_id:str; name:str; query:str; shared:bool=False; id:str=""
