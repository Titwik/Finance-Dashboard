from datetime import datetime, timedelta
from dotenv import load_dotenv
import data #  python file containing financial data
import os
import requests
import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.express as px
import plotly.graph_objs as go 

app = dash.Dash(__name__, suppress_callback_exceptions=True)

def dashboard():
    return html.Div([
        html.H1("My Personal Finance Dashboard", style={"textAlign": "center"}),

        # Row 1
        html.Div([
            html.Div(pocket_money_pie_chart(), style={"width": "50%", "padding": "10px"}),
            html.Div(savings_line_graph(), style={"width": "50%", "padding": "10px"}),           # this function is causing some bloat text in the terminal. Look into it
        ], style={"display": "flex"}),

        # Row 2
        html.Div([
            html.Div(categories_bar_graph(), style={"width": "50%", "padding": "10px"}),
        ], style={"display": "flex"}),

        # Row 3 - Transactions Table
        html.Div([
            html.Div(transactions_table(), 
            style = {
                'width': '100%', 
                'padding' : '10px',
            })
        ], style = {'display' : 'flex'})
    ])

############------GRAPH FUNCTIONS------###############

# visual to create pie chart for current month's expenditure tracking
def pocket_money_pie_chart():

    # update the date if today is the 27th of the month
    today = datetime.now()
    if today.day == 27:
        # update the start date to the 27th of the current month
        start_date = today.replace(day=27)
    else:
        # use the 27th of the previous month
        start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=27)

    # re-format start date to dd/mm/yyyy
    start_date = start_date.strftime("%d/%m/%Y")
    
    # format today's date as dd/mm/yyyy
    today_str = today.strftime("%d/%m/%Y")

    # get the monthly pocket money expenses
    monthly_balance = data.monthly_pocket_money_balance()
    
    # total budget for the month
    total_budget = 300
    monthly_spent = total_budget - monthly_balance

    # add a failsafe so the visual doesn't break if you have over 300 GBP in the account
    if monthly_balance >= 300:
        monthly_spent = 0
    
    # data for pie chart 
    values = [f'{monthly_spent}', f'{monthly_balance}']
    labels = ['Spent', 'Remaining']
    colors = ['#cc0000', '#008000']

    fig = go.Figure(
        data=go.Pie(
            labels=labels,
            values=values,
            marker={'colors': colors},
            textinfo='value',
            texttemplate='£%{value:.2f}'
        )
    )

    fig.update_layout(
        title={
            'text': (
                f"Monthly Pocket Money"
                f"<br><span style='font-size:12px; display:block; margin-top:10px;'>Today's Date: {today_str}</span>"
                f"<br><span style='font-size:12px; display:block; margin-top:10px;'>Start Date: {start_date}</span>"
            ),
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )

    return dcc.Graph(
        id="pocket-money-pie",
        figure=fig
    )

# visual for the savings growth of my account
def savings_line_graph():
    # call the function that returns balances in savings account across months
    df = data.savings_growth_history()  # DataFrame with 'month' and 'amount' columns

    return dcc.Graph(
        figure=go.Figure(
            data=[go.Scatter(
                x=df['month'],         # months on x-axis
                y=df['amount'],        # balance on y-axis
                mode='lines+markers',
                line=dict(color="#000D80"),
                name='Savings Balance'
            )],
            layout=go.Layout(
                title={
                    'text': "Savings Growth",
                    'y': 0.95,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },
                xaxis_title="Month",
                yaxis_title="Balance (£)",
                font=dict(
                    family="Comfortaa, sans-serif"
                )
            )
        )
    )

# visual for most spent categories in a month 
def categories_bar_graph():
    today = datetime.now()
    month = today.strftime("%B").upper()
    year = today.year

    # call the data, and filter for Direction == OUT to track money leaving the account
    df = data.biggest_expenses_in_current_month(month, year) 
    df = df[df['Direction'] == 'OUT']

    fig = go.Figure(
        data=[go.Bar(
            x=df['Category'],
            y=df['Total Expenditure'],
            marker_color="#FF9900",
            name='Amount Spent'
        )]
    )

    fig.update_layout(
        title={
            'text': f"Top Spending Categories This Month ({month.title()} {year})",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Category",
        yaxis_title="Amount (£)",
    )

    fig.add_annotation(
        text=f"Total Spent = £{round(sum(df['Total Expenditure']), 2)}",
        x=0.5, xref="paper",
        y=1.2, yref="paper",
        showarrow=False,
        font=dict(size=15)
    )

    return dcc.Graph(
        id='category-bar-graph',
        figure=fig
    )

# visual for a table containing spending information for a given time period 
def transactions_table():

    # last date of the table is today, start date is start of the month 
    end_date = datetime.now()
    start_date = end_date.replace(day=1)

    df = data.transactions(start_date, end_date)

    return dash_table.DataTable(
        id = 'spending_table',
        columns=[{"name": i, "id" : i} for i in df.columns],
        data=df.to_dict('records'), 
        style_cell={
            "fontFamily": "Comfortaa, sans-serif",
            "textAlign": "left",
            "padding": "5px"
        },
        style_cell_conditional=[
            {"if": {"column_id": "Amount"}, "textAlign": "center"},
            {"if": {"column_id": "Currency"}, "textAlign": "center"},
            {"if": {"column_id": "Direction"}, "textAlign": "center"},
        ],
        page_size=20,
        filter_action="native",
        dropdown={
            "Category": {   # column id
                "options": [
                    {"label": c, "value": c}
                    for c in df["Category"].unique()
                ]
            }
        },
        style_header={
            'fontWeight' : 'bold'
        },
        style_table={'overflowX': 'auto'},  # horizontal scroll if needed
    )

############------CALLBACKS------###############

@app.callback(
    Output("spending_table", "data"),
    Input("category-bar-graph", "clickData")
)
def update_table(clickData):
    
    # if no bar clicked, show current month’s full data
    end_date = datetime.now()
    start_date = end_date.replace(day=1)
    df = data.transactions(start_date, end_date)

    if clickData is None:
        return df.to_dict("records")

    # extract the clicked category
    category_clicked = clickData["points"][0]["x"]

    # filter dataframe
    df_filtered = df[df["Category"] == category_clicked]

    return df_filtered.to_dict("records")

app.layout = dashboard()
if __name__ == "__main__":
    app.run(debug=True)
    