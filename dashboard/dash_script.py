import sqlite3
import pandas as pd

from dash import Dash, html, dcc

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_sh = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_sh, con)

app = Dash()

app.layout = html.Div([
    html.H1("NBA GRAPH NETWORKS"),
    html.Div(
        "How are NBA Offenses different? Do teams follow a similar pattern? "
        "Do strategies change in the Playoffs? All these questions can be "
        "answered using network structure! This dashboard will display the "
        "results from a network for a given season and team.",
        style={
            "fontSize": "20px",
            "marginTop": "0px"
        }
    )
])

if __name__ == "__main__":
    app.run(debug=True)