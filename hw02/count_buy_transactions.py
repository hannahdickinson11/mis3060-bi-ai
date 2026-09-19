import csv

with open("data/raw/fact_transactions.csv", newline="") as f:
    reader = csv.DictReader(f)
    buy_count = sum(1 for row in reader if row["txn_type"] == "Buy")

print(f"Number of 'Buy' transactions: {buy_count}")
