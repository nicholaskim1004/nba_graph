import sqlite3
import pandas as pd
import numpy as np
import dash

from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query, con)

team_df = pd.DataFrame(teams.get_teams())
seasons = pageranks['season'].unique()

dash.register_page(__name__, path='/yoy', name='Year over Year', order = 2)

layout = html.Div([
    html.Label('Node:',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='node_options',
                    options=[],
                    value=0,
                    style={"fontFamily": 'sans-serif','width': '30%'}),
    html.Br(),
    dcc.Graph(
        id = 'yoy_change',
        figure = []
    )
])

#update the options to the node list based on the team and season
callback(
    Output('node_options','options'),
    Output('node_options','value'),
    Input('team-dropdown','value'),
    Input('season-slider','value')
)
def update_node_list_options(selected_team, selected_season):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()

    pageranks_yr = pageranks[
                                (pageranks['season'].astype(int) <= selected_season)&
                                (pageranks['team_id']==teamid)
                            ]
    options = pageranks_yr['node_name'].unique().sort_values()
    value = options[0]
    
    return options, value


cursor.close()
con.close()