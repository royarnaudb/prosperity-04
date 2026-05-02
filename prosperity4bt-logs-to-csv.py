import re
import csv
import json

input_file = "print.log"
lambda_output = "trader-metadata/bt_lambda_logs.csv"
market_output = "trader-metadata/bt_market_data.csv"
trades_output = "trader-metadata/bt_trades.csv"

# Regex to capture lambdaLog values
lambda_pattern = re.compile(r'"lambdaLog":\s*"([^"]+)"[\s\S]*?"timestamp":\s*(\d+)')

# Detect lines that look like your semicolon data (start with digit;digit;...)
market_pattern = re.compile(r'^\d+;\d+;')

# Regex to capture trade objects
trade_pattern = re.compile(r'Trade History:\s*(\[[\s\S]*?\])')

lambda_rows = []
market_rows = []
trades = []

with open(input_file, "r") as f:
    content = f.read()
    f.seek(0)
    
    for line in f:
        line = line.strip()
        match = market_pattern.search(line)
        if match:
            market_rows.append(line.split(";"))
    
    matches = lambda_pattern.findall(content)
    
    for lambda_str, ts in matches:
        values = lambda_str.split(",")
        values.append(ts)  # add timestamp as last column
        lambda_rows.append(values)
    
    match = re.search(trade_pattern, content)
    
    trade_block = match.group(1)
    # --- Remove trailing commas safely ---
    trade_block = re.sub(r',(\s*})', r'\1', trade_block) # Case 1: comma before closing brace
    trade_block = re.sub(r',(\s*\])', r'\1', trade_block) # Case 2: comma before closing bracket

    trades = json.loads(trade_block)

# Write to CSV
with open(lambda_output, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["best_bid","best_ask","mid_price","res_price","micro_price","volatility","sig","event","timestamp"])
    writer.writerows(lambda_rows)

# --- Write market CSV ---
with open(market_output, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["day","timestamp","product","bid_price_1","bid_volume_1","bid_price_2","bid_volume_2","bid_price_3","bid_volume_3","ask_price_1","ask_volume_1","ask_price_2","ask_volume_2","ask_price_3","ask_volume_3","mid_price","profit_and_loss"])
    writer.writerows(market_rows)

with open(trades_output, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
    writer.writeheader()
    writer.writerows(trades)

print("CSV files created")