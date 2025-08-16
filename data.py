import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()  # Loads variables from .env into the environment

class StarlingAPI:
    def __init__(self):
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
    
    # function to get transation statement
    def get_transaction_statement(self, account_uid, category_uid, start_date, end_date):
        url = f"{self.base_url}/feed/account/{account_uid}/category/{category_uid}/transactions-between?minTransactionTimestamp={start_date}&maxTransactionTimestamp={end_date}"
        response = requests.get(url, headers=self.headers)
        return response.json()["feedItems"] 

# define a function for the monthly pocket money expenses
def monthly_pocket_money_balance():
    api = StarlingAPI()

    # get accounts
    accounts_data = api.get_accounts()

    # extract accountUid and categoryUid from main account
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # get balance for that account
    main_balance = api.get_balance(main_accountUid)['effectiveBalance']['minorUnits'] / 100

    return main_balance

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

if __name__ == "__main__":
    # Example usage
    print(f"Main account balance: £{monthly_pocket_money_balance():.2f}")