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


# Execution script
if __name__ == "__main__":
    api = StarlingAPI()

    # Step 1: Get accounts first
    accounts_data = api.get_accounts()

    # Step 2: Extract accountUid and categoryUid from main account
    main_accountUid = accounts_data['accounts'][0]['accountUid']
    main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # Step 3: Get balance for that account
    #balance_data = api.get_balance(main_accountUid)

    # Step 4: Pretty print the balance JSON
    #print(f"The balance in your Main account is £{balance_data['effectiveBalance']['minorUnits']/100:.2f}")

    # Step 5: Get transaction statement for the last month
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  
    transactions = api.get_transaction_statement(
        main_accountUid, 
        main_categoryUid, 
        start_date.isoformat() + "Z", 
        end_date.isoformat() + "Z"
    )   
    # Step 6: Print the transactions
    for transaction in transactions:
        transaction_iso_time = transaction['transactionTime']
        dt = datetime.strptime(transaction_iso_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        transaction_date = dt.strftime("%d/%m/%Y")

        print(f"{transaction_date}: {transaction['counterPartyName']} - £{transaction['amount']['minorUnits']/100:.2f}")
