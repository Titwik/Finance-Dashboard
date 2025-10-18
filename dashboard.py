import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import data #  python file containing financial data
import os
import requests
import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.express as px
import plotly.graph_objs as go 

app = dash.Dash(__name__)

# dashboard files
def dashboard():
    return html.Div([
        html.H1("Personal Finance Dashboard", style={"textAlign": "center"}),

        # Row 1: Pocket Money & Groceries Donuts side by side
        html.Div([
            html.Div(pocket_money_donut_chart(), style={"width": "50%", "padding": "10px"}),
            html.Div(groceries_donut_chart(), style={"width": "50%", "padding": "10px"})
        ], style={"display": "flex"}),

        html.Div([
            html.Div(savings_line(), style={"width": "50%", "padding": "10px"})
        ], style={"display": "flex"})
    ])

#---------------- GRAPH FUNCTIONS ----------------#
# pocket money donut 
def pocket_money_donut_chart():

    pocket_money, _ = data.monthly_balance()
    labels = ['Remaining', 'Spent']
    #values = [pocket_money[0], pocket_money[1]]  
    values = [100,90]
    colors = ['#008000', '#cc0000']  

    fig = go.Figure(
        data=[go.Pie(
            labels=labels,
            values=values,
            sort = False,
            textinfo='label+percent',
            hole=0.4,
            marker=dict(
                colors=colors,
                line=dict(color='#000000', width=1)
            )
        )]
    )

    fig.update_layout(
        title=dict(
            text='Pocket Money',
            x=0.5,
            xanchor='center',
            font=dict(size=22, family='Arial', color='#333')
        )
    )

    return dcc.Graph(figure=fig, id='pocket_money_donut')

# groceries donut 
def groceries_donut_chart():

    _, groceries = data.monthly_balance()
    labels = ['Remaining', 'Spent']
    values = [groceries[0], groceries[1]]  
    colors = ['#008000', '#cc0000']  

    fig = go.Figure(
        data=[go.Pie(
            labels=labels,
            values=values,
            sort = False,
            textinfo='label+percent',
            hole=0.4,
            marker=dict(
                colors=colors,
                line=dict(color='#000000', width=1)
            )
        )]
    )

    fig.update_layout(
        title=dict(
            text='Groceries',
            x=0.5,
            xanchor='center',
            font=dict(size=22, family='Arial', color='#333')
        )
    )

    return dcc.Graph(figure=fig, id='groceries_donut')

# savings line
import plotly.graph_objects as go
from dash import dcc
import pandas as pd

def savings_line():
    # get the data
    savings_df = data.savings_growth_history()

    # convert dates to datetime
    savings_df['display_date'] = pd.to_datetime(savings_df['display_date'], format='%d/%m/%Y')

    x_values = savings_df['display_date'].to_list()
    y_values = savings_df['absolute_balance'].to_list()

    # Create the figure with improved design
    fig = go.Figure(
        data=go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',
            line=dict(color='#1f77b4', width=3, shape='spline'),  # smooth line
            marker=dict(size=10, color='#1f77b4', symbol='circle', line=dict(width=2, color='white')),
            hovertemplate='%{x|%b %Y}<br>Balance: £%{y:,.2f}<extra></extra>'  # cleaner hover
        )
    )

    fig.update_layout(
        title=dict(
            text='Savings',
            x=0.5,
            xanchor='center',
            font=dict(size=22, family='Arial', color='#333')
        ),
        xaxis=dict(
            title='Month',
            showgrid=True,
            gridcolor='rgba(200,200,200,0.2)',
            tickformat='%b %Y',
            tickangle=-45,
            showline=True,
            linecolor='rgba(200,200,200,0.8)',
            zeroline=False
        ),
        yaxis=dict(
            title='Balance (£)',
            showgrid=True,
            gridcolor='rgba(200,200,200,0.2)',
            showline=True,
            linecolor='rgba(200,200,200,0.8)',
            zeroline=False,
            tickprefix='£'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        showlegend=False,
        margin=dict(l=60, r=20, t=80, b=80)
    )

    # Optional: Add a subtle gradient fill under the line for style
    # Add gradient-like effect without forcing y=0
    fig.add_traces(go.Scatter(
        x=x_values,
        y=y_values,
        mode='lines',
        line=dict(color='rgba(31, 119, 180, 0)'),  # invisible line
        fill='none',  # do NOT fill to zero
        showlegend=False,
        hoverinfo='skip'
    ))


    return dcc.Graph(figure=fig, id='savings_line')

    

app.layout = dashboard()
if __name__ == "__main__":
    app.run(debug=True)