import asyncio
import aiohttp
import random
from flask import Flask, jsonify, render_template
from collections import deque
import threading

API_URL="https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

app = Flask(__name__)

real_history=deque(maxlen=200)
prediction_history=deque(maxlen=10)

last_period=0
current_prediction="LOADING..."
confidence=0

session=None

# ---------------- API (STRONG FIX) ----------------
async def get_latest():
    global session
    try:
        async with session.get(API_URL, timeout=10) as r:
            data = await r.json(content_type=None)

            items = data.get("data", {}).get("list", [])
            if not items:
                return None

            item = items[0]

            period = int(item.get("issueNumber", 0))
            number = int(item.get("number", 0))

            size = "BIG" if number >= 5 else "SMALL"

            if number == 0:
                color = "RED/VIOLET"
            elif number == 5:
                color = "GREEN/VIOLET"
            elif number % 2 == 0:
                color = "RED"
            else:
                color = "GREEN"

            return {
                "period": period,
                "number": number,
                "size": size,
                "color": color
            }

    except Exception as e:
        print("API ERROR:", e)
        return None

# ---------------- AI ENGINE ----------------
def ai_predict():

    if len(real_history) < 5:
        return random.choice(["BIG","SMALL","RED","GREEN"]),40

    score={"BIG":0,"SMALL":0,"RED":0,"GREEN":0}

    last=list(real_history)[-10:]

    for i,r in enumerate(last):
        score[r["size"]]+=i+1
        if "RED" in r["color"]:
            score["RED"]+=1
        if "GREEN" in r["color"]:
            score["GREEN"]+=1

    # streak boost
    if len(last)>=3:
        if last[-1]["size"]==last[-2]["size"]==last[-3]["size"]:
            score[last[-1]["size"]]+=5

    # zig-zag detect
    if len(last)>=4:
        if last[-1]["size"]!=last[-2]["size"] and last[-2]["size"]!=last[-3]["size"]:
            score[last[-1]["size"]]+=4

    best=max(score,key=score.get)
    conf=min(90,50+score[best])

    return best,conf

# ---------------- LOOP ----------------
async def game_loop():
    global last_period,current_prediction,confidence,session

    session=aiohttp.ClientSession()

    while True:
        try:
            data=await get_latest()

            if not data:
                await asyncio.sleep(1)
                continue

            period=data["period"]

            if period==last_period:
                await asyncio.sleep(0.5)
                continue

            # store real history
            real_history.append({
                "period":period,
                "number":data["number"],
                "size":data["size"],
                "color":data["color"]
            })

            # AI prediction
            pred,conf=ai_predict()

            current_prediction=f"{period+1} → {pred}"
            confidence=conf

            prediction_history.appendleft(current_prediction)

            last_period=period

        except Exception as e:
            print("LOOP ERROR:",e)
            await asyncio.sleep(1)

# ---------------- THREAD ----------------
def start_loop():
    asyncio.run(game_loop())

threading.Thread(target=start_loop).start()

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
