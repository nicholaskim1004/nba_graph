import sqlite3
import pandas as pd
import numpy as np
import dash
import plotly.express as px

from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

query = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query, con)

team_df = pd.DataFrame(teams.get_teams())
seasons = pageranks['season'].unique()

#creating a number for seasons
sorted_seasons = np.sort(seasons)  # e.g. ['2018-19', '2019-20', '2020-21', ...]
season_to_idx = {s: i for i, s in enumerate(sorted_seasons)}

#changing the player_id for diff shots to be numberic 0-7
shotnode_to_id = {s: i for i, s in enumerate(diff_shots)}
pageranks.loc[pageranks['node_name'].isin(diff_shots),'player_id'] = pageranks.loc[pageranks['node_name'].isin(diff_shots),'node_name'].map(shotnode_to_id)

pageranks['season_idx'] = pageranks['season'].map(season_to_idx)

#to make it numerical for plot
pageranks['season_start'] = pageranks['season'].str.split('-').str[0].astype(int)
#creating yoy change
# Build a group key: real players use player_id alone (ignore team changes),
# shot nodes use team_id + player_id (since 0-7 ids collide across teams)
is_shot_node = pageranks['node_name'].isin(diff_shots)

pageranks['group_key'] = np.where(
    is_shot_node,
    pageranks['team_id'].astype(str) + '_' + pageranks['player_id'].astype(str),
    pageranks['player_id'].astype(str)
)

pageranks = pageranks.sort_values(by=['group_key', 'season_idx']).reset_index(drop=True)

# Diff across whatever seasons the player has data for, regardless of team
pageranks['pagerank_yoy_diff'] = pageranks.groupby('group_key')['pagerank'].diff()

# But only keep it as a true "YoY" value if the seasons are actually consecutive
season_gap = pageranks.groupby('group_key')['season_idx'].diff()
pageranks.loc[season_gap != 1, 'pagerank_yoy_diff'] = np.nan

assert not pageranks[pageranks['player_id'].between(0,7)]['node_name'].isin(diff_shots).eq(False).any()

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
    Input('season-slider', 'value'),
    Input('node_options', 'value')
)
def update_yoy_heatmap(selected_team, selected_season, selected_node):
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

    #making the heat colors relative to each player
    row_mean = pivot.mean(axis=1)
    row_std = pivot.std(axis=1).replace(0, np.nan)  # avoid divide-by-zero for flat rows
    pivot_z = pivot.sub(row_mean, axis=0).div(row_std, axis=0)

    fig = px.imshow(
        pivot_z,
        color_continuous_scale='RdBu_r',
        color_continuous_midpoint=0,
        aspect='auto',
        labels=dict(x='Season', y='Player', color='YoY Δ (z-score, per player)'),
        title='Year-over-Year Pagerank Change by Player (Relative to Own History)'
    )

    # Show the RAW diff value on hover, not the z-score
    fig.update_traces(
        customdata=pivot.values,
        hovertemplate='Player: %{y}<br>Season: %{x}<br>YoY Δ: %{customdata:.4f}<extra></extra>'
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
        uirevision=selected_season
    )
    
    #outline of selected player
    if selected_node in pivot.index:
        row_pos = pivot.index.get_loc(selected_node)
        fig.add_shape(
            type='rect',
            x0=-0.5, x1=len(valid_seasons) - 0.5,
            y0=row_pos - 0.5, y1=row_pos + 0.5,
            line=dict(color='black', width=3),
            fillcolor='rgba(0,0,0,0)',
            layer='above'
        )
        
    return fig

cursor.close()
con.close()