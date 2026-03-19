import asyncio
import aiohttp
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

async def get_latest():
    global session
    try:
        async with session.get(API_URL,timeout=5) as r:
            data=await r.json(content_type=None)
            item=data["data"]["list"][0]

            period=int(item["issueNumber"])
            number=int(item["number"])

            size="BIG" if number>=5 else "SMALL"

            if number==0:
                color="RED"
            elif number==5:
                color="GREEN"
            elif number%2==0:
                color="RED"
            else:
                color="GREEN"

            return period,size,color,number
    except:
        return None,None,None,None

def ai_predict():
    global confidence

    if len(history)<20:
        confidence=50
        return "WAIT"

    h=list(history)
    n=list(number_history)

    score={"BIG":0,"SMALL":0,"RED":0,"GREEN":0}

    for i,v in enumerate(h[-15:]):
        score[v]+=(i+1)*2

    if h[-1]!=h[-2]:
        score[h[-1]]+=5

    if h[-1]==h[-2]==h[-3]:
        score[h[-1]]+=6

    for num in n[-15:]:
        if num==0:
            score["RED"]+=4
        elif num==5:
            score["GREEN"]+=4
        elif num%2==0:
            score["RED"]+=2
        else:
            score["GREEN"]+=2

    best=max(score,key=score.get)
    confidence=min(95,50+score[best])

    return best

async def game_loop():
    global last_period,current_prediction,session

    session=aiohttp.ClientSession()

    while True:
        try:
            period,size,color,number=await get_latest()

            if period is None:
                await asyncio.sleep(1)
                continue

            if period<=last_period:
                await asyncio.sleep(0.5)
                continue

            history.append(size)
            number_history.append(number)

            pred=ai_predict()
            current_prediction=f"{period+1} → {pred}"

            prediction_history.appendleft(current_prediction)

            last_period=period

        except:
            await asyncio.sleep(1)

def start_loop():
    asyncio.run(game_loop())

threading.Thread(target=start_loop).start()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/data')
def data():
    return jsonify({
        "real": list(history)[-10:],
        "prediction": list(prediction_history),
        "current": current_prediction,
        "confidence": confidence
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
