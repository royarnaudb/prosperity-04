import json
import csv

with open("imc_backtests/507446/507446.log") as f:
    data = json.load(f)
rows = []

for entry in data['logs']:
    if "lambdaLog" in entry:
        values = entry["lambdaLog"].split(",") # keep timestamp!
        values.append(entry["timestamp"])
        rows.append(values)

with open("trader-metadata/imc_lambda_logs.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "best_bid","best_ask","mid_price","res_price","micro_price","volatility","my_bid","my_ask","timestamp"
    ])
    writer.writerows(rows)

trades = data.get("tradeHistory", [])

with open("trader-metadata/imc_trades.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
    writer.writeheader()
    writer.writerows(trades)