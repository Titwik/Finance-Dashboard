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

        # container for the two visuals
        html.Div([
            # Pie chart box
            html.Div(
                pocket_money_pie_chart(),
                style={
                    "width": "50%",       # half the container width
                    "padding": "10px",
                    "boxSizing": "border-box"
                }
            ),

            # Savings line graph box
            html.Div(
                savings_line_graph(),
                style={
                    "width": "50%",       # half the container width
                    "padding": "10px",
                    "boxSizing": "border-box"
                }
            ),
        ], style={"display": "flex"})  # flex container makes them side by side
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


app = dash.Dash(__name__)
app.layout = dashboard()

if __name__ == "__main__":
    app.run(debug=True)