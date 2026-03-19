import asyncio
import aiohttp
import random
from flask import Flask, jsonify, render_template
from collections import deque
import threading

API_URL="https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

app = Flask(__name__)

history=deque(maxlen=200)
number_history=deque(maxlen=200)
prediction_history=deque(maxlen=10)

last_period=0
current_prediction="WAIT"
confidence=0

session=None

# ---------------- API FIX ----------------
async def get_latest():
    global session
    try:
        async with session.get(API_URL, timeout=10) as r:
            data = await r.json(content_type=None)

            if "data" not in data or "list" not in data["data"]:
                return None,None,None,None

            items = data["data"]["list"]
            if not items:
                return None,None,None,None

            item = items[0]

            period = int(item.get("issueNumber",0))
            number = int(item.get("number",0))

            size = "BIG" if number >= 5 else "SMALL"

            if number == 0:
                color = "RED"
            elif number == 5:
                color = "GREEN"
            elif number % 2 == 0:
                color = "RED"
            else:
                color = "GREEN"

            return period,size,color,number

    except Exception as e:
        print("API ERROR:", e)
        return None,None,None,None

# ---------------- AI FIX ----------------
def ai_predict():
    global confidence

    if len(history)<5:
        confidence=40
        return random.choice(["BIG","SMALL","RED","GREEN"])

    h=list(history)
    n=list(number_history)

    score={"BIG":0,"SMALL":0,"RED":0,"GREEN":0}

    # trend
    for i,v in enumerate(h[-10:]):
        score[v]+=(i+1)

    # repeat boost
    if len(h)>=2 and h[-1]==h[-2]:
        score[h[-1]]+=4

    # color logic
    for num in n[-10:]:
        if num==0:
            score["RED"]+=3
        elif num==5:
            score["GREEN"]+=3
        elif num%2==0:
            score["RED"]+=1
        else:
            score["GREEN"]+=1

    best=max(score,key=score.get)
    confidence=min(90,50+score[best])

    return best

# ---------------- LOOP FIX ----------------
async def game_loop():
    global last_period,current_prediction,session

    session=aiohttp.ClientSession()

    while True:
        try:
            period,size,color,number=await get_latest()

            if period is None:
                await asyncio.sleep(1)
                continue

            if period == last_period:
                await asyncio.sleep(0.5)
                continue

            history.append(size)
            number_history.append(number)

            pred=ai_predict()
            current_prediction=f"{period+1} → {pred}"

            prediction_history.appendleft(current_prediction)

            last_period=period

        except Exception as e:
            print("LOOP ERROR:", e)
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
        "real": [str(x) for x in list(history)[-10:]],
        "prediction": list(prediction_history),
        "current": current_prediction,
        "confidence": confidence
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
