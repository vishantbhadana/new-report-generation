import pandas as pd
import os
from pymongo import MongoClient
import datetime
ticker = 'CHOLAFIN'
bse_stock_listt = pd.read_csv('bse.csv')
ticker_isubgroup = bse_stock_listt[bse_stock_listt['Security Id'] == ticker]['ISubgroup Name'].iloc[0]
print(ticker_isubgroup)
peer_tickers = bse_stock_listt[bse_stock_listt['ISubgroup Name'] == ticker_isubgroup]['Security Id'].tolist()
print(peer_tickers)

if ticker in peer_tickers:
    peer_tickers.remove(ticker)
print(peer_tickers)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["SCREENER_DB"]

user_date_str = '2025-04-11'
market_cap_data = []
query_date = datetime.datetime.strptime(user_date_str, "%Y-%m-%d")


for peer_ticker in peer_tickers:
    collection = db[peer_ticker]
    doc = collection.find_one({
        "STOCK": peer_ticker,
        "report": False,
        "DateTime": query_date
    })
    if doc and "company_ratios" in doc and "top_ratios" in doc["company_ratios"]:
        market_cap = doc["company_ratios"]["top_ratios"].get("Market Cap", None)
        if market_cap:
            try:
                market_cap = float(str(market_cap).replace(',', ''))  # Convert to float, remove commas
                market_cap_data.append({"Ticker": peer_ticker, "Market Cap": market_cap})
            except (ValueError, TypeError):
                continue  # Skip if market cap is not a valid number

# Create DataFrame and sort by Market Cap
market_cap_df = pd.DataFrame(market_cap_data)
if market_cap_df.empty:
    print(f"No valid market cap data found for peers of {ticker}.")
    peerTable = pd.DataFrame(columns=['Name', 'Mar Cap (Rs. Cr.)', 'P/E', 'ROE', 'Sales(G) QoQ', 'Sales(G) QYoY', 'PAT(G) QoQ', 'PAT(G) QYoY'])
else:
    market_cap_df = market_cap_df.sort_values(by='Market Cap', ascending=False)
    top_peers = market_cap_df['Ticker'].head(5).tolist()

    # Fetch ratios for the selected peers
    peer_data_list = []
    for peer_ticker in top_peers:
        collection = db[peer_ticker]
        doc = collection.find_one({
            "STOCK": peer_ticker,
            "report": False,
            "DateTime": query_date
        })
        issuer_name = bse_stock_listt[bse_stock_listt['Security Id'] == peer_ticker]['Issuer Name'].iloc[0]
        
        if doc and "company_ratios" in doc:
            cr = doc["company_ratios"]
            top_ratios = cr.get("top_ratios", {})
            quick_ratios = cr.get("quick_ratios", {})

            # Use fallback keys to handle variations in document structure
            market_cap = str(top_ratios.get("Market Cap", top_ratios.get("Mar Cap", ""))).replace(',', '')
            pe_ratio = str(top_ratios.get("Price to Earning", top_ratios.get("Stock P/E", "")))
            roe = str(top_ratios.get("Return on equity", top_ratios.get("ROE", "")))
            sales_growth_qoq = str(quick_ratios.get("Sales Growth QoQ", ""))
            sales_growth_qyoy = str(quick_ratios.get("Qtr Sales Var", quick_ratios.get("Sales(G) QYoY", "")))
            pat_growth_qoq = str(quick_ratios.get("PAT Growth QoQ", quick_ratios.get("QoQ Profits", "")))
            pat_growth_qyoy = str(quick_ratios.get("PAT Growth QYoY", quick_ratios.get("Qtr Profit Var", "")))

            peer_info = {
                "Name": issuer_name,
                "Mar Cap (Rs. Cr.)": market_cap if market_cap else "",
                "P/E": pe_ratio if pe_ratio else "",
                "ROE": roe + "%" if roe else "",
                "Sales(G) QoQ": sales_growth_qoq + "%" if sales_growth_qoq else "",
                "Sales(G) QYoY": sales_growth_qyoy + "%" if sales_growth_qyoy else "",
                "PAT(G) QoQ": pat_growth_qoq + "%" if pat_growth_qoq else "",
                "PAT(G) QYoY": pat_growth_qyoy + "%" if pat_growth_qyoy else ""
            }
            peer_data_list.append(peer_info)
        else:
            peer_data_list.append({
                "Name": issuer_name,
                "Mar Cap (Rs. Cr.)": "",
                "P/E": "",
                "ROE": "",
                "Sales(G) QoQ": "",
                "Sales(G) QYoY": "",
                "PAT(G) QoQ": "",
                "PAT(G) QYoY": ""
            })

    # Create peer table DataFrame
    peerTable = pd.DataFrame(peer_data_list)
    if peerTable.empty:
        peerTable = pd.DataFrame(columns=['Name', 'Mar Cap (Rs. Cr.)', 'P/E', 'ROE', 'Sales(G) QoQ', 'Sales(G) QYoY', 'PAT(G) QoQ', 'PAT(G) QYoY'])

# Ensure the table has at least 5 rows
while len(peerTable) < 5:
    peerTable = peerTable.append(pd.Series([''] * len(peerTable.columns), index=peerTable.columns), ignore_index=True)

# Select only the required columns
peerTable = peerTable[['Name', 'Mar Cap (Rs. Cr.)', 'P/E', 'ROE', 'Sales(G) QoQ', 'Sales(G) QYoY', 'PAT(G) QoQ', 'PAT(G) QYoY']]
peerTable = peerTable.head(6)  # Limit to 6 rows for consistency

# Debug: Print peerTable to verify data
print(peerTable)