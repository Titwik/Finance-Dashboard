import datetime as dt
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import data
import os
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.graph_objs as go
from pymongo import MongoClient

# Load environment
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
db_name = "finance_dashboard"
client = MongoClient(mongo_uri)
db = client[db_name]

app = dash.Dash(__name__)

# ---------- GLOBAL DARK STYLE ----------
DARK_BG = "#121212"
CARD_BG = "#1E1E1E"
TEXT_COLOR = "#E0E0E0"
ACCENT = "#00E3CC"
FONT_FAMILY = "Poppins, sans-serif"

app.title = "Personal Finance Dashboard"
app.css.config.serve_locally = True

# ---------- REUSABLE STYLES ----------
CARD_STYLE = {
    "backgroundColor": CARD_BG,
    "padding": "20px",
    "borderRadius": "20px",
    "boxShadow": "0 4px 15px rgba(0, 0, 0, 0.4)",
    "color": TEXT_COLOR,
    "textAlign": "center",
    "flex": "1",
}

GRAPH_STYLE = {"backgroundColor": CARD_BG, "borderRadius": "20px", "padding": "20px"}

# ---------- LAYOUT ----------
def dashboard():
    return html.Div(
        style={
            "backgroundColor": DARK_BG,
            "minHeight": "100vh",
            "padding": "20px 40px",
            "fontFamily": FONT_FAMILY,
            "color": TEXT_COLOR,
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
        },
        children=[

            dcc.Store(id='monthly-transactions-store'),
            html.H1(
                "Personal Finance Dashboard",
                style={
                    "textAlign": "center",
                    "color": ACCENT,
                    "marginBottom": "20px",
                    "fontSize": "32px",
                    "fontWeight": "600",
                },
            ),

            # ---------- FIRST ROW ----------
            html.Div(
                [
                    html.Div(pocket_money_donut_chart(), style=GRAPH_STYLE),
                    html.Div(groceries_donut_chart(), style=GRAPH_STYLE),
                    html.Div(categories_bar(), style=GRAPH_STYLE),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "2fr 2fr 5fr",
                    "gap": "20px",
                    "width": "100%",
                    "maxWidth": "1800px",
                    "marginBottom": "20px",
                },
            ),

            # ---------- SECOND ROW ----------
            html.Div(
                [
                    html.Div(savings_line(), style=GRAPH_STYLE),

                    html.Div(
                        net_worth_card(),
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "width": "100%",
                        },
                    ),

                    html.Div(portfolio_line(), style=GRAPH_STYLE),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "5fr 2fr 5fr",
                    "gap": "20px",
                    "width": "100%",
                    "maxWidth": "1800px",
                    "marginBottom": "20px",
                },
            ),

            # ---------- THIRD ROW: TRANSACTIONS TABLE ----------
            html.Div(
                [
                    html.Div(
                        transactions_table(),
                        style={
                            "width": "100%",
                            "maxWidth": "1800px",
                        },
                    )
                ],
                style={
                    "width": "100%",
                    "display": "flex",
                    "justifyContent": "center",
                },
            ),
        ],
    )


# ---------- DARK MODE PLOTLY STYLES ----------
def dark_layout(fig, title):
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, x=0.5, font=dict(size=22, color=ACCENT)),
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR, family=FONT_FAMILY),
        hovermode="x unified",
        margin=dict(l=60, r=20, t=80, b=80),
        xaxis=dict(showgrid=False, linecolor="#333"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
        showlegend=False,
    )
    return fig


# ---------- CHARTS ----------
def pocket_money_donut_chart():
    pocket_money, _ = data.monthly_balance()
    labels = ["Remaining", "Spent"]
    values = [pocket_money[0], pocket_money[1]]
    colors = ["#26A69A", "#EF5350"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors, line=dict(color="#000", width=1)),
                textinfo="label+percent",
            )
        ]
    )
    return dcc.Graph(figure=dark_layout(fig, "Pocket Money"), id='pocket-donut')

def groceries_donut_chart():
    _, groceries = data.monthly_balance()
    labels = ["Remaining", "Spent"]
    values = [groceries[0], groceries[1]]
    colors = ["#26A69A", "#EF5350"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors, line=dict(color="#000", width=1)),
                textinfo="label+percent",
            )
        ]
    )
    return dcc.Graph(figure=dark_layout(fig, "Groceries"), id='groceries-donut')

def savings_line():
    df = data.savings_growth_history()
    df["display_date"] = pd.to_datetime(df["display_date"], format="%d/%m/%Y")

    fig = go.Figure(
        go.Scatter(
            x=df["display_date"],
            y=df["absolute_balance"],
            mode="lines+markers",
            line=dict(color="#00E3CC", width=3, shape="spline"),
            marker=dict(size=8, color="#00E3CC", line=dict(width=2, color="black")),
            hovertemplate="%{x|%b %Y}<br>Balance: £%{y:,.2f}<extra></extra>",
        )
    )
    return dcc.Graph(
        figure=dark_layout(fig, "Savings Growth"),
        style={'height': '400px'}
        )

def portfolio_line():

    # add a snapshot to the DB today if not done so yet
    today = dt.datetime.now(dt.timezone.utc).date()
    latest_entry = db['portfolio_value'].find_one(
        sort=[('timestampAdded', -1)]
    )

    if latest_entry and latest_entry['timestampAdded'].date() < today:
        data.snapshot(latest_entry)

    portfolio_df = pd.DataFrame(list(db["portfolio_value"].find().sort("timestampAdded", 1)))
    portfolio_df["timestampAdded"] = pd.to_datetime(portfolio_df["timestampAdded"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=portfolio_df["timestampAdded"],
            y=portfolio_df["netDeposit"],
            mode="lines+markers",
            name="Net Deposit",
            line=dict(color="#26A69A", width=3),
            marker=dict(size=8, color="#26A69A", line=dict(width=2, color="black")),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=portfolio_df["timestampAdded"],
            y=portfolio_df["portfolioValue"],
            mode="lines+markers",
            name="Portfolio Value",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8, color="#FFA726", line=dict(width=2, color="black")),
        )
    )
    return dcc.Graph(
        figure=dark_layout(
            fig, "Portfolio Performance"),
            style={'height': '400px'}
            )

def categories_bar():
    current_month = datetime.now().strftime("%B")
    current_year = datetime.now().year
    df = data.biggest_expenses_in_current_month(current_month, current_year)
    df = df[df["Direction"] == "OUT"].sort_values("Total Expenditure", ascending=True)

    fig = go.Figure(
        data=go.Bar(
            x=df["Category"],
            y=df["Total Expenditure"],
            text=[f"£{v:,.2f}" for v in df["Total Expenditure"]],
            textposition='auto',
            marker=dict(
                color='#FF7043',  # modern dashboard color
                line=dict(color='rgba(0,0,0,0.1)', width=1)
            ),
            hovertemplate='%{x}<br>Total: £%{y:,.2f}<extra></extra>'
        )
    )

    return dcc.Graph(figure=dark_layout(fig, f"Top Expenses in {current_month} {current_year}"), id='categories-bar')

# ---------- KPI CARD ----------
def net_worth_card():
    coll = db["portfolio_value"]
    entries = list(coll.find().sort("timestampAdded", -1).limit(2))
    if not entries:
        return html.Div("No Data Available", style=CARD_STYLE)

    latest, prev = entries[0], entries[1] if len(entries) > 1 else None
    net_worth = latest.get("netWorth", 0)
    change = net_worth - (prev.get("netWorth", 0) if prev else 0)
    trend_color = "#66BB6A" if change >= 0 else "#EF5350"

    return html.Div(
        [
            html.H4("Net Worth", style={"color": ACCENT}),
            html.H2(f"£{net_worth:,.0f}", style={"fontSize": "48px", "color": "white"}),
            html.P(
                f"{'▲' if change >= 0 else '▼'} £{abs(change):,.0f}",
                style={"color": trend_color, "fontWeight": "600"},
            ),
        ],
        style={
            **CARD_STYLE, 
            "display": "flex",              
            "flexDirection": "column",      
            "justifyContent": "center",     
        }
    )

# ---------- TRANSACTIONS TABLE ----------
def transactions_table():

    # create empty transactions df
    df = pd.DataFrame(columns=['Date', 'Counter Party Name', 'Category', 'Amount', 'Currency', 'Direction'])

    # Convert any datetime columns
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%d/%m/%Y %H:%M")

    return dash_table.DataTable(
        id="transactions-table",
        columns=[{"name": col, "id": col} for col in df.columns],
        data=[],

        # ---------- DARK THEME ----------
        style_table={
            "backgroundColor": CARD_BG,
            "padding": "20px",
            "borderRadius": "20px",
            "maxHeight": "400px",
            "overflowX": "scroll",
            "boxShadow": "0 4px 15px rgba(0, 0, 0, 0.4)",
        },

        # ----- HEADER (CENTER ALIGN) -----
        style_header={
            "backgroundColor": "#1E1E1E",
            "color": ACCENT,
            "fontWeight": "bold",
            "border": "1px solid #333",
            "fontFamily": FONT_FAMILY,
            "textAlign": "center",     # <-- CENTER ALIGN HEADERS
        },

        # ----- FILTER ROW DARK THEME -----
        style_filter={
            "backgroundColor": "#111",
            "color": TEXT_COLOR,
            "border": "1px solid #333",
            "fontFamily": FONT_FAMILY,
        },

        # ----- DATA CELLS (LEFT ALIGN) -----
        style_data={
            "backgroundColor": CARD_BG,
            "color": TEXT_COLOR,
            "border": "1px solid #333",
            "fontFamily": FONT_FAMILY,
            "textAlign": "left",        # <-- LEFT ALIGN DATA
        },

        
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#181818",
            },
            { "if": {"column_id": "Amount"}, "textAlign": "center" },
            { "if": {"column_id": "Currency"}, "textAlign": "center" },
            { "if": {"column_id": "Direction"}, "textAlign": "center" },
        ],

        style_cell={
            "padding": "8px",
            "minWidth": "120px",
            "whiteSpace": "normal",
            "fontSize": "14px",
        },

        filter_options={"case": "insensitive"},
        fixed_rows={"headers": True},


        # ---------- EXTRA FEATURES ----------
        sort_action="native",
        filter_action="native",
        page_action="none",
        page_size=15,
    )

# ---------- CALLBACKS ----------
@app.callback(
    Output("monthly-transactions-store", "data"),
    Input("monthly-transactions-store", "data"),
    prevent_initial_call=False  # run on page load
)
def load_monthly_data(_):

    today = dt.datetime.today()
    start_date = today.replace(day=1)
    end_date = (today.replace(day=1) + pd.DateOffset(months=1)) - pd.DateOffset(days=1)

    start = f"{start_date.day}/{start_date.month}/{start_date.year}"
    end = f"{end_date.day}/{end_date.month}/{end_date.year}"

    df = data.transactions(start, end)

    # convert datetimes
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%d/%m/%Y %H:%M")

    return df.to_dict("records")

@app.callback(
    Output('transactions-table', 'data'),
    [
        Input('categories-bar', 'clickData'),
        Input('categories-bar', 'relayoutData'),
        Input('monthly-transactions-store', 'data')
    ]
)
def update_table(bar_click, relayout, store_data):

    if store_data is None:
        return []

    df = pd.DataFrame(store_data)
    filtered = df.copy()

    # --- RESET FILTER ---
    if relayout and "xaxis.autorange" in relayout:
        # Double click happened → Return full table
        return df.to_dict("records")

    # --- APPLY CATEGORY FILTER ---
    if bar_click:
        category = bar_click['points'][0]['x']
        filtered = filtered[filtered["Category"] == category]

    return filtered.to_dict("records")


# ---------- APP LAYOUT ----------
app.layout = dashboard()

if __name__ == "__main__":
    app.run(debug=True)
