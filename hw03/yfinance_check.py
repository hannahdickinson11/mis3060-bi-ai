import yfinance as yf

t = yf.Ticker("AAPL")
inc = t.quarterly_income_stmt
print(inc.loc[["Total Revenue", "Net Income"]] / 1_000_000)  # in $ millions
