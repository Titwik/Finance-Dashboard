import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()  # Loads variables from .env into the environment

class StarlingAPI:
    def __init__(self):

        # API token environment variable
        TOKEN = os.getenv("payment_token")

        self.base_url = "https://api.starlingbank.com/api/v2"
        self.headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json"
        }

    # get account data
    def get_accounts(self):
        return requests.get(f"{self.base_url}/accounts", headers=self.headers).json()

    # get specified account balance 
    def get_balance(self, account_uid):
        return requests.get(f"{self.base_url}/accounts/{account_uid}/balance", headers=self.headers).json()
    
    # get transation statement between  specified times
    def get_transaction_statement(self, account_uid, category_uid, start_date, end_date):
        url = f"{self.base_url}/feed/account/{account_uid}/category/{category_uid}/transactions-between?minTransactionTimestamp={start_date}&maxTransactionTimestamp={end_date}"
        response = requests.get(url, headers=self.headers)
        return response.json()["feedItems"] 
    
    # categories like "bills", "Eating out" etc
    def get_monthly_categories(self, account_uid, year, month):

        url = f"{self.base_url}/accounts/{account_uid}/spending-insights/spending-category"

        params = {
            'year' : year,
            'month' : month 
        }
        response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params
        )
        return response.json()

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
    return category_df

# function to get the transaction history from the main account
def transactions(start_date: str, end_date: str = None):
    """
    Enter the start and end date in dd/mm/yyyy format.
    If end_date is not provided, defaults to current time.
    """

    # Convert start_date string -> datetime
    start_dt = datetime.strptime(start_date, "%d/%m/%Y")

    # If end_date is None, use current datetime
    if end_date:
        end_dt = datetime.strptime(end_date, "%d/%m/%Y")
    else:
        end_dt = datetime.now()

    # Convert both to API format
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    savings_accountUid = accounts_data['accounts'][0]['accountUid']
    savings_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # Get balance (optional, but you had it before)
    current_balance_minor = api.get_balance(savings_accountUid)['effectiveBalance']['minorUnits']
    current_balance = current_balance_minor / 100

    # Get transactions
    try:
        transactions = api.get_transaction_statement(
            savings_accountUid,
            savings_categoryUid,
            start_iso,
            end_iso
        )
    except:
        print('Something went wrong')

    transaction_list = []
    for tx in transactions:

        # get relevant attributes that may be missing
        settled_date = tx.get("transactionTime")
        spending_category = tx.get('spendingCategory')

        if not spending_category:
            spending_category = 'N/A'

        # if settled date exists, convert to dd/mm/yyyy
        if settled_date:  
            settled_date = datetime.strptime(settled_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")
        else:
            settled_date = "N/A"  

        transaction_list.append({
            'Date': settled_date,
            'Counter Party Name': tx['counterPartyName'],
#            'Reference': tx['reference'],
            'Category' : tx['spendingCategory'],
            'Amount': tx['amount']['minorUnits']/100,           
            'Currency': tx['sourceAmount']['currency'],
            'Direction' : tx['direction']
        })
    transactions_df = pd.DataFrame(transaction_list)

    return transactions_df


if __name__ == "__main__":
    # Example usage
    df = biggest_expenses_in_current_month('AUGUST', 2025)
    print(df)
