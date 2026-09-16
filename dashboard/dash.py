import sqlite3
import pandas as pd

from dash import Dash, html, dcc

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_sh = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_sh, con)

app = Dash()

