import os, datetime, requests, re
import pandas as pd
from bs4 import BeautifulSoup
from pymongo import MongoClient
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ----------------------
# Step 0: Setup and Inputs
# ----------------------
bse_stock_list = pd.read_csv('bse.csv')

st.title("Peer Fundamentals from MongoDB & Screener")
base_ticker = st.text_input("Enter the base stock ticker for peers (e.g., ALKEM)")
user_date = st.date_input("Enter the date for which data is required", datetime.date(2023, 1, 1))
user_date_str = user_date.strftime("%Y-%m-%d")
st.write("User date:", user_date_str)

# ----------------------
# Button to trigger the main process
# ----------------------
button = st.button("Get Analysis")
if button:
    # ----------------------
    # Step 1: Connect to MongoDB and retrieve base stock data
    # ----------------------
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI)
    db = client["SCREENER_DB"]
    collection = db[base_ticker]  # assumes one collection per stock

    try:
        query_date = datetime.datetime.strptime(user_date_str, "%Y-%m-%d")
    except ValueError:
        st.write("Error parsing date. Please use YYYY-MM-DD format.")
        st.stop()

    doc_fund = collection.find_one({"STOCK": base_ticker, "report": False, "DateTime": query_date})
    doc_reports = collection.find_one({"STOCK": base_ticker, "report": True})
    if not doc_reports:
        st.write("No 'report:true' document found for", base_ticker)
        st.stop()

    # Build the ratios dictionary from doc_fund
    ratios_dict = {}
    if "company_ratios" in doc_fund:
        cr = doc_fund["company_ratios"]
        if "top_ratios" in cr:
            for k, v in cr["top_ratios"].items():
                ratios_dict[k] = str(v)
        if "quick_ratios" in cr:
            for k, v in cr["quick_ratios"].items():
                ratios_dict[k] = str(v)
    else:
        st.write("Fundamental ratios not found in document.")
        st.stop()

    price = ratios_dict.get("Current Price", "N/A")

    # ----------------------
    # Step 2: Scrape Peer Data from Screener using company_id
    # ----------------------
    company_id = doc_reports.get("company_id")
    if not company_id:
        st.write("Company ID not found in doc_reports.")
        st.stop()

    sess = requests.Session()
    peer_response = sess.get(url=f"https://www.screener.in/api/company/{company_id}/peers/")
    peer_data_html = peer_response.content
    sess.close()

    peer_table_html = BeautifulSoup(peer_data_html, "html.parser").table

    def getPeers(peer_data: BeautifulSoup) -> pd.DataFrame:
        headers = [re.sub(r"\s+", " ", th.text.strip()) for th in peer_data.find_all('th')]
        rows = []
        for tr in peer_data.find_all("tr"):
            cells = tr.find_all("td")
            if cells:
                row = [cell.text.strip() for cell in cells]
                rows.append(row)
        df = pd.DataFrame(rows, columns=headers)
        return df

    peer_df = getPeers(peer_table_html)
    st.write("Scraped Peer Data:")
    st.table(peer_df)

    if "Name" not in peer_df.columns:
        st.write("No 'Name' column found in peer data.")
        st.stop()

    # Get the top 5 company names from the peer data
    top5_names = peer_df["Name"].head(5).tolist()
    st.write("Top 5 peer companies:", top5_names)

    # ----------------------
    # Step 3: Lookup NSE tickers from bse.csv and get fundamentals from MongoDB for each peer
    # ----------------------
    peer_info_list = []
    for comp in top5_names:
        match = bse_stock_list[bse_stock_list["Issuer Name"].str.contains(comp, case=False, na=False)]
        if not match.empty:
            nse_ticker = match.iloc[0]["Security Id"]
        else:
            nse_ticker = "N/A"
        peer_info_list.append({"Company Name": comp, "NSE Ticker": nse_ticker})

    st.write("Peer Info with NSE Tickers:")
    peer_info_df = pd.DataFrame(peer_info_list)
    st.table(peer_info_df)

    peer_fundamentals = []
    for info in peer_info_list:
        nse = info["NSE Ticker"]
        if nse == "N/A":
            continue
        doc_ratios = collection.find_one({"STOCK": nse, "report": False, "DateTime": query_date})
        if doc_ratios and "company_ratios" in doc_ratios:
            top_ratios = doc_ratios["company_ratios"].get("top_ratios", {})
            current_price = top_ratios.get("Current Price", "N/A")
            pe_value = top_ratios.get("Price to Earning", "N/A")
            roe_value = top_ratios.get("ROE", top_ratios.get("ROE %", "N/A"))
        else:
            current_price = "N/A"
            pe_value = "N/A"
            roe_value = "N/A"
        peer_fundamentals.append({
            "Company Name": info["Company Name"],
            "NSE Ticker": nse,
            "Current Price": current_price,
            "P/E": pe_value,
            "ROE": roe_value
        })

    final_peer_df = pd.DataFrame(peer_fundamentals)
    st.write("Final Peer Fundamental Data:")
    st.table(final_peer_df)

    # ----------------------
    # Step 4: (Optional) Continue with your PDF generation process using ratios_dict and concall PDF
    # ----------------------
    st.write("Current Price from ratios:", price)
    st.write("All data fetched. Proceeding with further processing (e.g., PDF generation)...")
    
    # (Insert your existing PDF generation code here)
