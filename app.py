from flask import Flask, render_template
from flask_sock import Sock
from src.compounder import compound_investment_with_monthly_contributions as compound_df
from src.optimizer import compute_efficient_weights, compute_discrete_allocation
import json
import pandas as pd

app = Flask(__name__, static_folder='static')
sock = Sock(app)

@app.route("/")
def home():
    context = {'title': "finance cookbook"}
    return render_template("home.html", context=context)
@app.route("/tutorials")
def tutorials():
    context = {'title': "finance cookbook"}
    return render_template("tutorials.html", context=context)

@app.route("/tutorial-diversification")
def diversification():
    global stocks
    stocks = ["MSFT", "RCL", "DIS", "PG", "AAPL", "MMM", "AXP", "BA", "LUV"]
    context = {"stocks" : [[stock] for stock in stocks]}
    stock_info = pd.read_csv("data/sp500_info.csv")
    for i, stock in enumerate(context["stocks"]):
        context["stocks"][i] += [stock_info.loc[stock_info["Symbol"] == context["stocks"][i][0]]["GICS Sector"].values[0]]

    return render_template("diversification.html", context=context)

@sock.route('/diversification-ws')
def diversification_socket(ws):
    while True:
        message = ws.receive()
        stocks = ["MSFT", "RCL", "DIS", "PG", "AAPL", "MMM", "AXP", "BA", "LUV"]
        weights_personal = [int(val) for val in message.split(",")[:-1]]
        print(weights_personal)
        stocks_selected = [stocks[i] for i, weight in enumerate(weights_personal) if weight > 0]
        weights_personal = [weight/100 for weight in weights_personal if weight > 0]
 
        compute_efficient_weights(stocks_selected)
        print(pd.read_csv("data/stocks_hist.csv", index_col=0)[stocks_selected])
        stock_hist = pd.read_csv("data/stocks_hist.csv", index_col=0)[stocks_selected].pct_change().dropna()
        
        weights_eff = pd.read_csv("data/weights.csv", index_col=0, header=None)[1].values.tolist()
        print("efficient", weights_eff)
        print("personal", weights_personal)
        personal_pf = pd.DataFrame()
        eff_pf = pd.DataFrame()

        for col in stock_hist.columns:
            print('i')
            personal_pf[col] = stock_hist[col] * weights_personal[stocks_selected.index(col)]
            eff_pf[col] = stock_hist[col] * weights_eff[stocks_selected.index(col)]
            print("e")
        
        personal_pf = personal_pf.sum(axis=1)
        #rename column to personal_pf
        personal_pf.columns = ["personal_pf"]

        eff_pf = eff_pf.sum(axis=1)
        #rename column to eff_pf
        eff_pf.columns = ["eff_pf"]

        print(pd.read_csv("data/sp500_value.csv", index_col=0).dtypes)
        sp500 = pd.read_csv("data/sp500_value.csv", index_col=0).pct_change().dropna().cumsum()
        print(sp500)

        personal_pf = personal_pf.cumsum()
        personal_pf.index = pd.to_datetime(personal_pf.index)
        eff_pf.index = pd.to_datetime(eff_pf.index)
        
        sp500.index = pd.to_datetime([val[:10] for val in sp500.index])
        print(personal_pf)
        eff_pf = eff_pf.cumsum()

        val = pd.concat([sp500, personal_pf, eff_pf], axis=1).dropna()
        print(val)
        dates = val.index.tolist()
        dates = [date.strftime("%Y-%m-%d") for date in dates]
        sp500 = val["SP500"].values.tolist()
        personal_pf = val[0].values.tolist()
        eff_pf = val[1].values.tolist()

        context = json.dumps({
            "weights-personal": weights_personal, 
            "weights-eff": weights_eff, 
            "stocks": stocks_selected,
            "dates": dates,
            "sp500": sp500, 
            "personal-pf": personal_pf, 
            "eff-pf": eff_pf
            })

        ws.send(context)

@app.route("/tutorial-compounding")
def compound():
    data = [1,2, 4, 3, 4, 2]
    context = {'title': "finance cookbook"}
    return render_template("compounding.html", context=context, data=data)

# rename this for compounding
@sock.route('/compound-ws')
def compound_socket(ws):
    while True:
        message = ws.receive()
        message = [int(val) for val in message.split(",")]
        ts_compounding = compound_df(message[1], message[0]/100, 30,  message[2]).to_json(orient='index')
        ws.send(ts_compounding)


@app.route("/about-us")
def about():
    return render_template("aboutus.html")