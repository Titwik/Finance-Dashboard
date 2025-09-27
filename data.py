import yfinance as yf
import time 
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()  # Loads variables from .env into the environment

class StarlingAPI:
    def __init__(self, max_retries=3, backoff=2):
        # API token environment variable
        TOKEN = os.getenv("payment_token")

        self.base_url = "https://api.starlingbank.com/api/v2"
        self.headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json"
        }
        self.max_retries = max_retries
        self.backoff = backoff

    def _request(self, method, endpoint, **kwargs):
        """
        Internal helper method to make API requests with retry logic.
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(
                    method, url, headers=self.headers, timeout=10, **kwargs
                )
                response.raise_for_status()  

                return response.json()  

            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"[StarlingAPI] Attempt {attempt} failed: {e}")

                # re-raise on final failure
                if attempt == self.max_retries:
                    raise  

                time.sleep(self.backoff)

    # get account data
    def get_accounts(self):
        return self._request("GET", "/accounts")

    # get specified account balance 
    def get_balance(self, account_uid):
        return self._request("GET", f"/accounts/{account_uid}/balance")

    # get transaction statement between specified times
    def get_transaction_statement(self, account_uid, category_uid, start_date, end_date):
        url = f"/feed/account/{account_uid}/category/{category_uid}/transactions-between"
        params = {
            "minTransactionTimestamp": start_date,
            "maxTransactionTimestamp": end_date
        }

        data = self._request("GET", url, params=params)
        return data.get("feedItems", [])

    # categories like "bills", "Eating out" etc
    def get_monthly_categories(self, account_uid, year, month):

        # parameters
        params = {"year": year, "month": month}

        # return the .json response
        return self._request("GET", f"/accounts/{account_uid}/spending-insights/spending-category", params=params)

# define a function for the monthly pocket money expenses
def monthly_pocket_money_balance():

    # call the API class
    api = StarlingAPI()

    # get accounts
    accounts_data = api.get_accounts()
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    #main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # get balance for that account
    main_balance = api.get_balance(main_accountUid)['effectiveBalance']['minorUnits'] / 100

    return main_balance

# function to track the growth of savings account
def savings_growth_history():
    
    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    savings_accountUid = accounts_data['accounts'][1]['accountUid']
    savings_categoryUid = accounts_data['accounts'][1]['defaultCategory']

    # Get current account balance (assume this is the balance at 'today')
    current_balance_minor = api.get_balance(savings_accountUid)['effectiveBalance']['minorUnits']
    current_balance = current_balance_minor / 100  # convert to pounds

    # Get transactions since start date
    start_date = datetime.strptime("2025-07-27", "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    transactions = api.get_transaction_statement(
        savings_accountUid,
        savings_categoryUid,
        start_date,
        today
    )

    # Create DataFrame
    df = pd.DataFrame(transactions)
    df = df[['amount', 'settlementTime', 'direction']]
    df['settlementTime'] = pd.to_datetime(df['settlementTime'])
    df['amount'] = df.apply(
        lambda x: x['amount']['minorUnits'] / 100 * (-1 if x['direction'] == 'OUT' else 1),
        axis=1
    )

    # Create month column
    df['month'] = df['settlementTime'].dt.to_period('M')

    # Sum transactions by month
    monthly_change = df.groupby('month')['amount'].sum().sort_index()

    # Compute cumulative balance starting from initial balance
    # Estimate starting balance = current balance minus sum of all transactions
    starting_balance = current_balance - monthly_change.sum()
    monthly_balance = monthly_change.cumsum() + starting_balance

    # Convert month to string for plotting
    monthly_balance = monthly_balance.reset_index()
    monthly_balance['month'] = monthly_balance['month'].dt.strftime('%b %Y')

    return monthly_balance

# function to return the biggest expenses in the month 
def biggest_expenses_in_current_month(month, year):

    """
    month is one of the following:
    [JANUARY, FEBRUARY, MARCH, APRIL, MAY, JUNE, JULY, AUGUST, SEPTEMBER, OCTOBER, NOVEMBER, DECEMBER]

    year is an integer year.
    """

    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    
    transactions = api.get_monthly_categories(main_accountUid, int(year), month.upper())

    if len(transactions['breakdown']) == 0:
        return print('No account activity for the chosen time.')
    
    # convert to a df so plotly can visualize it
    category_list = []
    for category in transactions['breakdown']:
        category_text = category['spendingCategory'].title().replace("_", " ")
        category_list.append({
            'Category': category_text,
            'Total Expenditure': category['netSpend'],
            'Direction': category['netDirection']
        })

    category_df = (
    pd.DataFrame(category_list)
      .sort_values(
          by=["Direction", "Total Expenditure"], 
          ascending=[False, False]
      )
    )

    category_df = category_df[~category_df['Category'].isin(['Saving', 'Investments'])]
    return category_df

# function to get the transaction history from the main account
def transactions(start_date, end_date):

    start_iso = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    end_iso  = end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # call the bank api
    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # Get balance (optional, but you had it before)
    current_balance_minor = api.get_balance(main_accountUid)['effectiveBalance']['minorUnits']
    current_balance = current_balance_minor / 100

    # Get transactions
    try:
        transactions = api.get_transaction_statement(
            main_accountUid,
            main_categoryUid,
            start_iso,
            end_iso
        )
    except:
        print('Something went wrong')

    transaction_list = []
    for tx in transactions:

        # get relevant attributes that may be missing
        settled_date = tx.get("transactionTime")

        # if settled date exists, convert to dd/mm/yyyy
        if settled_date:  
            settled_date = datetime.strptime(settled_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")
        else:
            settled_date = "N/A"  

        transaction_list.append({
            'Date': settled_date,
            'Counter Party Name': tx['counterPartyName'],
#            'Reference': tx['reference'],
            'Category': tx['spendingCategory'].replace('_', ' ').title(),
            'Amount': tx['sourceAmount']['minorUnits']/100,           
            'Currency': tx['sourceAmount']['currency'],
            'Direction' : tx['direction']
        })
    transactions_df = pd.DataFrame(transaction_list)

    return transactions_df

# function to get investment data
# want to return how many shares I own of a ticker, total invested value per ticker, net deposit, rate of return, and how much it has grown by 
def investments_data(statement_file):

    # read the statement file
    df = pd.read_csv(statement_file)

    # fucnction to return number of shares owned per ticker
    def shares_owned_per_ticker():
        
        # dataframe for buy and sell 
        df_buy = df[df['Action'] == 'Market buy']
        df_sell = df[df['Action'] == 'Market sell']

        shares_buy = df_buy.groupby('Ticker')['No. of shares'].sum()
        shares_sell = df_sell.groupby('Ticker')['No. of shares'].sum()
        
        # get number of shares owned
        shares_owned = shares_buy.subtract(shares_sell, fill_value=0)

        # number of shares owned per ticker
        shares_owned = shares_owned[shares_owned > 0]
        shares_owned_df = shares_owned.reset_index()

        return shares_owned_df
    
    # function to return net deposit per ticker
    def net_deposit_per_ticker():

        df_buy = df[df['Action'] == 'Market buy']
        df_sell = df[df['Action'] == 'Market sell']

        buy_deposit = df_buy.groupby('Ticker')['Total'].sum()
        sell_withdrawal = df_sell.groupby('Ticker')['Total'].sum()

        net_deposit = buy_deposit.subtract(sell_withdrawal, fill_value=0)
        net_deposit = net_deposit[net_deposit > 0].reset_index()
        net_deposit.columns = ['Ticker', 'Net Deposit']

        # keep only tickers you still own
        owned_tickers = shares_owned_per_ticker()['Ticker'].tolist()
        net_deposit = net_deposit[net_deposit['Ticker'].isin(owned_tickers)]

        return net_deposit

    # inner join the tables on Ticker
    shares_owned = shares_owned_per_ticker()
    net_deposit = net_deposit_per_ticker()

    # Get current price for each ticker using yfinance
    def get_current_price(ticker):
        try:
            data = yf.Ticker(ticker).history(period="1d")
            print('Ignore the message above')
            print('')
            if data.index.empty:
                pass
            elif not data.empty:
                return data['Close'].iloc[-1]
            
        except:
            pass
        
        # Try London Stock Exchange
        try:
            data_l = yf.Ticker(f"{ticker}.L").history(period="1d")
            if not data_l.empty:
                return data_l['Close'].iloc[-1]
        except:
            pass
        
        # Could not fetch price
        return None

    shares_owned['Current Price'] = shares_owned['Ticker'].apply(get_current_price)
    
    # Calculate current value
    shares_owned['Current Value'] = shares_owned['No. of shares'] * shares_owned['Current Price']

    result = pd.merge(
        shares_owned,
        net_deposit,
        on="Ticker",   
        how="inner"    
    )

    #Per-ticker rate of return and growth
    result['Rate of Return (%)'] = (
        (result['Current Value'] - result['Net Deposit']) / result['Net Deposit']
    ) * 100
    result['Growth'] = result['Current Value'] - result['Net Deposit']

    # Portfolio-level totals 
    total_net_deposit = result['Net Deposit'].sum()
    total_current_value = result['Current Value'].sum()
    total_growth = total_current_value - total_net_deposit
    total_return_pct = (total_growth / total_net_deposit) * 100 if total_net_deposit > 0 else 0

    portfolio_summary = {
        "Total Net Deposit": total_net_deposit,
        "Total Current Value": total_current_value,
        "Total Growth": total_growth,
        "Overall Rate of Return (%)": total_return_pct
    }

    return result, portfolio_summary

if __name__ == "__main__":

    end_date = datetime.now()
    start_date = end_date.replace(day=19)

    start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    #df = transactions(start_date, end_date)
    #print(df[df['Direction'] == 'OUT'])

    api = StarlingAPI()

    end_date = datetime.now()
    start_date = end_date.replace(day=19)

    df = transactions(start_date, end_date)
    print(df[df['Direction'] == 'OUT'])