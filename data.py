import os
import json
import time
import requests
import pandas as pd
import datetime as dt
#import yfinance as yf
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta

# ===================== CREDENTIALS ===================== #

load_dotenv()  # Loads variables from .env into the environment
api_username = os.getenv("investment_api_key")
api_password = os.getenv("investment_api_secret")
mongo_uri = os.getenv("MONGO_URI")  
db_name = "finance_dashboard"

# initialize mongoDB
client = MongoClient(mongo_uri)
db = client[db_name]

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

# ===================== BANK API ===================== #

# define a function for the monthly pocket money and groceries expenses
def monthly_balance():

    # call the API class
    api = StarlingAPI()

    # account data
    account_data = api.get_accounts()
    accountUid = account_data['accounts'][0]['accountUid']

    def pocket_money():

        '''
        Logic: I have 180 GBP for casual, guilt-free spending. Check if category is NOT investments, rent, utilities etc and subtract from 180 GBP
        '''
        pocket_money_allowance = 18000 # in minorUnits

        remaining_pocket_money = api.get_balance(accountUid)['effectiveBalance']['minorUnits']
        if remaining_pocket_money > 18000:
            remaining_pocket_money = 18000 # prevents the visual from breaking
        
        total_pocket_money_spent = pocket_money_allowance - remaining_pocket_money

        return remaining_pocket_money/100, total_pocket_money_spent/100
    
    def grocery_balance():

        """
        Logic: I have 120 GBP for groceries, so 100% of the visual should be 120. I will then deduct from 120 any amount that is classed as 'groceries' in the transaction statement category.
        """

        #groceries_allowance = 12000 # in minorUnits

        spaces = api.get_savings_spaces(accountUid)['savingsGoals']
        for space in spaces:
            if space['name'] == 'Groceries':
                grocery_space = space
                break
        
        #savingUid = grocery_space['savingsGoalUid']
        groceries_allowance = grocery_space['target']['minorUnits']
        remaining_groceries = grocery_space['totalSaved']['minorUnits']
        if remaining_groceries > groceries_allowance:
            remaining_groceries = groceries_allowance # prevents visual from breaking
        total_groceries_spent = groceries_allowance - remaining_groceries
        
        return remaining_groceries/100, total_groceries_spent/100
    
    return pocket_money(), grocery_balance()

# function to track growth of savings account
def savings_growth_history():
    
    """
    data to track the growth of savings account over time
    """

    api = StarlingAPI()
    collection = db['savings']

    # Get accounts
    accounts_data = api.get_accounts()
    savings_accountUid = accounts_data['accounts'][1]['accountUid']
    savings_categoryUid = accounts_data['accounts'][1]['defaultCategory']

    # Get current account balance (assume this is the balance at 'today')
    current_balance_minor = api.get_balance(savings_accountUid)['effectiveBalance']['minorUnits']
    current_balance = current_balance_minor / 100  # convert to pounds

    # Get transactions
    today = dt.datetime.now(dt.UTC)
    if collection.count_documents({}) == 0:
        start_date = dt.datetime(2025, 7, 1, 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    end_date = today.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    transactions = api.get_transaction_statement(
        savings_accountUid,
        savings_categoryUid,
        start_date,
        end_date
    )
    
    # assign feedItemUid as _id
    for tx in transactions:
        tx["_id"] = tx["feedItemUid"]

    # insert ignoring duplicates
    if transactions:
        existing_ids_cursor = collection.find(
            {"_id": {"$in": [t["_id"] for t in transactions]}},
            {"_id": 1}
        )
        existing_ids = {doc["_id"] for doc in existing_ids_cursor}
        new_transactions = [t for t in transactions if t["_id"] not in existing_ids] if False else [t for t in transactions if t["_id"] not in existing_ids]
        if new_transactions:
            try:
                collection.insert_many(new_transactions)
            except Exception as e:
                print(f"[savings_growth_history] Failed to insert transactions: {e}")

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
    Returns a DataFrame of the largest spending categories for the given month and year,
    including money spent from the 'Groceries' savings space.
    """

    api = StarlingAPI()

    # Get accounts
    accounts_data = api.get_accounts()
    accountUid = accounts_data['accounts'][0]['accountUid']

    # Get categories for the month
    categoryUid = api.get_monthly_categories(accountUid, int(year), month.upper())

    # get the amount spent on groceries
    _, groceries = monthly_balance()
    groceries_spent = groceries[1]

    if len(categoryUid['breakdown']) == 0 and groceries_spent == 0:
        print('No account activity for the chosen time.')
        return None

    # Convert to DataFrame
    category_list = [
        {
            'Category': cat['spendingCategory'].title().replace("_", " "),
            'Total Expenditure': cat['netSpend'],
            'Direction': cat['netDirection']
        }
        for cat in categoryUid['breakdown']
    ]

    category_df = pd.DataFrame(category_list)

    # Remove unwanted categories
    category_df = category_df[~category_df['Category'].isin(['Saving', 'Investments'])]

    # Add Groceries from the savings space
    if groceries_spent > 0:
        if 'Groceries' in category_df['Category'].values:
            category_df.loc[category_df['Category'] == 'Groceries', 'Total Expenditure'] += groceries_spent
        else:
            category_df = pd.concat([
                category_df,
                pd.DataFrame([{'Category': 'Groceries', 'Total Expenditure': groceries_spent, 'Direction': 'OUT'}])
            ], ignore_index=True)

    # Sort by expenditure
    category_df = category_df.sort_values(
        by=["Direction", "Total Expenditure"], 
        ascending=[False, False]
    )

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
    accountUid = accounts_data['accounts'][0]['accountUid']
    main_categoryUid = accounts_data['accounts'][0]['defaultCategory']

    # Fetch spaces once
    spaces = api.get_savings_spaces(accountUid)['savingsGoals']

    def get_space_uid(spaces, name):
        for s in spaces:
            if s['name'] == name:
                return s['savingsGoalUid']
        return None

    # Define categories you want to fetch from
    categories = {
        "general": main_categoryUid,
        "groceries": get_space_uid(spaces, "Groceries"),
        "bills": get_space_uid(spaces, "Bills"),
    }

    # Fetch all transactions in a loop
    transactions = []
    for cat_uid in categories.values():
        if cat_uid:  # ignore if not found
            tx = api.get_transaction_statement(
                accountUid,
                cat_uid,
                start_iso,
                end_iso
            )
            transactions.extend(tx)

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

# ===================== TRADING212 API ===================== #

# get current portfolio data
def portfolio():
    
    url = "https://live.trading212.com/api/v0/equity/portfolio"
    response = requests.get(url, auth=(api_username, api_password))
    response.raise_for_status()
    
    # Data is guaranteed to be the list of instruments from the API call
    data = response.json()
    
    # Add timestamp to each instrument
    for instrument in data:
        instrument['timestampAdded'] = dt.datetime.now(dt.UTC)

    return data

# get historical transactions from the last year
def investment_transactions():
    base_url = "https://live.trading212.com"
    endpoint = "/api/v0/equity/history/orders"
    current_path = endpoint
    all_orders = []
    transaction_coll = db['investment_transactions']

    # Only set a cutoff date if the collection is empty
    three_months_ago = None
    if transaction_coll.count_documents({}) > 0:
        three_months_ago = datetime.now() - timedelta(days=30 * 3)  # 3 months back

    while current_path:
        url = base_url + current_path
        response = requests.get(url, auth=(api_username, api_password))
        response.raise_for_status()
        data = response.json()

        if "items" in data and isinstance(data["items"], list):
            should_stop = False

            for order in data["items"]:
                date_created_str = order.get('dateCreated')

                # Apply cutoff only if set
                if three_months_ago and date_created_str:
                    transaction_date = datetime.strptime(date_created_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    if transaction_date < three_months_ago:
                        should_stop = True
                        break

                order["transaction_type"] = order['order']['side']

                all_orders.append(order)

            if should_stop:
                break

        current_path = data.get("nextPagePath")
        if not current_path:
            break

    def save_to_mongo(orders):
        """
        Saves new, unique orders to a MongoDB collection.

        :param orders: A list of transaction dictionaries (from your data).
        :param transaction_coll: The MongoDB collection object (e.g., pymongo.collection.Collection).
        """
        if not orders:
            # print("No transactions to process.")
            return

        # Find the IDs of all orders that are NOT already in the database
        new_orders = []
        for o in orders:
            order_id = o["order"]["id"]
            
            # Check if an order with this ID already exists in the MongoDB collection
            if not transaction_coll.find_one({"id": order_id}):
                o["id"] = order_id
                new_orders.append(o)

        if new_orders:
            transaction_coll.insert_many(new_orders)

    save_to_mongo(all_orders)

# net deposit must be saved every day, so that net P/L can be tracked per day.
def portfolio_performance():

    transaction_coll = db["investment_transactions"]
    conversion_rate_usd_to_gbp = 0.75  # update if needed

    # save any new transactions to DB
    investment_transactions()
    #time.sleep(3)

    # get net deposits 
    net_deposit_result = list(transaction_coll.aggregate([
        {
            "$group": {
                "_id": None,
                "totalNetValue": {
                    "$sum": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": { "$eq": ["$transaction_type", "SELL"] },
                                    "then": { "$multiply": [ { "$ifNull": ["$fill.walletImpact.netValue", 0] }, -1 ] }
                                }
                            ],
                            "default": { "$ifNull": ["$fill.walletImpact.netValue", 0] }
                        }
                    }
                }
            }
        }
    ]))

    net_deposit = net_deposit_result[0]["totalNetValue"] if net_deposit_result else 0

    # ------------------------------ #

    # get current portfolio value
    portfolio_data = portfolio()

    portfolio_value = 0
    for ins in portfolio_data:
        ticker = ins['ticker']
        current_price = ins['currentPrice']
        shares = ins['quantity']

        if "_US_" in ticker:
            current_price *= conversion_rate_usd_to_gbp
        elif "SGLNl_EQ" in ticker:
            current_price /= 100

        portfolio_value += shares * current_price

    portfolio_value = round(portfolio_value, 2)

    # today's latest snapshot
    insert_dict = {
        'netDeposit': round(net_deposit,2),
        'portfolioValue': round(portfolio_value, 2),
        'portfolio': [
        {
            'ticker': ins['ticker'],
            'quantity': ins['quantity'],
            'priceGBP': round(
                ins['currentPrice'] * conversion_rate_usd_to_gbp if "_US_" in ins['ticker'] else
                ins['currentPrice'] / 100 if "SGLNl_EQ" in ins['ticker'] else
                ins['currentPrice'], 2
            )
        } for ins in portfolio_data
    ],
        'timestampAdded': dt.datetime.now(dt.timezone.utc)
    }

    return insert_dict

# portfolio + networth snapshot 
def snapshot(latest_entry):

    portfolio_coll = db['portfolio_value']
    savings_coll = db['savings']
    
    today = dt.datetime.now(dt.UTC).date()
    
    if latest_entry['timestampAdded'].date() == today:
        portfolio_coll.delete_one({'_id': latest_entry['_id']})

    # get savings data 
    savings_data = list(savings_coll.find())

    savings_value = 0
    for data in savings_data:

        # compute the sum value
        if data['direction'] == 'IN':
            savings_value += data['sourceAmount']['minorUnits']/100
        
        elif data['direction'] == 'OUT':
            savings_value -= data['sourceAmount']['minorUnits']/100 

    snapshot = portfolio_performance()
    snapshot['savingsTotal'] = round(savings_value, 2)
    snapshot['netWorth'] = round(savings_value + snapshot['portfolioValue'], 2)

    # save to mongodb
    portfolio_coll.insert_one(snapshot)
    
    snapshot['timestampAdded'] = str(snapshot['timestampAdded'])
    snapshot['_id'] = str(snapshot['_id'])
    #print('Inserted to DB')

    return snapshot

# ===================== EXECUTION SCRIPT ===================== #
if __name__ == "__main__":

    print(portfolio_performance())
