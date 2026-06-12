import sqlite3

def get_risk_data():

    conn=sqlite3.connect("emotions.db")
    cur=conn.cursor()

    cur.execute("""
    SELECT emotion
    FROM emotions
    ORDER BY id DESC
    LIMIT 5
    """)

    recent=[r[0] for r in cur.fetchall()]

    negative_count=0

    for e in recent:
        if e in ["sad","fear","anger"]:
            negative_count+=1

    if negative_count>=4:
        risk="High Alert ⚠️"
    elif negative_count>=2:
        risk="Moderate"
    else:
        risk="Low"


    insight="Mood stable."

    if recent.count("fear")>=3:
        insight="Possible anxiety pattern detected."

    elif recent.count("sad")>=3:
        insight="Repeated sadness trend detected."

    conn.close()

    return risk, insight