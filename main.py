import requests
import time
import threading
from flask import Flask, jsonify, render_template
from collections import deque
import random

API_URL="https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

app = Flask(__name__)

real_history=deque(maxlen=200)
prediction_history=deque(maxlen=10)

last_period=0
current_prediction="LOADING..."
confidence=0

# ---------------- API FIX ----------------
def get_latest():
    try:
        r = requests.get(API_URL, timeout=5, headers={
            "User-Agent":"Mozilla/5.0"
        })
        data = r.json()

        items = data.get("data", {}).get("list", [])
        if not items:
            return None

        item = items[0]

        period = int(item["issueNumber"])
        number = int(item["number"])

        size = "BIG" if number >= 5 else "SMALL"

        if number == 0:
            color = "RED/VIOLET"
        elif number == 5:
            color = "GREEN/VIOLET"
        elif number % 2 == 0:
            color = "RED"
        else:
            color = "GREEN"

        return period,number,size,color

    except Exception as e:
        print("API ERROR:", e)
        return None

# ---------------- AI ENGINE ----------------
def ai_predict():
    if len(real_history)<5:
        return random.choice(["BIG","SMALL","RED","GREEN"]),50

    score={"BIG":0,"SMALL":0,"RED":0,"GREEN":0}

    last=list(real_history)[-10:]

    for i,r in enumerate(last):
        score[r["size"]]+=i+1

        if "RED" in r["color"]:
            score["RED"]+=1
        if "GREEN" in r["color"]:
            score["GREEN"]+=1

    # streak
    if len(last)>=3:
        if last[-1]["size"]==last[-2]["size"]==last[-3]["size"]:
            score[last[-1]["size"]]+=5

    best=max(score,key=score.get)
    conf=min(90,50+score[best])

    return best,conf

# ---------------- LOOP FIX ----------------
def loop():
    global last_period,current_prediction,confidence

    while True:
        data=get_latest()

        if not data:
            time.sleep(2)
            continue

        period,number,size,color=data

        if period==last_period:
            time.sleep(1)
            continue

        real_history.append({
            "period":period,
            "number":number,
            "size":size,
            "color":color
        })

        pred,conf=ai_predict()

        current_prediction=f"{period+1} → {pred}"
        confidence=conf

        prediction_history.appendleft(current_prediction)

        last_period=period

        time.sleep(2)

# ---------------- START THREAD ----------------
threading.Thread(target=loop, daemon=True).start()

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/data')
def data():
    return jsonify({
        "real":[
            f'{x["period"]} → {x["number"]} {x["size"]} {x["color"]}'
            for x in list(real_history)[-10:]
        ],
        "prediction":list(prediction_history),
        "current":current_prediction,
        "confidence":confidence
    })

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
