import sqlite3


DATABASE = "soc.db"



def get_analytics():

    conn = sqlite3.connect(
        DATABASE
    )

    cursor = conn.cursor()



    cursor.execute(
        "SELECT * FROM incidents"
    )


    incidents = cursor.fetchall()


    conn.close()



    total = len(incidents)



    high = 0
    open_cases = 0
    investigating = 0
    resolved = 0


    risk_scores = []

    severity_data = {}

    attack_types = {}




    for incident in incidents:


        severity = incident[3]

        risk = incident[4]

        mitre = incident[5]

        status = incident[6]



        risk_scores.append(
            risk
        )



        # Severity count

        severity_data[severity] = (
            severity_data.get(severity,0)
            + 1
        )



        # Attack type

        attack = (
            "Phishing"
            if "T1566" in mitre
            else mitre
        )


        attack_types[attack] = (
            attack_types.get(attack,0)
            + 1
        )




        if severity == "HIGH":

            high += 1



        if status == "OPEN":

            open_cases += 1



        elif status == "INVESTIGATING":

            investigating += 1



        elif status == "RESOLVED":

            resolved += 1





    average_risk = 0


    max_risk = 0



    if risk_scores:


        average_risk = round(
            sum(risk_scores)
            /
            len(risk_scores),
            2
        )


        max_risk = max(
            risk_scores
        )





    return {


        "total":
        total,


        "high":
        high,


        "open":
        open_cases,


        "investigating":
        investigating,


        "resolved":
        resolved,


        "average_risk":
        average_risk,


        "max_risk":
        max_risk,


        "severity_data":
        severity_data,


        "attack_types":
        attack_types

    }