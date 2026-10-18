import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.neighbors import NearestNeighbors

from nba_api.stats.static import teams

import plotly.graph_objects as go
import plotly.express as px

import dash # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()


query = "SELECT * FROM player_profiles"
prof_df = pd.read_sql_query(query, con)

teams_nba = pd.DataFrame(teams.get_teams())
seasons = prof_df['season'].unique()

#merging team names to player profiles
prof_df = prof_df.merge(teams_nba[['id','full_name']], left_on='team_id', right_on='id', how='left').drop(columns=['id']).rename(columns={'full_name': 'team_name'})

features = ['positions','pagerank_scaled','def_rating_per_rank','AST_PCT','USG','paint_prop','mid_range_prop','left_corner_prop','right_corner_prop','above_break_prop']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features[1:]),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

X = preprocessor.fit_transform(prof_df[features])
nn = NearestNeighbors(n_neighbors=6, metric='euclidean').fit(X)

def similar(player_id, season, n=5):
    i = prof_df.index[(prof_df.player_id == player_id) & (prof_df.season == season)][0]
    pid = prof_df.at[i, 'player_id']

    # distance from the query row to every row
    dist = np.linalg.norm(X - X[i], axis=1)

    # exclude every row belonging to this player (other seasons and the row itself)
    dist[(prof_df['player_id'] == pid).to_numpy()] = np.inf

    idx = np.argsort(dist)[:n]
    return prof_df.iloc[idx].assign(distance=dist[idx])

def get_player_profile(choice):
    player_name, season = choice.split(' (')
    season = season[:-1]
    player_prof = prof_df[(prof_df['player_name'] == player_name) & (prof_df['season'] == season)]
    if player_prof.empty:
        return player_name, player_prof

    if len(player_prof) > 1:
        # one row: average each feature across the player's rows (e.g. multiple teams)
        row = player_prof.iloc[[0]].copy()
        row[features[1:]] = player_prof[features[1:]].mean(axis=0).values
        player_prof = row
    return player_name, player_prof.copy()

def profile_vector(name, season, team=None):
    """Feature vector for one player-season (averaged if multiple teams)."""
    rows = prof_df[(prof_df['player_name'] == name) & (prof_df['season'] == season)]
    if team is not None:
        rows = rows[rows['team_name'] == team]
    if rows.empty:
        return None
    return rows[features[1:]].mean(axis=0)


def build_radar(traces, title):
    """traces: list of (label, pd.Series of feature values)."""
    theta = features[1:]
    fig = go.Figure()
    for label, s in traces:
        r = s.values.tolist()
        fig.add_trace(go.Scatterpolar(
            r=r + r[:1],                 # repeat first point to close the loop
            theta=theta + theta[:1],
            fill='toself',
            opacity=0.4,
            name=label,
        ))
    fig.update_layout(title=title, 
                      showlegend=True, 
                      polar=dict(radialaxis=dict(range=[0, 1], visible=True)))
    return fig

#making a column that combines player name and season for the dropdown
prof_df['player_name_season'] = prof_df['player_name'] + ' (' + prof_df['season'] + ')' 


dash.register_page(__name__, path='/player_profiles', name='Player Profiles', order = 4)

layout = html.Div([
    html.Label('Choice:',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='player_profile_choice',
                options=prof_df['player_name_season'].unique(),
                value=prof_df['player_name_season'].unique()[0],
                style={"fontFamily": 'sans-serif','width': '10%'}),
    html.Br(),
    html.Div(style={
        'display': 'flex',
        'flexDirection': 'row',
        'gap': '20px',
        'width': '100%'
    },
        children=[
            html.Div(
                dcc.Graph(id='player_profile_graph', style={'height': '600px'}),
            ),
            html.Div(
                dash_table.DataTable(id='player_profile_table',
                    columns=[{"name": i, "id": i} for i in features],
                    style_cell={'textAlign': 'left', "fontFamily": 'sans-serif'},
                    style_header={'fontWeight': 'bold'},
                    data = []),
                style={'width': '40%'}
            )]
    ),
    html.Br(),
    html.Label('Similar Players:',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='num_similar_players',
                options=[5, 10, 15, 20],
                value=5,
                style={"fontFamily": 'sans-serif','width': '10%'}),
    dash_table.DataTable(id='similar_players_table',
        columns=[{"name": i, "id": i} for i in ['player_name','season','team_name','distance']],
        style_cell={'textAlign': 'left', "fontFamily": 'sans-serif'},
        style_header={'fontWeight': 'bold'},
        data = [])
])

#change the player dropdown based on the season selected in the season slider & team dropdown based on the season selected in the season slider
@callback(
    Output("player_profile_choice", "options"),
    Output("player_profile_choice", "value"),
    Input("season-slider", "value"),
    Input("team-dropdown", "value")
)
def update_player_dropdown(season_index, team_value):
    if team_value == 'All':
        if season_index >= len(seasons):  # "All" option selected
            options = prof_df['player_name_season'].unique()
        else:
            selected_season = seasons[season_index]
            options = prof_df[prof_df['season'] == selected_season]['player_name_season'].unique()
    else:
        if season_index >= len(seasons):  # "All" option selected
            options = prof_df[prof_df['team_name'] == team_value]['player_name_season'].unique()
        else:
            selected_season = seasons[season_index]
            options = prof_df[(prof_df['season'] == selected_season) & (prof_df['team_name'] == team_value)]['player_name_season'].unique()
    value = options[0] if len(options) > 0 else None
    return options, value

@callback(
    Output('player_profile_graph', 'figure'),
    Input('player_profile_choice', 'value'),
    Input('similar_players_table', 'active_cell'),
    State('similar_players_table', 'data'),
)
def update_player_profile_graph(choice, active_cell, table_data):
    if not choice:
        return go.Figure()
    player_name, season = choice.split(' (')
    season = season[:-1]

    main = profile_vector(player_name, season)
    if main is None:
        return go.Figure()
    traces = [(f"{player_name} ({season})", main)]

    # only add the comparison if the click came from the table, not a player change
    if active_cell and table_data and ctx.triggered_id == 'similar_players_table':
        row = table_data[active_cell['row']]
        other = profile_vector(row['player_name'], row['season'], row['team_name'])
        if other is not None:
            traces.append((f"{row['player_name']} ({row['season']})", other))

    return build_radar(traces, f"{player_name} Player Profile")

@callback(
    Output('player_profile_table', 'data'),
    Input('player_profile_choice', 'value')
)
def update_player_profile_table(choice):
    _, player_prof = get_player_profile(choice)
    if player_prof.empty:
        return []
    player_prof[features[1:]] = player_prof[features[1:]].round(3)
    return player_prof[features].to_dict('records')

@callback(
    Output('similar_players_table', 'data'),
    Output('similar_players_table', 'active_cell'),
    Input('player_profile_choice', 'value'),
    Input('num_similar_players', 'value'),
)
def update_similar_players_table(choice, num_similar):
    player_name, season = choice.split(' (')  # Extract the player name and season
    season = season[:-1]  # Remove the closing parenthesis
    player_prof = prof_df[(prof_df['player_name'] == player_name)&(prof_df['season'] == season)]
    if player_prof.empty:
        return [], None
    player_id = player_prof.iloc[0]['player_id']
    season = player_prof.iloc[0]['season']
    similar_players = similar(player_id, season, num_similar)
    return similar_players[['player_name','season','team_name','distance']].to_dict('records'), None
