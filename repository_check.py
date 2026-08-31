"""
Sentinel DNA
Repository Layer Test
"""


from database.models import create_tables

from database.repository import (
    create_case,
    add_evidence_record,
    get_evidence
)



# Initialize database

create_tables()



from datetime import datetime
import uuid

case_id = (
    "INC-"
    + datetime.now().strftime("%Y%m%d")
    + "-"
    + uuid.uuid4().hex[:6].upper()
)



# Create test case

create_case({

    "case_id":

        case_id,


    "title":

        "Phishing Investigation",


    "severity":

        "HIGH",


    "description":

        "Testing evidence storage layer"

})




# Add evidence

hash_value = add_evidence_record(

    case_id,

    "MALICIOUS_URL",

    "https://micr0soft-login.xyz/verify"

)



print(
    "🧬 SENTINEL DNA EVIDENCE TEST"
)


print("=" * 40)



print(

    "SHA256:",

    hash_value

)




print("\nCASE EVIDENCE")

print("=" * 40)



for evidence in get_evidence(case_id):

    print(evidence)