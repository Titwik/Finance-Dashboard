from datetime import datetime, timedelta
from dotenv import load_dotenv
import data #  python file containing financial data
import os
import requests
import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objs as go

# function for the overall dashboard layout
def dashboard():
    return html.Div([
        html.H1("My Personal Finance Dashboard", style={"textAlign": "center"}),

        # === Row 1 === (two visuals side by side)
        html.Div([
            html.Div(pocket_money_pie_chart(), style={"width": "50%", "padding": "10px"}),
            html.Div(savings_line_graph(), style={"width": "50%", "padding": "10px"}),
        ], style={"display": "flex"}),

        # === Row 2 === (three visuals side by side)
        html.Div([
            html.Div(categories_bar_graph(), style={"width": "50%", "padding": "10px"}),
        ], style={"display": "flex"}),

        # === Row 3 === (single full-width visual)
#        html.Div([
#            html.Div(net_worth_line_chart(), style={"width": "100%", "padding": "10px"})
#        ], style={"display": "flex"}),
    ])


# function to create pie chart for current month's expenditure tracking
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

    # get the monthly pocket money expenses
    monthly_balance = data.monthly_pocket_money_balance()
    
    # total budget for the month
    total_budget = 300
    monthly_spent = total_budget - monthly_balance
    
    # data for pie chart 
    values = [f'{monthly_spent}', f'{monthly_balance}']
    labels = ['Spent', 'Remaining']
    colors = ['#cc0000', '#008000']

    return dcc.Graph(
        figure=go.Figure(
            data=[go.Pie(
                labels=labels,
                values=values,
                marker={'colors': colors}, # Set custom colors here
                textinfo='value',           # Display the flat values
                texttemplate='£%{value:.2f}'
            )],
            layout=go.Layout(
                title={
                    'text': f"Monthly Pocket Money<br><sup>Start: {start_date}</sup>", # this date needs to be automatically updated
                    'y': 0.95,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                }
            )
        )
    )

# function for the savings growth of my account
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
            )
        )
    )

# function for most spent categories in a month 
def categories_bar_graph():
    today = datetime.now()
    month = today.strftime("%B").upper()
    year = today.year

    df = data.biggest_expenses_in_current_month(month, year) ###### FILTER ONLY DIRECTION == OUT

    return dcc.Graph(
        figure=go.Figure(
            data=[go.Bar(
                x=df['Category'],
                y=df['Total Expenditure'],
                marker_color="#FF9900",
                name='Amount Spent'
            )],
            layout=go.Layout(
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
        )
    )


app = dash.Dash(__name__)
app.layout = dashboard()

if __name__ == "__main__":
    app.run(debug=True)
    