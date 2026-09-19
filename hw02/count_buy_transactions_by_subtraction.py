import csv

known_types = {"Sell", "Deposit", "Withdrawal", "Dividend", "Advisory Fee"}

with open("data/raw/fact_transactions.csv", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total_count = len(rows)
known_count = sum(1 for row in rows if row["txn_type"] in known_types)
buy_count = total_count - known_count

print(f"Total transactions: {total_count}")
print(f"Non-Buy known-type transactions: {known_count}")
print(f"Number of 'Buy' transactions: {buy_count}")
