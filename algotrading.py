import websocket, json, requests, sys
from config import *
import dateutil.parser
from datetime import datetime
#establishing socket connection to coinbasepro
#connected to realtime datafeed over websockets
#able to process tick data for bitcoin
#able to aggregate that data and keep track of candlesticks including their open high low and close prices
#figure out how to process this list, detect a pattern in the price data, and then execute trades based upon
#the price patterns
#reversal candlesticks
#three white soldiers pattern
#take distance from first candles open to last candles close and go for a 2:1 ratio place a bracket order at the
#market price

#take profit at 2*distance
#cut losses if price goes back to the opening price of the first candle
#


minutes_processed = {}
#tracks each minute
minute_candlesticks = []
#tracking candlesticks
current_tick = None
previous_tick = None
in_position = False

BASE_URL = "https://paper-api.alpaca.markets"
API_KEY = "PKU265B1GZ4TRJV6SBKT"
SECRET_KEY = "9PQDU96sefu8gbkcrZxKYKuYMH0OQEWwo5Gz4Y9j"
ACCOUNT_URL = "{}/v2/account".format(BASE_URL)
ORDERS_URL = "{}/v2/orders".format(BASE_URL)
POSITIONS_URL = "{}/v2/positions".format(BASE_URL, SYMBOL)

HEADERS = {'APCA_API_KEY_ID': API_KEY, 'APCA_API_SECRET_KEY': SECRET_KEY}


def place_order(profit_price, loss_price):
    data = {
        "symbol": SYMBOL,
        "qty":1,
        "side":"buy",
        "type":"market",
        "time_in_force":"gtc",
        "order_class":"bracket",
        "take_profit": {
            "limit_price": profit_price
        },
        "stop_loss": {
            "stop_price": loss_price
        }
    }

    r = requests.post(ORDERS_URL, json=data, headers=HEADERS)

    response = json.loads(r.content)

    print(response)




def on_open(ws):
    print("Opened Connection")

    auth_data = {
        "action": "auth",
        "parmas": API_KEY
    }

    ws.send(json.dumps(auth_data))

    channel_data = {
        "action": "subscribe",
        "parmas": TICKERS
    }

    ws.send(channel_data)


def on_message(ws, message):
    global current_tick, previous_tick, in_position

    previous_tick = current_tick
    current_tick = json.loads(message)[0]
    #current tick becomes the very first price that we get
    print("current tick")
    print("=== Received Tick ===")
    print("{} @ {}".format(current_tick['t'], current_tick['bp']))

    #dont care about seconds and milliseconds only minute changes
    #minute changes keep track of the closing price and associate it with the opening price

    tick_datetime_object = datetime.utcfromtimestamp(current_tick['t']/1000)
    tick_dt = tick_datetime_object.strftime("%m/%d/%Y %H:%M")
    print(tick_dt) #prints a shorter timestamp for the stocks in question
    print(tick_datetime_object.minute) #prints out data for each minute
    #use this to keep track of the minute and see if it changes on any given tick

    #going to keep track of a list of unique minute candlesticks
    #only add the minute into the list if it hasnt been accounted for in the ticker data

    if not tick_dt in minutes_processed: #know we have a new minute
        print("starting new candlestick")
        minutes_processed[tick_dt] = True
        print(minutes_processed)

        if len(minute_candlesticks) > 0:
            minute_candlesticks[-1]["close"] = previous_tick["bp"]

            #once we have a candlestick we can look at the previous candlestick close to the previous tick's price
            #to record the closing price of the previous candlestick


        minute_candlesticks.append({
            "minute": tick_dt,
            "open": current_tick["bp"] , #first tick
            "high": current_tick["bp"],
            "low": current_tick["bp"]
        })


    if len(minute_candlesticks) > 0 :
        current_candlestick = minute_candlesticks[-1] #current candlestick is the last one in the list
        if current_tick["bp"] > current_candlestick["high"]:
            current_candlestick["high"] = current_tick["bp"] #updating the high
        if current_tick["bp"] < current_candlestick["low"]:
            current_candlestick["low"] = current_tick["bp"] # keep checking for new highs and lows in the candlestick

        print("===Candlesticks===")
        for candlestick in minute_candlesticks:
            print(candlestick)

        #as the minute changes, new tick is recorded and hence new highs and lows
        #also creates a new candlestick

        if len(minute_candlesticks) > 3:
            print("== there are more than 3 candlesticks, checking for pattern ==")
            last_candle = minute_candlesticks[-2]
            previous_candle = minute_candlesticks[-3]
            first_candle = minute_candlesticks[-4]

            print("== let's compare the last 3 candle closes ==")
            if last_candle['close'] > previous_candle['close'] and previous_candle['close'] > first_candle['close']:
                print("=== Three green candlesticks in a row, let's make a trade! ===")
                distance = last_candle['close'] - first_candle['open']
                print("Distance is {}".format(distance))
                profit_price = last_candle['close'] + (distance * 2)
                print("I will take profit at {}".format(profit_price))
                loss_price = first_candle['open']
                print("I will sell for a loss at {}".format(loss_price))

                if not in_position:
                    print("== Placing order and setting in position to true ==")
                    in_position = True
                    place_order(profit_price, loss_price)
                    sys.exit()
            else:
                print("No go")




def on_close(ws):
    print("closed connection")

    socket = "wss://alpaca.socket.polygon.io/stocks"
    ws = websocket.WebSocketApp(socket, on_open=on_open, on_message=on_message, on_close= on_close)

    ws.run_forever()

    #Keeping track of the high and low price to come up with the candle stick data


