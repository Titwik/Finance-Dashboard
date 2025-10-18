
import os
import json
import time
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
    
    # get savings spaces
    def get_savings_spaces(self, accountUid):

        url = f'/account/{accountUid}/spaces'
        
        return self._request('GET', url)
    
    def get_spending_space(self, accountUid, spaceUid):

        url = f'/account/{accountUid}/spaces/spending/{spaceUid}'

        return self._request('GET', url)

# define a function for the monthly pocket money and groceries expenses
def monthly_balance():

    # call the API class
    api = StarlingAPI()

    # account data
    account_data = api.get_accounts()
    accountUid = account_data['accounts'][0]['accountUid']
    categoryUid = account_data['accounts'][0]['defaultCategory']

    # payday is the 27th, so budget from the 27th onwards
    today = datetime.now()
    end_date = today
    if today.day >= 27:
        start_date = today.replace(day=27)
    else:
        temp_date = today.replace(day=1)
        last_month = temp_date - timedelta(days=1) # subtract 1 from the last day of month to go to 'last month'
        start_date = last_month.replace(day=27)
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # get the transaction history
    transaction_history = api.get_transaction_statement(
        accountUid,
        categoryUid,
        start_date_str,
        end_date_str
    )

    def pocket_money():

        '''
        Logic: I have 180 GBP for casual, guilt-free spending. Check if category is NOT investments, rent, utilities etc and subtract from 180 GBP
        '''
        pocket_money_allowance = 18000 # in minorUnits
        exclusions = ('investments', 'rent', 'bills', 'expenses', 'income', 'saving', 'groceries') # categories not to consider for personal spending

        total_pocket_money_spent = 0
        for tx in transaction_history:
            if (tx['spendingCategory'].lower() not in exclusions and 
                tx['direction'] == 'OUT'
            ):
                total_pocket_money_spent += tx['amount']['minorUnits']

        remaining_pocket_money = pocket_money_allowance - total_pocket_money_spent

        return remaining_pocket_money/100, total_pocket_money_spent/100
    
    def grocery_balance():

        """
        Logic: I have 120 GBP for groceries, so 100% of the visual should be 120. I will then deduct from 120 any amount that is classed as 'groceries' in the transaction statement category.
        """

        groceries_allowance = 12000 # in minorUnits

        total_groceries_spent = 0
        for tx in transaction_history:
            if tx['spendingCategory'].lower() == 'groceries' and tx['direction'] == 'OUT':
                total_groceries_spent += tx['amount']['minorUnits']

        remaining_groceries = groceries_allowance - total_groceries_spent

        return remaining_groceries/100, total_groceries_spent/100
    
    return pocket_money(), grocery_balance()

# function to track growth of savings account
def savings_growth_history():
    
    """
    data to track the growth of savings account over time
    """

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
    end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    transactions = api.get_transaction_statement(
        savings_accountUid,
        savings_categoryUid,
        start_date,
        end_date
    )

    # Create DataFrame
    df = pd.DataFrame(transactions)
    df = df[['direction', 'amount', 'spendingCategory', 'settlementTime']]

    # keep datetime for calculations
    df['settlementTime'] = pd.to_datetime(df['settlementTime'])
    df['amount'] = df.apply(
        lambda x: x['amount']['minorUnits'] / 100 * (-1 if x['direction'] == 'OUT' else 1),
        axis=1
    )
    
    # reverse order for chronological
    df = df.iloc[::-1].reset_index(drop=True)
    df['display_date'] = df['settlementTime'].dt.strftime('%d/%m/%Y')

    # Compute cumulative change
    df['running_balance_change'] = df['amount'].cumsum()
    starting_balance = current_balance - df['running_balance_change'].iloc[-1]
    df['absolute_balance'] = starting_balance + df['running_balance_change']

    df = df[['display_date', 'amount', 'absolute_balance']]

    return df

# function to return the biggest expenses in the month 
def biggest_expenses_in_current_month(month, year):

    """
    Returns a DataFrame of the largest spending categories for the given month and year.

    Args:
        month (str): One of ["JANUARY", "FEBRUARY", ..., "DECEMBER"] (case-insensitive)
        year (int): The year as an integer, e.g., 2025

    Returns:
        pd.DataFrame: Sorted list of spending categories and their total expenditure.
                      Returns None and prints a message if no activity.
    """

    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    main_categories = api.get_monthly_categories(main_accountUid, int(year), month.upper())

    if len(main_categories['breakdown']) == 0:
        return print('No account activity for the chosen time.')
    
    # convert to a df so plotly can visualize it
    category_list = [
        {
            'Category': cat['spendingCategory'].title().replace("_", " "),
            'Total Expenditure': cat['netSpend'],
            'Direction': cat['netDirection']
        }
        for cat in main_categories['breakdown']
    ]

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

    # Convert input strings to datetime objects
    start_dt = datetime.strptime(start_date, "%d/%m/%Y")
    end_dt = datetime.strptime(end_date, "%d/%m/%Y")
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    end_iso   = end_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Call the API
    api = StarlingAPI()
    accounts_data = api.get_accounts()
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # Get transactions
    try:
        transactions = api.get_transaction_statement(
            main_accountUid,
            main_categoryUid,
            start_iso,
            end_iso
        )
    except Exception as e:
        print('Something went wrong:', e)
        return pd.DataFrame()  # return empty DataFrame on error

    transaction_list = []
    for tx in transactions:
        # get relevant attributes that may be missing
        settled_date_str = tx.get("transactionTime")

        # convert to datetime if exists
        if settled_date_str:  
            settled_date = datetime.strptime(settled_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            display_date = settled_date.strftime("%d/%m/%Y")
        else:
            settled_date = None
            display_date = "N/A"

        transaction_list.append({
            'DateTime': settled_date,                 # keep datetime for sorting
            'Date': display_date,             
            'Counter Party Name': tx['counterPartyName'],
            'Category': tx['spendingCategory'].replace('_', ' ').title(),
            'Amount': tx['sourceAmount']['minorUnits']/100,           
            'Currency': tx['sourceAmount']['currency'],
            'Direction' : tx['direction']
        })

    transactions_df = pd.DataFrame(transaction_list)

    # Sort using the datetime column
    transactions_df = transactions_df.sort_values(by='DateTime', ascending=True).reset_index(drop=True)
    transactions_df = transactions_df[['Date', 
                                       'Counter Party Name', 
                                       'Category', 
                                       'Amount',
                                       'Currency',
                                       'Direction']]

    return transactions_df

if __name__ == "__main__":

    end_date = '05/04/2025'
    start_date = '02/04/2025'

    end_dt = datetime.strptime(end_date, "%d/%m/%Y")
    start_dt = datetime.strptime(start_date, "%d/%m/%Y")

    # Convert to ISO format for the API
    #end_date_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    #start_date_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    #api = StarlingAPI()
    # Get accounts
    #accounts_data = api.get_accounts()
    #accountUid = accounts_data['accounts'][0]['accountUid']
    #categoryUid = accounts_data['accounts'][0]['defaultCategory']
    print(savings_growth_history())

    
