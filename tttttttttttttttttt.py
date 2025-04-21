import pandas as pd

# read and set index in one go
df = pd.read_csv("financial_metrics.csv", index_col="Aspect")

# remove stray spaces from both column names and index
df.columns = df.columns.str.strip()
df.index   = df.index.str.strip()

# now fetch the text you want
comment = df.at["Revenue", "Commentary"]   # same as df.loc["Revenue", "Commentary"]
print(comment)