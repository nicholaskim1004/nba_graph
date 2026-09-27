import sqlite3
import pandas as pd
import numpy as np
import dash
import plotly.express as px

from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query, con)

team_df = pd.DataFrame(teams.get_teams())
seasons = pageranks['season'].unique()

#creating a number for seasons
sorted_seasons = np.sort(seasons)  # e.g. ['2018-19', '2019-20', '2020-21', ...]
season_to_idx = {s: i for i, s in enumerate(sorted_seasons)}

pageranks['season_idx'] = pageranks['season'].map(season_to_idx)

#to make it numerical for plot
pageranks['season_start'] = pageranks['season'].str.split('-').str[0].astype(int)
#creating yoy change
pageranks = pageranks.sort_values(by=['player_id', 'season_idx']).reset_index(drop=True)
pageranks['pagerank_yoy_diff'] = pageranks.groupby('player_id')['pagerank'].diff()

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
        figure = {}
    ),
    html.Br(),
    dcc.Graph(id='yoy_heatmap', figure={})
])

#update the options to the node list based on the team and season
@callback(
    Output('node_options','options'),
    Output('node_options','value'),
    Input('team-dropdown','value'),
    Input('season-slider','value')
)
def update_node_list_options(selected_team, selected_season):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()
    pageranks_yr = pageranks[
                                (pageranks['season_idx'] <= selected_season)&
                                (pageranks['team_id']==teamid[0])
                            ]
    options = pageranks_yr['node_name'].sort_values().unique()
    value = options[0]
    
    return options, value

#now to create figure
@callback(
    Output('yoy_change','figure'),
    Input('team-dropdown','value'),
    Input('season-slider','value'),
    Input('node_options','value')
)
def update_yoy_fig(selected_team, selected_season, selected_node):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()
    
    node_yoy = pageranks[
                    (pageranks['season_idx']<=selected_season)&
                    (pageranks['team_id']==teamid[0])&
                    (pageranks['node_name']==selected_node)
                ]
    
    fig = px.line(node_yoy.loc[:,['season_start','pagerank']], x='season_start', y='pagerank', title='Pagerank over Time', markers=True)
    fig.update_layout(width=800, height=600)
    fig.update_xaxes(dtick=1)
    return fig

@callback(
    Output('yoy_heatmap', 'figure'),
    Input('team-dropdown', 'value'),
    Input('season-slider', 'value')
)
def update_yoy_heatmap(selected_team, selected_season):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()

    team_yoy = pageranks[
        (pageranks['season_idx'] <= selected_season) &
        (pageranks['team_id'] == teamid[0])
    ]

    # pivot: rows = node_name, cols = season_start, values = yoy diff
    valid_seasons = sorted(team_yoy['season_start'].unique())

    pivot = team_yoy.pivot_table(
        index='node_name',
        columns='season_start',
        values='pagerank_yoy_diff',
        aggfunc='mean',
        observed=True
    ).reindex(columns=valid_seasons)

    pivot.columns = pivot.columns.astype(str)

    fig = px.imshow(
        pivot,
        color_continuous_scale='RdBu',
        color_continuous_midpoint=0,
        aspect='auto',
        labels=dict(x='Season', y='Player', color='YoY Δ Pagerank'),
        title='Year-over-Year Pagerank Change by Player'
    )

    fig.update_xaxes(
        type='category',
        categoryorder='array',
        categoryarray=pivot.columns.tolist(),
        autorange=True
    )
    fig.update_layout(
        width=900,
        height=max(400, 25 * pivot.shape[0]),
        uirevision=selected_season  # forces full UI reset when season changes
    )
    return fig

cursor.close()
con.close()