from my_kite_ticker import MyKiteTicker
from selenium import webdriver
import os,time
import login
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import pandas as pd
from reportlab.lib.pagesizes import letter,A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
import requests
from kiteconnect import KiteConnect, KiteTicker
from bs4 import BeautifulSoup
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
from reportlab.platypus import Image
from openai import OpenAI
import re
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from dotenv import load_dotenv
# import yfinance as yf
import streamlit as st
from PyPDF2 import PdfReader,PdfWriter
# NEW: import PyMongo to connect to your MongoDB
from pymongo import MongoClient
load_dotenv()

#read bse stock list
bse_stock_list = pd.read_csv('bse.csv')

# # Streamlit interface
# st.title('Stock Analysis')
# st.write('Enter the stock ticker to get the analysis')
# ticker = st.text_input('Enter the stock ticker')


########################################################
# ADD A DATE INPUT FOR USER
########################################################
# user_date = st.date_input(
#     "Enter the date for which data is required",
#     datetime.date(2023, 1, 1)
# )
# date = user_date.strftime("%d-%b-%Y")
# user_date_str = user_date.strftime("%Y-%m-%d")
# print(f"User date as string: {user_date_str}")

# # Connect to Zerodha Kite only once
# if 'kite' not in st.session_state:
#     st.write('Connecting to Zerodha Kite')
#     user_name = os.getenv("user_name")
#     password = os.getenv("password")
#     totp = os.getenv("totp")
#     api_key = os.getenv("api_key")
#     api_secret = os.getenv("api_secret")

#     kite = KiteConnect(api_key=api_key)
#     request_token = login.kiteLogin(user_name, password, totp, api_key)
#     data = kite.generate_session(request_token, api_secret)
#     kite.set_access_token(data["access_token"])

#     instrument_dump = kite.instruments()  # Get instruments dump from NSE
#     instrument_df = pd.DataFrame(instrument_dump)  # Dump it to a dataframe

#     st.session_state.kite = kite
#     st.session_state.instrument_df = instrument_df

#     st.write('Connected to Zerodha Kite')

# # Add a button to get the analysis
# button = st.button('Get Analysis')

# if button:
#     kite = st.session_state.kite
#     instrument_df = st.session_state.instrument_df

#     #check if ticker is present in the instrument list
#     if ticker not in instrument_df['tradingsymbol'].values:
#         st.write('Invalid ticker. Please enter a valid ticker.')
#         st.stop()

def get_analyst_viewpoint(ticker, user_date_str, kite, instrument_df, date):
    st.write(f"Starting analysis for {ticker} on {user_date_str}")
    # Example: Check ticker exists in instrument_df
    if ticker not in instrument_df['tradingsymbol'].values:
        st.write(f"Ticker {ticker} not found in instruments.")
        return "Invalid ticker"

    # Fetch the fundamental data
    st.write('Fetching Fundamental Data')
    st.write('Please wait...')
    st.write('Connecting to database....')
    downloads_dir = os.path.join(os.getcwd(),'downloads')
    save_path = os.path.join(downloads_dir, f"{ticker}_concall.pdf")
    balance_dir = os.path.join(os.getcwd(),'balance')
    fonts_dir = os.path.join(os.getcwd(),"fonts")

    os.makedirs(downloads_dir,exist_ok=True)
    os.makedirs(balance_dir,exist_ok=True)


    print(f'Downloads dir: {downloads_dir}')
    print(f'Balance dir: {balance_dir}')

    screener_id = os.getenv("id")
    screener_pass = os.getenv("password_screener")
    api_key = os.getenv("apiKey")

    # Starting chrome in headless mode and saving page source
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    log_path = os.path.join(os.getcwd(), "chromedriver.log")
    service = webdriver.ChromeService(log_output=log_path)

    driver = webdriver.Chrome(service=service, options=options)

    print('Fetching Data Screener.in')
    driver.get("https://www.screener.in/login")

    # time.sleep(1)
    try:
        login = WebDriverWait(driver,5).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/main/div[2]/div[2]/form/button'))
        )
    except TimeoutException:
        print("login button not loaded")

    email=driver.find_element(By.XPATH, '//*[@id="id_username"]')
    email.send_keys(screener_id)
    password=driver.find_element(By.XPATH, '//*[@id="id_password"]')
    password.send_keys(screener_pass)
    login=driver.find_element(By.XPATH, '/html/body/main/div[2]/div[2]/form/button')
    login.click()
    time.sleep(3)
    # st.write('Logged in to Screener.in')
    print("Cookies:", driver.get_cookies())
    session_id = driver.get_cookie("sessionid")['value']
    csrf_token = driver.get_cookie("csrftoken")['value']

    cookies = {'sessionid':session_id,"csrftoken":csrf_token}

    address=f"https://www.screener.in/company/{ticker}/"


    MONGO_URI = os.getenv("MONGO_URI")  # or any other approach for your MongoDB URI
    client = MongoClient(MONGO_URI)
    db = client["SCREENER_DB"]
    collection = db[ticker]

    try:
        query_date = datetime.datetime.strptime(user_date_str, "%Y-%m-%d")
        print(f"Query date as datetime: {query_date}")
    except ValueError:
        st.write("Error parsing the date. Please ensure the date is in YYYY-MM-DD format.")
        st.stop()
    query = {
        "STOCK": ticker,
        "report": False,
        "DateTime": query_date
    }
    doc = collection.find_one(query)




    if doc:
        st.write("Document found:", doc)
    else:
        st.write("No document found for that date.")
 
   

    




    

    ratios_dict = {}

    if "company_ratios" in doc:
        cr = doc["company_ratios"]
        if "top_ratios" in cr:
            for k, v in cr["top_ratios"].items():
                ratios_dict[k] = str(v)
        if "quick_ratios" in cr:
            for k, v in cr["quick_ratios"].items():
                ratios_dict[k] = str(v)
    else:
        st.write("Ratios not found in the document.")
        st.stop()


    
    

    #display the ratios in a table format of six columns with three ratios in each row
    ratios_df = pd.DataFrame(ratios_dict.items(), columns=['Ratios', 'Values'])
    ratios_df = ratios_df.set_index('Ratios')
    ratios_df = ratios_df.sort_index()
    ratios_df = ratios_df.replace(',', '', regex=True)
    ratios_df = ratios_df.T


    if "longName" not in ratios_dict:
        ratios_dict["longName"] = ticker
    if "shortName" not in ratios_dict:
        ratios_dict["shortName"] = ticker
    if "longBusinessSummary" not in ratios_dict:
        ratios_dict["longBusinessSummary"] = "Summary from Screener..."

    
    stock = MyKiteTicker(
        symbol=ticker + ".NS",
        kite=kite,
        instrument_df=instrument_df,
        info_dict=ratios_dict
    )
    stock_info = stock.info



    # Display the ratios on Streamlit in a table format of six columns with three ratios in each row
    st.header('Fundamentals')
    num_columns = 6
    num_rows = (len(ratios_df.columns) + num_columns - 1) // num_columns

    # Create a new DataFrame to format the table
    formatted_ratios = pd.DataFrame(index=range(num_rows), columns=range(num_columns))

    for i, (ratio, value) in enumerate(ratios_df.items()):
        row = i // num_columns
        col = i % num_columns
        formatted_ratios.iloc[row, col] = f"{ratio}: {value.values[0]}"

    st.table(formatted_ratios)

    doc_reports = collection.find_one({
        "STOCK": ticker,
        "report": True
    })
    
    concalls = doc_reports.get("Concalls", [])
    if not concalls:
        st.write("No concalls in this 'report: true' doc.")

    user_dt = datetime.datetime(
    user_date.year,
    user_date.month,
    user_date.day
    )

    def parse_month_year(mystring):
        # e.g. "Mar 2025," or "Feb 2025" => "Mar 2025"
        mystring = mystring.strip().rstrip(',')
        # Now parse as month abbreviations + year:
        # "%b %Y" matches patterns like "Mar 2025"
        return datetime.datetime.strptime(mystring, "%b %Y")
    
    valid_concalls = []
    for c in concalls:
        mystr = c.get("month_year", "").strip()
        if not mystr:
            continue
        try:
            dt = parse_month_year(mystr)
        except ValueError:
            # skip if parsing fails
            continue

        # Keep only those whose date is <= the user date
        if dt <= user_dt:
            valid_concalls.append((dt, c))

    if not valid_concalls:
        st.write("No concall found on or before that user date.")
    else:
        valid_concalls.sort(key=lambda x: x[0])  # sort ascending
        latest_dt, latest_concall = valid_concalls[-1]

        links = latest_concall.get("links", [])
        transcript_url = None
        ppt_url = None
        for link in links:
            text_lower = link["text"].lower().strip()
            if text_lower.startswith("transcript"):
                transcript_url = link["url"]
            elif text_lower.startswith("ppt"):
                ppt_url = link["url"]
                

        chosen_url = transcript_url or ppt_url
        if not chosen_url:
            st.write("No transcript or PPT link in that latest concall.")
        

        st.write("Found concall link:", chosen_url)

        import subprocess

        def download_concall_file(chosen_url, ticker):
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            save_path = os.path.join(downloads_dir, f"{ticker}_concall.pdf")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.bseindia.com'
            }

            try:
                print("🔄 Trying download with requests...")
                with requests.Session() as session:
                    response = session.get(chosen_url, headers=headers, stream=True, allow_redirects=True, verify=False)
                    final_url = response.url
                    content_type = response.headers.get("Content-Type", "")

                    print(f"🔍 Final URL: {final_url}")
                    print(f"📎 Content-Type: {content_type}")

                    if response.status_code == 200 and "application/pdf" in content_type:
                        with open(save_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"✅ File successfully downloaded using requests at: {save_path}")
                        return save_path
                    else:
                        print("⚠️ requests worked, but response is not PDF. Falling back to wget...")
                        raise Exception("Invalid content type")

            except Exception as e:
                print(f"❌ Requests failed: {e}")
                print("🔄 Trying download with wget...")

                try:
                    result = subprocess.run(
                        ['wget', '-O', save_path, '--no-check-certificate', chosen_url],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print("✅ File successfully downloaded using wget")
                    return save_path
                except subprocess.CalledProcessError as we:
                    print("❌ wget also failed:", we.stderr)
                    return None
        save_path = download_concall_file(chosen_url, ticker)
        if save_path:
            st.write("✅ Concall downloaded successfully:", save_path)
        else:
            st.write("❌ Failed to download the concall transcript.")


    price = ratios_dict.get("Current Price", "N/A")
    sess = requests.Session()

    headers = {
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"'
    }
    company_id = doc_reports.get("company_id")

    # Function to download a file and save it


    
    peer_data = sess.get(url=f"https://www.screener.in/api/company/{company_id}/peers/",cookies=cookies).content
    peer_data = BeautifulSoup(peer_data).table

    sess.close()

    def getPeers(peer_data:BeautifulSoup)->pd.DataFrame:
        headers = [re.sub(r"\s+"," ",th.text.strip())for th in peer_data.find_all('th')]
        rows = []
        for tr in peer_data.find_all("tr"):
            cells = tr.find_all("td")
            row = [cell.text.strip() for cell in cells]
            rows.append(row)
        df = pd.DataFrame(rows,columns=headers)
        return df

    peerTable = getPeers(peer_data)
    print(peerTable.columns)
    peerTable = peerTable.drop(['S.No.'],axis=1).rename(columns={'Mar Cap Rs.Cr.':'Mar Cap (Rs. Cr.)'})
    #keep 'Mar Cap (Rs. Cr.)','Price','Price to Earning','ROE %','ROA 12M %','ROCE %','EPS Growth QoQ' only
    peerTable = peerTable[['Name','Mar Cap (Rs. Cr.)','P/E','ROE %','Sales Growth QoQ %','Qtr Sales Var %','PAT Growth QoQ %','PAT Growth QYoY %']]
    #change name of sales var qtr to sales growth qoq
    peerTable = peerTable.rename(columns={'Qtr Sales Var %':'Sales(G) QYoY'})
    peerTable = peerTable.rename(columns={'Sales Growth QoQ %':'Sales(G) QoQ'})
    peerTable = peerTable.rename(columns={'PAT Growth QoQ %':'PAT(G) QoQ'})
    peerTable = peerTable.rename(columns={'PAT Growth QYoY %':'PAT(G) QYoY'})
    peerTable = peerTable.rename(columns={'ROE %':'ROE'})

    # Add percentage sign to specific columns
    columns_to_update = ['ROE', 'Sales(G) QoQ', 'Sales(G) QYoY', 'PAT(G) QoQ', 'PAT(G) QYoY']
    for column in columns_to_update:
        peerTable[column] = peerTable[column].fillna('').apply(lambda x: x + '%' if x != '' else x)
    #remove last row
    peerTable = peerTable[:-1]

    #remove first row
    peerTable = peerTable[1:]
    print(peerTable)

    #sort by market cap
    peerTable = peerTable.sort_values(by='Mar Cap (Rs. Cr.)',ascending=False)
    peerTable = peerTable.reset_index(drop=True)
    #select first 5 rows
    peerTable = peerTable.head(6)
    peerTable

    hex_color = '#201c64'
    background_color = HexColor(hex_color)

    # Data to be stored in the table
    data = [list(peerTable.columns)]
    for i in range(min(5, len(peerTable))):
        data.append(list(peerTable.loc[i]))

    # Add empty rows if there are less than 5 rows
    while len(data) < 6:
        data.append([''] * len(peerTable.columns))

    peerTablePdf = Table(data,rowHeights= [19] + [22] * (len(data) - 1), colWidths=[1.4* inch, 1.1* inch, 0.5* inch, 0.6* inch, 1* inch,1* inch, 1.0* inch,1.*inch])


    peerTablePdf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), background_color),
        ('TEXTCOLOR', (0, 0), (-1,0), colors.white),
        ('TEXTCOLOR', (0, 1), (0,-1), background_color),
        ('FONTNAME', (0, 0), (-1,0),'Seaford-Bold' ),
        ('FONTNAME', (0, 1), (0, -1), 'Seaford-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (1, 1), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.2, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.2, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))


    

    df=pd.DataFrame(ratios_dict.items(), columns=['Ratios', 'Values'])
    df = df.set_index('Ratios')
    df = df.sort_index()
    df = df.replace(',', '', regex=True)



    #calculated values
    sales_growth_qoq = ''
    if 'Sales Qtr' in df.index and 'Sales Prev Qtr' in df.index:
        try:
            sales_growth_qoq_value = (float(df.loc['Sales Qtr'][0]) - float(df.loc['Sales Prev Qtr'][0])) * 100 / abs(float(df.loc['Sales Prev Qtr'][0]))
            sales_growth_qoq = f"{round(sales_growth_qoq_value, 2)} %"
        except (ValueError, ZeroDivisionError):
            sales_growth_qoq = ''
    
    eps_growth_qoq = ''
    if 'EPS latest quarter' in ratios_dict and 'EPS Prev Qtr' in ratios_dict:
        try:
            eps_growth_qoq = (float(ratios_dict['EPS latest quarter']) - float(ratios_dict['EPS Prev Qtr'])) * 100 / abs(float(ratios_dict['EPS Prev Qtr']))
            eps_growth_qoq = f"{round(eps_growth_qoq, 2)} %"
        except (ValueError, ZeroDivisionError):
            eps_growth_qoq = ''  # Default to empty string if conversion fails or division by zero occurs
    
    eps_growth_yoy = ''
    if 'EPS' in ratios_dict and 'EPS last year' in ratios_dict:
        try:
            eps_growth_yoy_value = (float(ratios_dict['EPS']) - float(ratios_dict['EPS last year'])) * 100 / abs(float(ratios_dict['EPS last year']))
            eps_growth_yoy = f"{round(eps_growth_yoy_value, 2)} %"
        except (ValueError, ZeroDivisionError):
            eps_growth_yoy = ''
    
    
    font_path = os.path.join(fonts_dir,'SeafordRg.ttf')


    # Register the font with a name you can refer to in your PDFs
    pdfmetrics.registerFont(TTFont('Seaford-Regular', font_path))
    font_path = os.path.join(fonts_dir,'SeafordBold.ttf')
    pdfmetrics.registerFont(TTFont('Seaford-Bold', font_path))

    styles = getSampleStyleSheet()
    # Page dimensions
    hex_color = '#201c64'
    background_color = HexColor(hex_color)
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('capitalallocation.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    data = [['Capital Allocation', ''],  # Header row
            ['RoE', f"{df.loc['Return on equity'][0] if 'Return on equity' in df.index else ''} %"],
            ['RoA', f"{df.loc['Return on assets'][0] if 'Return on assets' in df.index else ''} %"],
            ['RoCE', f"{df.loc['ROCE'][0] if 'ROCE' in df.index else ''} %"],
            ['RoIC', f"{df.loc['ROIC'][0] if 'ROIC' in df.index else ''} %"],
            ['', '']]
    c_width=[1.6*inch,1*inch]
    c= Table(data,rowHeights = 0.19*inch ,colWidths=c_width)
    c.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                        ('BACKGROUND',(0,0),(-1,0),background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font size for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    # Setting up the styles
    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('growthquaterly.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    sales_growth_qyoy = ''
    if 'Sales Qtr' in df.index and 'Sales PY Qtr' in df.index:
        try:
            sales_growth_qyoy_value = (float(df.loc['Sales Qtr'][0]) - float(df.loc['Sales PY Qtr'][0])) * 100 / float(df.loc['Sales PY Qtr'][0])
            sales_growth_qyoy = f"{round(sales_growth_qyoy_value, 2)} %"
        except (ValueError, ZeroDivisionError):
            sales_growth_qyoy = ''
    
    pat_qoq = ''
    if 'PAT Qtr' in df.index and 'PAT Prev Qtr' in df.index:
        try:
            pat_qoq_value = (float(df.loc['PAT Qtr'][0]) - float(df.loc['PAT Prev Qtr'][0])) * 100 / float(df.loc['PAT Prev Qtr'][0])
            pat_qoq = f"{round(pat_qoq_value, 2)} %"
        except (ValueError, ZeroDivisionError):
            pat_qoq = ''
   
    pat_qyoy = ''
    if 'PAT Qtr' in df.index and 'PAT PY Qtr' in df.index:
        try:
            pat_qyoy_value = (float(df.loc['PAT Qtr'][0]) - float(df.loc['PAT PY Qtr'][0])) * 100 / float(df.loc['PAT PY Qtr'][0])
            pat_qyoy = f"{round(pat_qyoy_value, 2)} %"
        except (ValueError, ZeroDivisionError):
            pat_qyoy = ''
    
    data = [['Growth(QoQ)',''],	
            ['Sales Growth',f"{sales_growth_qoq} %"],
            ['Sales Growth QYoY',f"{sales_growth_qyoy} %"],
            ['PAT Growth',f"{pat_qoq} %"],
            ['PAT Growth QYoY',f"{pat_qyoy} %"]
            ]
    c_width=[1.6*inch,1*inch]
    gq= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    gq.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                            ('BACKGROUND',(0,0),(-1,0),background_color),
                            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('growthtable.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    pat_yoy = ''
    if 'PAT Ann' in df.index and 'PAT Prev Ann' in df.index:
        try:
            pat_yoy = (float(df.loc['PAT Ann'][0]) - float(df.loc['PAT Prev Ann'][0])) * 100 / float(df.loc['PAT Prev Ann'][0])
            pat_yoy = f"{round(pat_yoy, 2)} %"
        except (ValueError, ZeroDivisionError):
            pat_yoy = ''  # Default to empty string if conversion fails or division by zero occurs
    data = [['Growth(YoY)', ''],  # Header row
            ['Sales Growth', f"{df.loc['Sales growth'][0] if 'Sales growth' in df.index else ''} %"],
            ['PAT Growth', pat_yoy],  # pat_yoy already includes % if calculated
            ['EPS Growth', eps_growth_yoy],  # eps_growth_yoy already includes % if calculated
            ['Dividend Yield', f"{df.loc['Dividend Yield'][0] if 'Dividend Yield' in df.index else ''}"]]
    c_width=[1.6*inch,1*inch]
    gy = Table(data,rowHeights= 0.19*inch  ,colWidths=c_width)
    gy.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                            ('BACKGROUND',(0,0),(-1,0),background_color),
                            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    # Setting up the styles
    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('holdings.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    data = [['Holdings', ''],  # Header row
            ['Promoter', f"{df.loc['Promoter holding'][0] if 'Promoter holding' in df.index else ''} %"],
            ['FII', f"{df.loc['FII holding'][0] if 'FII holding' in df.index else ''} %"],
            ['DII', f"{df.loc['DII holding'][0] if 'DII holding' in df.index else ''} %"],
            ['Public', f"{df.loc['Public holding'][0] if 'Public holding' in df.index else ''} %"],
            ['No of Shares', f"{df.loc['No. Eq. Shares'][0] if 'No. Eq. Shares' in df.index else ''} Cr"]]
    c_width=[1.6*inch,1*inch]
    h= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    h.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                        ('BACKGROUND',(0,0),(-1,0), background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    # Setting up the styles
    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('leverage.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    data = [['Leverage', ''],  # Header row
            ['Debt/Equity', f"{df.loc['Debt to equity'].iloc[0] if 'Debt to equity' in df.index else ''}"],
            ['Debt', f"{df.loc['Debt'][0] if 'Debt' in df.index else ''} Cr"],
            ['Market Cap', f"{df.loc['Market Cap'][0] if 'Market Cap' in df.index else ''} Cr"],
            ['Enterprise value', f"{df.loc['Enterprise Value'][0] if 'Enterprise Value' in df.index else ''} Cr"],
            ['Cash Equivalents', f"{df.loc['Cash Equivalents'][0] if 'Cash Equivalents' in df.index else ''} Cr"]]
    c_width=[1.6*inch,1*inch]
    l= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    l.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                        ('BACKGROUND',(0,0),(-1,0), background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('profitability.pdf',pagesize=letter)
    ebidta_margin = ''
    if 'EBIDT last year' in df.index and 'Sales' in df.index:
        try:
            ebidta_margin = f"{100 * float(df.loc['EBIDT last year'][0]) / float(df.loc['Sales'][0]):.2f} %"
        except (ValueError, ZeroDivisionError):
            ebidta_margin = ''

    data = [['Profitability Matrix', ''],
            ['Operating Profit Margin', f"{df.loc['OPM'][0] if 'OPM' in df.index else ''} %"],
            ['EBITDA Margin', ebidta_margin],
            ['Net Profit Margin', f"{df.loc['NPM last year'][0] if 'NPM last year' in df.index else ''} %"],
            ['EPS', f"{df.loc['EPS'][0] if 'EPS' in df.index else ''}"],
            ['', '']]
    c_width=[1.6*inch,1*inch]
    p= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    p.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                        ('BACKGROUND',(0,0),(-1,0),background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))
    
    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('valuation.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    data = [['Valuation Matrix', ''],  # Header row
            ['Trailing P/E', f"{df.loc['Price to Earning'][0] if 'Price to Earning' in df.index else ''}"],
            ['PEG Ratio', f"{df.loc['PEG Ratio'][0] if 'PEG Ratio' in df.index else ''}"],
            ['EV/EBITDA', f"{df.loc['EVEBITDA'][0] if 'EVEBITDA' in df.index else ''}"],
            ['P/B', f"{df.loc['Price to book value'][0] if 'Price to book value' in df.index else ''}"]]
    c_width=[1.6*inch,1*inch]
    v= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    v.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                        ('BACKGROUND',(0,0),(-1,0),background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('revenue.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    
    data = [['Sales'],  # Header row
        ['Current Year', f"{df.loc['Sales'][0] if 'Sales' in df.index else ''} Cr"],
        ['Previous Year', f"{df.loc['Sales Prev Ann'][0] if 'Sales Prev Ann' in df.index else ''} Cr"],
        ['Current Quarter', f"{df.loc['Sales Qtr'][0] if 'Sales Qtr' in df.index else ''} Cr"],
        ['Previous Quarter', f"{df.loc['Sales Prev Qtr'][0] if 'Sales Prev Qtr' in df.index else ''} Cr"],
        ['Revenue (QYoY)', f"{df.loc['Sales PY Qtr'][0] if 'Sales PY Qtr' in df.index else ''} Cr"]]




    
    c_width=[1.6*inch,1*inch]
    rev= Table(data,rowHeights= 0.19*inch ,colWidths=c_width)
    rev.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)),
                            ('BACKGROUND',(0,0),(-1,0), background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9),    # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('P/L.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    data = [['Profit & Loss'],
        ['Operating Profit(Year)', f"{df.loc['Operating profit'][0] if 'Operating profit' in df.index else ''} Cr"],
        ['Operating Profit(Quarter)', f"{df.loc['OP Qtr'][0] if 'OP Qtr' in df.index else ''} Cr"],
        ['PAT (Year)', f"{df.loc['PAT Ann'][0] if 'PAT Ann' in df.index else ''} Cr"],
        ['PAT (Quarter)', f"{df.loc['PAT Qtr'][0] if 'PAT Qtr' in df.index else ''} Cr"],
        ['', '']]
    c_width=[1.6*inch,1*inch]
    p_l= Table(data,rowHeights= 0.19*inch  ,colWidths=c_width)
    p_l.setStyle(TableStyle([
                            ('SPAN', (0, 0), (1, 0)),
                            ('BACKGROUND',(0,0),(-1,0), background_color),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),    # Font type for the first row
                        ('FONTNAME', (0, 1), (-1, -1), 'Seaford-Regular'),    # Font type for the first row
                        ('FONTSIZE', (0, 0), (-1, -1), 9), # Font type for the first row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))

    styles = getSampleStyleSheet()

    large_font_style = ParagraphStyle(
        'LargeFontStyle',
        parent=styles['Normal'],
        fontSize=30,
        leading=24,
        textColor=background_color,
        fontName='Seaford-Bold',
        alignment=1,
    )

    
    stockname=bse_stock_list.loc[bse_stock_list['Security Id']==ticker, 'Issuer Name'].iloc[0]


    # Add a condition when longName key is not present
    # if 'longName' in stock_info:
    #     stockname = stock_info['longName']
    # else:
    #     stockname = stock_info['shortName']

    if len(stockname) > 40:
        stockname = stock_info['shortName']
    # Create the data for the table
    Name=f"""{stockname}"""
    stockname=Paragraph(Name, large_font_style)
    isin_data=pd.read_csv('union.csv')
    isin_data.index=isin_data['TICKER']

    isinno=isin_data.loc[ticker]['ISIN']
    nseticker=ticker

    Ticker=f"""ISIN :{isinno} | NSE :{nseticker}"""
    custom_style= ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=background_color,
        alignment=1,
    )
    ticker1=Paragraph(Ticker,custom_style)

    print(stockname)


    styles = getSampleStyleSheet()
    width, height = letter 
    repdate=date
    covdate=date
    buyorsell='Buy'
    #get sector from bse stock list
    sector=bse_stock_list[bse_stock_list['Security Id']==ticker]['Sector Name'].values[0]
    industry=bse_stock_list[bse_stock_list['Security Id']==ticker]['ISubgroup Name'].values[0]
    if len(industry)>25:
        #remove words after whitespace just before 25th character
        industry=industry[:industry[:25].rfind(' ')]
        #remove '-' from industry if present at last
        industry=industry.rstrip('-')
        #remove '&' character from industry
        industry=industry.replace('&','')
    # Adjust your text to use the <font> tag for bold parts
    text = f"""<font name="Seaford-Bold">Price:</font> <font name='Seaford-Regular'>{price}</font><br/>
    <font name="Seaford-Bold">Recommendation:</font> <font name='Seaford-Regular'>{buyorsell}</font><br/>
    <font name="Seaford-Bold">Industry:</font> <font name='Seaford-Regular'>{industry}</font><br/>
    <font name="Seaford-Bold">Sector:</font> <font name='Seaford-Regular'>{sector}</font><br/>
    <font name="Seaford-Bold">Report Date:</font> <font name='Seaford-Regular'>{repdate}</font><br/>"""
    # <font name="Seaford-Bold">Coverage Date:</font> <font name='Seaford-Regular'>{covdate}</font><br/>
    # """

    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=colors.black,
        spaceAfter=0,
        alignment=0,
        fontName='Seaford-Regular'  # This is your default font for the paragraph
    )

    date = Paragraph(text, custom_style)

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('profitability.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor='#000000',
        spaceAfter=9,
        alignment=0,  
        fontname='Seaford-Regular'
    )


    # Content for the PDF

    text = stock_info['longBusinessSummary']
    about= Paragraph(text,custom_style)

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('profitability.pdf',pagesize=letter)
    # Function to create the first page
    # Create the Table with styles
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor='#000000',
        spaceAfter=9,
        alignment=0,  
        fontname='Seaford-Regular'
    )


    # Content for the PDF

    text = stock_info['longBusinessSummary']
    about= Paragraph(text,custom_style)

    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        textColor='#000000',
        spaceAfter=10,
    )

    goalfi=""" Avanti Feeds Limited showcases strong financial health with consistent revenue growth of 5.54% YoY and robust quarterly sales growth. The company's profitability metrics are commendable, highlighted by a high operating profit margin of 8.53% and a net profit margin of 7.34%. With a low debt-to-equity ratio of 0.01, Avanti demonstrates excellent financial prudence and stability, making it a secure investment. The high returns on equity, assets, and capital employed further confirm its efficient capital utilization and operational excellence. Although the Trailing P/E of 28.1 might hint at slight overvaluation, the company's consistent performance and growth prospects make it a strong buy recommendation."""
    viewpoint=f"""<b>GoaFi's viewpoint:</b> {goalfi}"""
    goalfiviewpoint=Paragraph(viewpoint,custom_style)
    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    assistant1 = client.beta.assistants.create(
        name="Financial Analyst Assistant",
        instructions="""
            You are an elite AI assistant at a top-tier financial advisory firm.
            Your task is to analyze the latest concalls of companies if a concall PDF is provided;
            otherwise, use publicly available information (website, press releases, etc.) 
            to provide insightful summaries. 
            Ensure your explanations are clear, strictly up to 2800 characters (including spaces), 
            and accessible for our clients. 
            Maintain a response temperature=0 for precise and accurate information.
        """,
        model="gpt-4o",
        tools=[{"type": "file_search"}],
        temperature=0
    )

    # Construct the PDF path and initialize message_file1
    pdf_path = f"downloads/{ticker}_concall.pdf"
    message_file1 = None

    # Check if the concall PDF exists
    if os.path.exists(pdf_path):
        # If the PDF exists, upload it (assuming client.files.upload exists) and create a thread with the file
        message_file1 = client.files.create(
        file=open(f"downloads/{ticker}_concall.pdf", "rb"), purpose="assistants"
        )
        thread1 = client.beta.threads.create(
             messages=[
        {
        "role": "user",
        "content": """
    Summarize the transcript of the last meeting provided.
    Identify and explain the new initiatives, business strategies, and diversification schemes adopted by the company.
    Try to keep the language simnilar to the original document. Add few lines exactly from the document.
    Describe the future growth and scaling perspectives of the company.
    Provide both positive and even better if views based on the transcript analysis with zero temperature.
    Highlight any specific data points or details that are of particular interest or importance.

    write this summary in 4 paragraphs with mentioning important points in exactly 2800 characters including whitespace.  follow this insructions strictly.
    do not write anything else in the message, do not mention any refrences or citations.
    Ensure your explanations are clear and accessible for our clients who rely on our financial advisory services. Maintain a response temperature=0 for precise and accurate information.
    """,
        # Attach the new file to the message.
        "attachments": [
            { "file_id": message_file1.id, "tools": [{"type": "file_search"}] }
        ],
        }
    ]
        )
        print("Concall PDF found. Thread created for PDF analysis. Thread ID:", thread1.id)
    else:
        # Fallback branch when PDF is not found
        thread1 = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": f"""
    No PDF found for {ticker}. 
    Please summarize the company's recent announcements, initiatives, and press releases from publicly available sources. 
    Identify and explain new business strategies, diversification schemes, and provide insights into future growth/scaling perspectives. 
    Offer positive observations and constructive suggestions. 
    Highlight any key data or figures that might be important.

    Write exactly 4 paragraphs, each detailing important points, in exactly 2800 characters (including spaces). 
    Do not add extra references or disclaimers.
    Ensure the summary is precise, factual, and helpful for our clients.
                    """
                }
            ]
        )
        print("No PDF found. Fallback thread created with ID:", thread1.id)

    # Optional: Check if a file was uploaded
    if message_file1 is not None:
        print("message_file1 is defined (file uploaded).")

    # Print the file search tool resource for debugging purposes
    print(thread1.tool_resources.file_search)
    print(message_file1)

    # Create a run and poll for the result
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread1.id, assistant_id=assistant1.id
    )

    # Retrieve messages from the thread run
    messages = list(client.beta.threads.messages.list(thread_id=thread1.id, run_id=run.id))

    # Process the message content, handle annotations, and prepare citations
    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")

    # Output the final message content
    print(message_content.value)
    st.header("COMPANY'S OVERVIEW BASED ON RECENT CONCALL AND PERFORMANCE")
    st.write(message_content.value)

    # Example formatting adjustments for the response message
    response_message = message_content.value.replace('₹', 'Rs.')
    formatted_text = message_content.value.replace('\n\n', '<br/><br/>').replace('\n', ' ')

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc = SimpleDocTemplate('concall_meet.pdf', pagesize=letter)
    hex_color = '#201c64'
    background_color = HexColor(hex_color)

    # Custom style for table text
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=10,
        fontName='Seaford-Regular',
        alignment=TA_JUSTIFY,
    )

    # Adjusted data to be stored in the table for one column layout
    data = [
        [Paragraph(f"""
    <font name="Seaford-Bold" color={hex_color}><u>Company's Overview Based on Recent Concall and Performance:</u></font><br/><br/>
    {formatted_text}""", custom_style)]
        # Add more rows as needed
    ]

    # Adjusted table setup for one column
    para = Table(data,rowHeights= [5.45*inch],colWidths=[7.8* inch])

    para.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Regular'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    assistant2 = client.beta.assistants.create(
    name="Change length of the paragraph assistant",
    instructions="""
    You are an exceptional rephrasing assistant. Your tasks include:

    Analyze the text and adjust the length of the paragraph with a total character limit of 400 characters including whitespaces.

    Ensure your explanations are clear and accessible for our clients who rely on our financial advisory services. Maintain a response temperature setting of 0.1 for precise and accurate information.

    """,
    model="gpt-4o",
    tools=[{"type": "file_search"}],
    temperature=0
    )

    thread2 = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": f"""
    read this text:
    {stock.info['longBusinessSummary']}
    Write a introduction for the company by Analyzing the given text. 

    you can also use this if you are short of words:{para}

    adjust the length of the paragraph with a total of exactly 400 characters.
    do not write anything else in the message, strictly follow this instructions.

    """,
        # Attach the new file to the message.
        
        }
    ]
    )
    
    # The thread now has a vector store with that file in its tool resources.
    print(thread2.tool_resources.file_search)

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread2.id, assistant_id=assistant2.id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread2.id, run_id=run.id))

    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")

    print(message_content.value)
    # print("\n".join(citations))

    #show the message content.value in the streamlit app
    #start with a header "COMPANY INTRODUCTION"
    st.header("COMPANY INTRODUCTION")
    st.write(message_content.value)

    text = message_content.value

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc = SimpleDocTemplate('concall_meet.pdf', pagesize=letter)
    hex_color = '#201c64'
    background_color = HexColor(hex_color)

    # Custom style for table text
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=10,
        fontName='Seaford-Regular',
        alignment=TA_JUSTIFY,
    )

    # Adjusted data to be stored in the table for one column layout
    data = [
        [Paragraph(f"""
    {text}
    """, custom_style)]
        # Add more rows as needed
    ]

    # Adjusted table setup for one column
    about = Table(data,rowHeights= [1.3*inch],colWidths=[5* inch])

    about.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Regular'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Create a ParagraphStyle for the source line
    source_style = ParagraphStyle(
        'SourceStyle',
        parent=styles['Normal'],
        fontSize=8,       # Adjust font size as needed
        leading=10,
        textColor=colors.black,   # Ensure text is black
        alignmen=TA_RIGHT        # Right-align the paragraph text
    )

    # Create the Paragraph
    source_para = Paragraph("source : Company filings", source_style)

    # Build a small one-cell table to hold that Paragraph
    source_data = [[source_para]]
    source_table = Table(source_data, colWidths=[4.0*inch])  # total width ~7 inches
    source_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),    # top align text
        # You could also do left/center alignment, or remove it entirely
        # Just note that we've set alignment=TA_RIGHT in the ParagraphStyle
    ]))

    canv=canvas.Canvas('DCB_pdf.pdf',pagesize=A4)
    width, height = A4
    canv.line(0.36*inch,10.5*inch,2.9*inch,10.5*inch)
    canv.drawImage('logo.png',0.36*inch,10.7*inch,width=1.681102*inch,height=0.6377953*inch)
    #canv.drawImage('goalfilogo.jpg',0.5*inch,9.4*inch,width=1*inch,height=1*inch)
    rev.wrapOn(canv,2.6*inch, 1.5*inch)
    rev.drawOn(canv, 0.25*inch, 8*inch)
    p_l.wrapOn(canv, 2.6*inch, 1.5*inch)
    p_l.drawOn(canv,2.85*inch, 8*inch)
    p.wrapOn(canv,2.6*inch, 1.5*inch)
    p.drawOn(canv,5.45*inch, 8*inch) #(canv, 5.5*inch, 6.72*inch)

    v.wrapOn(canv,2.6*inch, 1.5*inch)
    v.drawOn(canv, 0.25*inch, 7.05*inch)
    gy.wrapOn(canv,2.6*inch, 1.5*inch)
    gy.drawOn(canv, 2.85*inch, 7.05*inch)
    gq.wrapOn(canv, 2.6*inch, 1.5*inch)
    gq.drawOn(canv, 5.45*inch, 7.05*inch)

    c.wrapOn(canv,2.6*inch, 1.5*inch)
    c.drawOn(canv,0.25*inch,5.91*inch)
    h.wrapOn(canv,2.6*inch, 1.5*inch)
    h.drawOn(canv, 2.85*inch, 5.91*inch)
    l.wrapOn(canv,2.6*inch, 1.5*inch)
    l.drawOn(canv, 5.45*inch, 5.91*inch)

    

    



    stockname.wrapOn(canv, 5.25*inch, 15*inch)
    stockname.drawOn(canv, 2.9* inch, 10.9*inch)
    ticker1.wrapOn(canv, 4.75*inch, 20)
    ticker1.drawOn(canv, 3.15*inch,10.5*inch)

    about.wrapOn(canv,4.75*inch,2*inch)
    about.drawOn(canv,3*inch, 9.22*inch )
    date.wrapOn(canv,3*inch,3*inch)
    date.drawOn(canv,0.4*inch,9.3*inch)

    canv.setLineWidth(0.2)
    # canv.rect(0.25*inch,0.5*inch,7.8*inch,5.35*inch)
    # overview.wrapOn(canv, 7*inch, 0.5*inch)
    # overview.drawOn(canv,0.4*inch ,5.55*inch)
    para.wrapOn(canv, 7.4*inch,3.95*inch)
    para.drawOn(canv,0.25*inch, 0.22*inch)

    # Decide where to place it: adjust X/Y to your liking
    source_table.wrapOn(canv, 2.0*inch, 0.25)
    source_table.drawOn(canv, 6.7*inch, 5.7*inch)


    
    canv.showPage()
    canv.save()


    assistant = client.beta.assistants.create(
    name="Financial Analyst Assistant",
    instructions="""
    You are an exceptional financial analyst assistant. Your tasks include:

    Analyze Financial Sheets: Thoroughly review the provided financial sheets of a company, focusing on specified metrics.
    Create Advisory Reports: Assist in developing comprehensive financial advisory reports based on your analysis.
    Answer Questions: Respond accurately to any questions related to your analysis.
    Deliver Detailed Insights: Supply various tables, sector analyses, and other relevant data to support your findings.

    Ensure your explanations are clear and accessible for our clients who rely on our financial advisory services. Maintain a response temperature setting of 0.1 for precise and accurate information.

    """,
    model="gpt-4o",
    tools=[{"type": "file_search"}],
    temperature=0
    )


    message_file = client.files.create(
    file=open("DCB_pdf.pdf", "rb"), purpose="assistants"
    )
    
    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": """

    **Analyze the Company Data and Provide Commentary**

    You are given data for a company, which is organized into nine tables:
    1. Revenue
    2. Profit & Loss
    3. Profitability Matrix
    4. Valuation Matrix
    5. Growth (YoY)
    6. Growth (QoQ)
    7. Capital Allocation
    8. Holdings
    9. Leverage

    Your tasks are as follows:
    1. Thoroughly analyze each table.
    2. Write an unbiased analysis of exactly 350 characters (including whitespaces) for each table, focusing on interpretation and analysis without repeating the financial data, follow these instructions strictly.

    **Table Structure:**
    Create a table with two columns:
    - Aspect
    - Commentary

    **Guidelines:**
    - Use data points for which values are available and ignore any missing data points in the analysis commentary.
    - Ensure explanations are clear and accessible for our clients who rely on our research advisory services.
    - Maintain a response temperature setting of 0 for precise and accurate information.
    - Write as a human research analyst, avoiding any machine-generated tonality.
    - Provide only the requested table in your response, strictly following these instructions.



    give this table in format like this:
    Aspect,Commentary
    Revenue,"",""
    Profit & Loss,"",""
    Profitability Matrix,"",""
    Valuation Matrix,"",""
    Growth (YoY),"",""
    Growth (QoQ),"",""
    Capital Allocation,"",""
    Holdings,"",""
    Leverage,"",""

    Do not write anything extra in the response

    """,
        # Attach the new file to the message.
        "attachments": [
            { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
        ],
        }
    ]
    )
    
    # The thread now has a vector store with that file in its tool resources.
    print(thread.tool_resources.file_search)


    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")

    print(message_content.value)
    print("\n".join(citations))

    csv_content = message_content.value

    # Define the path to save the CSV file
    file_path = os.path.join(os.getcwd(), 'financial_metrics.csv')

    # Write the CSV content to a file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(csv_content)

    print(f"CSV file has been saved to {file_path}")

    df_table = pd.read_csv('financial_metrics.csv')
    df_table = df_table.set_index('Aspect')
    for column in df_table.columns:
        df_table[column] = df_table[column].str.replace('₹', 'Rs.')
        df_table[column] = df_table[column].str.replace('\n\n', '<br/><br/>').replace('\n', ' ')
    print(df_table)
    #print the table in the streamlit app
    st.header("COMPANY'S FINANCIAL METRICS AND COMMENTARY")
    st.write(df_table)
    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc= SimpleDocTemplate('prosandcons.pdf',pagesize=letter)
    hex_color = '#201c64'
    background_color = HexColor(hex_color)

    # Custom style for table text
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=10,
        fontName='Seaford-Regular',
        alignment=TA_JUSTIFY,
    
    )

    # Data to be stored in the table
    data = [
        ['Aspect', 'Commentary'],
        ['Revenue', Paragraph(f'{df_table.loc["Revenue"]["Commentary"]}', custom_style)],
        ['Profit & Loss', Paragraph(f'{df_table.loc["Profit & Loss"]["Commentary"]}', custom_style) ],
        ['Profitability Matrix',Paragraph(f'{df_table.loc["Profitability Matrix"]["Commentary"]}', custom_style)],
        ['Valuation Matrix', Paragraph(f'{df_table.loc["Valuation Matrix"]["Commentary"]}', custom_style) ],
        ['Growth (YoY)', Paragraph(f'{df_table.loc["Growth (YoY)"]["Commentary"]}', custom_style) ],
        ['Growth (QoQ)', Paragraph(f'{df_table.loc["Growth (QoQ)"]["Commentary"]}', custom_style) ],
        ['Capital Allocation',Paragraph(f'{df_table.loc["Capital Allocation"]["Commentary"]}', custom_style) ],
        ['Holdings', Paragraph(f'{df_table.loc["Holdings"]["Commentary"]}' , custom_style)],
        ['Leverage', Paragraph(f'{df_table.loc["Leverage"]["Commentary"]}', custom_style) ],
        
    ]

    prosandcons = Table(data,rowHeights= [19] + [45.5] * (len(data) - 1), colWidths=[1.4* inch, 6.2* inch])


    prosandcons.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), background_color),
        ('TEXTCOLOR', (0, 0), (-1,0), colors.white),
        ('TEXTCOLOR', (0, 1), (0,-1), background_color),
        ('TEXTCOLOR', (1, 1), (1,-1), colors.darkgreen),
        ('TEXTCOLOR', (2, 1), (2,-1), colors.red),
        ('FONTNAME', (0, 0), (-1,0),'Seaford-Bold' ),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Seaford-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (1, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.2, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.2, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    #get instrument token using the trading symbol
    def get_instrument_token(instrument_df, symbol):
        print((instrument_df['tradingsymbol'] == symbol))
        return instrument_df[(instrument_df['tradingsymbol'] == symbol)&(instrument_df['exchange'] == 'NSE')]['instrument_token'].values[0]


    date=datetime.datetime.now().strftime("%Y-%m-%d")
    report_date=date


    # Calculate the start date
    start_Date = pd.to_datetime(report_date) - relativedelta(years=1)
    #get the next date of report date
    next_date = pd.to_datetime(report_date) + timedelta(days=1)
    # price_data = yf.download(ticker + '.NS', start=start_Date, end=next_date)
    #download the price data of the stock using kiteconnect
    def get_stock_data(symbol, start_date, end_date, interval="day"):
        try:
            token = get_instrument_token(instrument_df, symbol)
            historical_data = kite.historical_data(token, start_date, end_date, interval)
            df = pd.DataFrame(historical_data)
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df.set_index('date', inplace=True)
            df.rename(columns={'close':'Close'},inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    price_data = get_stock_data(ticker, start_Date, report_date)
    print(price_data)
    # create a dataframe of price_data

    #chyange the name of close column to Close  
    

    #set date as index of price_data
    
    #if data is not empty


    # Create the plot
    fig = go.Figure()
    #change the width of the chart lines
    fig.add_trace(go.Scatter(x=price_data.index, y=price_data['Close'], mode='lines', name='Close Price', line=dict(width=1.3)))

    # Generate tick values for each month
    tickvals = pd.date_range(start=start_Date, end=report_date, freq='MS').tolist()
    # Ensure the index is a datetime object
    if not isinstance(price_data.index[0], pd.Timestamp):
        price_data.index = pd.to_datetime(price_data.index)


    print(tickvals)

    annotations = [
        dict(
            x=price_data.index[0],
            y=price_data['Close'].iloc[0],
            xref='x',
            yref='y',
            text=f"{round(price_data['Close'].iloc[0],2)}, {price_data.index[0].strftime("%d-%b-%y")}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(
                color="black",
                size=12
            ),
            bgcolor="white",
            bordercolor="black",
            borderwidth=1
        ),
        dict(
            x=price_data.index[-1],
            y=price_data['Close'].iloc[-1],
            xref='x',
            yref='y',
            text=f"{round(price_data['Close'].iloc[-1],2)}, {price_data.index[-1].strftime("%d-%b-%y")}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(
                color="black",
                size=12
            ),
            bgcolor="white",
            bordercolor="black",
            borderwidth=1
        )
    ]

    fig.update_layout(
    
        title=f'{ticker} Daily Closing One Year Price Chart',
        yaxis_title='Price',
        template='plotly_white',
        width=1000,
        height=300,
        #remove gridlines
        
        xaxis=dict(
            tickformat="%b'%y",  # Format ticks as abbreviated month and full year
            tickvals=tickvals,
            showgrid=False,  # Remove the gridlines
            showline=True,  # Show the x-axis line 
            linecolor='black',  # Set the x-axis line color to black
            linewidth=1.3,  # Set the x-axis line width
            
        ),
        margin=dict(l=20, r=20, t=30, b=20),  # Adjust margins to remove extra spaces
        paper_bgcolor='white',  # Set background color to white
        plot_bgcolor='white',   # Set plot area background color to white
        yaxis=dict(
            showgrid=False,  # Remove the gridlines
            showline=True,  # Show the y-axis line
            linecolor='black',  # Set the y-axis line color to black
            linewidth=1.3,  # Set the y-axis line width
        ),
        #change color of the chartlines to black
        colorway=['black'],
        annotations=annotations 

    )

    # Save the chart as an image
    fig.write_image(f'price_chart.jpg', scale=10)

    # Show the chart
    # fig.show()

    left_margin = 0.36 * inch
    right_margin = 0.36 * inch
    top_margin = 0.3 * inch
    bottom_margin = 0.75 * inch

    available_width = A4[0] - left_margin - right_margin
    available_height = A4[1] - top_margin - bottom_margin

    # Create a custom frame with the specified margins
    frame = Frame(
        left_margin, bottom_margin, available_width, available_height, id='normal'
    )
    
    doc = SimpleDocTemplate(f"second.pdf",pagesize=A4,leftMargin=left_margin,topMargin=0)
    doc.addPageTemplates([PageTemplate(id='2nd', frames=[frame])])


    chart_image = Image(f'price_chart.jpg', width=available_width, height=available_height * 0.2)

    flowables = [
        Spacer(1, 0.1 * inch),
        chart_image,
        Spacer(1, 0.005 * inch),  # Add a gap after the chart image
        peerTablePdf,
        Spacer(1, 0.1 * inch),  # Add a gap after the peer table
        prosandcons
    ]
    doc.build(flowables)

    # Function to add pages from one PDF to another
    def add_pdf_pages(source_pdf, writer):
        reader = PdfReader(source_pdf)
        for page in reader.pages:
            writer.add_page(page)


    # Create a new PDF writer object
    pdf_writer = PdfWriter()


    # Add pages from both PDFs to the new file
    add_pdf_pages('DCB_pdf.pdf', pdf_writer)
    add_pdf_pages(f'second.pdf', pdf_writer)

    output_dir = os.path.join(os.getcwd(),"reports")
    date=datetime.datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(output_dir,date)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write the combined PDF to a file in the specified directory
    with open(f'{output_dir}/{ticker}.pdf', 'wb') as out:
        pdf_writer.write(out)

    assistant3 = client.beta.assistants.create(
    name="Financial Analyst Assistant",
    instructions="""
    You are an exceptional financial analyst assistant. Your tasks include:

    Analyze Financial Sheets: Thoroughly review the provided financial sheets of a company, focusing on specified metrics.
    Create Advisory Reports: Assist in developing comprehensive financial advisory reports based on your analysis.
    Answer Questions: Respond accurately to any questions related to your analysis.
    Provide Recommendations: If requested, offer a biased recommendation to either buy or sell.
    Deliver Detailed Insights: Supply various tables, sector analyses, and other relevant data to support your findings.

    Ensure your explanations are clear and accessible for our clients who rely on our financial advisory services. Maintain a response temperature setting of 0.1 for precise and accurate information.

    """,
    model="gpt-4o",
    tools=[{"type": "file_search"}],
    )
    file_path=f'{output_dir}/{ticker}.pdf'
    message_file = client.files.create(
    file=open(file_path, "rb"), purpose="assistants"
    )
    
    # Create a thread and attach the file to the message
    thread3 = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": """
    Please write the commentary maximum of 1500 characters in two paragraphs for the recommendation section of our report. We are bullish on this company from a short to mid-term perspective. 

    Use key data points such as growth QoQ metrics, valuation metrics, capital allocation , peer to peer competition , price chart and from the recent concall summary. 

    Additionally, include a one-line mention of a potential negative aspect of the company in a mild manner to keep the recommendation unbiased.

    Ensure the explanations are simple, clear and accessible for our clients who rely on our research advisory services. 

    Maintain a response temperature setting of 0 for precise and accurate information. 

    Write as a human research analyst and keep language similar to concall summary,make sure to avoiding any machine-generated tonality, there shouldnt be a semi column anywhere

    Keep the summary in one or two paragraphs, strictly following these instructions.

    Only provide the paragraphs without any additional information or commentary of the previous response, do not add anything extra in your response prompt i have to copy it directly and use it somewhere. 
    alse not include citations or references in the response.
    follow these instructions strictly 
        """,
        # Attach the new file to the message.
        "attachments": [
            { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
        ],
        }
    ]
    )
    
    # The thread now has a vector store with that file in its tool resources.
    print(thread3.tool_resources.file_search)

    run3 = client.beta.threads.runs.create_and_poll(
        thread_id=thread3.id, assistant_id=assistant3.id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread3.id, run_id=run3.id))

    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")

    print(message_content.value)
    print("\n".join(citations))

    response_table=message_content.value.replace('₹', 'Rs.')
    formatted_text = message_content.value.replace('\n\n', '<br/><br/>').replace('\n', ' ')
    print(formatted_text)

    #show the formatted text in the streamlit app   
    st.header("Analyst Viewpoint")
    analyst_viewpoint = message_content.value
    st.write(message_content.value)
    

    styles = getSampleStyleSheet()
    # Page dimensions
    width, height = letter  # Keep for later
    my_doc = SimpleDocTemplate('prosandcons.pdf', pagesize=letter)
    hex_color = '#201c64'
    background_color = HexColor(hex_color)

    # Custom style for table text
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=10,
        fontName='Seaford-Regular',
        alignment=TA_JUSTIFY,
    )

    # Adjusted data to be stored in the table for one column layout
    data = [
        [Paragraph(f'<font name="Seaford-Bold" color={hex_color}>Analyst viewpoint:</font> {formatted_text}', custom_style)]
        # Add more rows as needed
    ]

    # Adjusted table setup for one column
    commentry = Table(data,rowHeights= [3.3*inch],colWidths=[7.7* inch])

    commentry.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('BOX', (0, 0), (-1, -1), 2, colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Adjusted data to be stored in the table for one column layout
    data = [
        [Paragraph('<font>Please read detailed disclosure on next page.</font>', custom_style)]
        # Add more rows as needed
    ]

    # Adjusted table setup for one column
    disclaimer_one =Table(data,rowHeights= [0.5*inch],colWidths=[7.7* inch])

    disclaimer_one.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Seaford-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('BOX', (0, 0), (-1, -1), 2, colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))


    doc = SimpleDocTemplate(f"third.pdf",pagesize=A4,leftMargin=left_margin,topMargin=0)
    doc.addPageTemplates([PageTemplate(id='3rd', frames=[frame])])
    flowables = [
        Spacer(1, 0.2 * inch),
        commentry,
        Spacer(1, 0.1 * inch),
        disclaimer_one
    ]
    doc.build(flowables)


    # Function to add pages from one PDF to another
    def add_pdf_pages(source_pdf, writer):
        reader = PdfReader(source_pdf)
        for page in reader.pages:
            writer.add_page(page)

    # Create a new PDF writer object
    pdf_writer = PdfWriter()


    # Add pages from both PDFs to the new file
    add_pdf_pages(file_path, pdf_writer)
    add_pdf_pages(f'third.pdf', pdf_writer)

    #add disclaimer-GoalFi pdf to the final pdf
    add_pdf_pages('Disclaimer-GoalFi.pdf', pdf_writer)

    output_dir = os.path.join(os.getcwd(),"reports")
    date=datetime.datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(output_dir,date)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write the combined PDF to a file in the specified directory
    with open(f'{output_dir}/{ticker}.pdf', 'wb') as out:
        pdf_writer.write(out)
    report_pdf_path = f'{output_dir}/{ticker}.pdf'
      

    st.write("Please download the PDF report for detailed analysis")
    with open(report_pdf_path, "rb") as file:
            st.download_button(
                label="Download Report",
                data=file,
                file_name=f"{ticker}.pdf",
                mime="application/pdf"
            )
    return analyst_viewpoint

st.title("Multi-Stock Analyst Viewpoint Generator")

# Get list of tickers (comma separated)
tickers_input = st.text_area("Enter NSE tickers separated by commas (e.g., ALKEM, SHYAMMETL, SAFARI)", 
                             value="ALKEM, SHYAMMETL, SAFARI")
tickers_list = [t.strip() for t in tickers_input.split(",") if t.strip()]

# Get the date from the user
user_date = st.date_input("Enter the date for which data is required", datetime.date(2023, 1, 1))
user_date_str = user_date.strftime("%Y-%m-%d")
date = user_date.strftime("%d-%b-%Y")
st.write(f"Selected Date: {user_date_str}")

# Connect to Zerodha Kite only once and store in session_state
if 'kite' not in st.session_state:
    st.write("Connecting to Zerodha Kite...")
    user_name = os.getenv("user_name")
    password = os.getenv("password")
    totp = os.getenv("totp")
    api_key = os.getenv("api_key")
    api_secret = os.getenv("api_secret")
    
    kite = KiteConnect(api_key=api_key)
    # (Assuming your login.kiteLogin() function returns a valid request token)
    request_token = login.kiteLogin(user_name, password, totp, api_key)
    data = kite.generate_session(request_token, api_secret)
    kite.set_access_token(data["access_token"])
    
    instrument_dump = kite.instruments()  # Get instruments dump from NSE
    instrument_df = pd.DataFrame(instrument_dump)
    instrument_df['expiry']=pd.to_datetime(instrument_df['expiry'])  # Dump it to a DataFrame
    
    st.session_state.kite = kite
    st.session_state.instrument_df = instrument_df
    st.write("Connected to Zerodha Kite")

# -------------------------------
# Process each ticker and collect results
# -------------------------------
results = []

if st.button("Get Analysis for All Tickers"):
    kite = st.session_state.kite
    instrument_df = st.session_state.instrument_df

    for ticker in tickers_list:
        st.write(f"Processing ticker: {ticker}")
        # (If the ticker is not found in instrument_df, skip it.)
        if ticker not in instrument_df['tradingsymbol'].values:
            st.write(f"Ticker {ticker} is invalid. Skipping...")
            continue

        # Run your processing (up to the analyst viewpoint) for this ticker.
        analyst_viewpoint = get_analyst_viewpoint(ticker, user_date_str, kite, instrument_df, date)
        results.append({"Ticker": ticker, "Analyst Viewpoint": analyst_viewpoint})
        st.write(f"Analyst Viewpoint for {ticker}:")
        st.write(analyst_viewpoint)
        st.write("---")
    
    # -------------------------------
    # Create CSV output and download button
    # -------------------------------
    if results:
        results_df = pd.DataFrame(results)
        st.write("Final Analysis Results:")
        st.dataframe(results_df)
        csv_data = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="analyst_viewpoints.csv",
            mime="text/csv"
        )
    else:
        st.write("No valid tickers were processed.")
    