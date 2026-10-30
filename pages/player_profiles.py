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

#merging team names & abbreviation to player profiles
prof_df = (
    prof_df.merge(teams_nba[['id', 'full_name', 'abbreviation']],
                  left_on='team_id', right_on='id', how='left')
           .drop(columns=['id'])
           .rename(columns={'full_name': 'team_name', 'abbreviation': 'team_abbr'})
)
features = ['positions','pagerank_scaled','def_rating_per_rank','AST_PCT','USG','paint_prop','mid_range_prop','left_corner_prop','right_corner_prop','above_break_prop']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features[1:]),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

prof_df = prof_df.dropna(subset=features).reset_index(drop=True)

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

def get_player_profile(choice, team=None):
    player_name, season = choice.split(' (')
    season = season[:-1]
    player_prof = prof_df[(prof_df['player_name'] == player_name) & (prof_df['season'] == season)]
    if player_prof.empty:
        return player_name, player_prof

    if team is not None:
        player_prof = player_prof.loc[player_prof['team_name']==team].copy()
    else:
        # one row: average each feature across the player's rows (e.g. multiple teams)
        row = player_prof.iloc[[0]].copy()
        row[features[1:]] = player_prof[features[1:]].mean(axis=0).values
        player_prof = row
    return player_name, player_prof.copy()

#function to show correct team label for player and season
def team_label(choice, team=None):
    """'ORL' for one team, 'ORL/DEN' if traded (when no team is selected)."""
    player_name, season = choice.split(' (')
    season = season[:-1]
    rows = prof_df[(prof_df['player_name'] == player_name) & (prof_df['season'] == season)]
    if team is not None and team != 'All':
        rows = rows[rows['team_name'] == team]
    return '/'.join(rows['team_abbr'].dropna().unique())

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
                style={"fontFamily": 'sans-serif','width': '20%'}),
    html.Br(),
    html.Div(style={
        'display': 'flex',
        'flexDirection': 'row',
        'gap': '20px',
        'width': '100%'
    },
        children=[
            html.Div(
                children = [dcc.Graph(id='player_profile_graph', style={'height': '600px','width': '900px'}),

                html.Div(
                id='traded_diff_container',
                style={'display': 'none'},
                children=[
                    html.H5("Change after trade", style={'fontFamily': 'sans-serif'}),
                    dash_table.DataTable(
                        id='traded_diff_table',
                        columns=[],
                        data=[],
                        style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif', 'padding': '4px 8px'},
                        style_header={'fontWeight': 'bold'},
                    ),
                ],
                )]
            ),
            html.Div(
                children=[
                    html.Img(
                        id='player-profile-image',
                        src='',
                        style={
                            'width': '100%',
                            'height': 'auto',
                            'objectFit': 'contain'
                        }
                    ),
                    dash_table.DataTable(
                        id='player_profile_table',
                        columns=[
                            {"name": "Feature", "id": "feature"},
                            {"name": "Value", "id": "value"}
                        ],
                        style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif', 'padding': '4px 8px'},
                        style_header={'fontWeight': 'bold'},
                        data=[],
                    )],
            style={'flex': '1 1 25%', 'minWidth': 0},
        )]
    ),
    html.Br(),
    html.Label('Similar Players:',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='num_similar_players',
                options=[5, 10, 15, 20],
                value=5,
                style={"fontFamily": 'sans-serif','width': '10%'}),
    html.Br(),
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
            options = prof_df['player_name_season'].sort_values(ascending=True).unique()
        else:
            selected_season = seasons[season_index]
            options = prof_df[prof_df['season'] == selected_season]['player_name_season'].sort_values(ascending=True).unique()
    else:
        if season_index >= len(seasons):  # "All" option selected
            options = prof_df[prof_df['team_name'] == team_value]['player_name_season'].sort_values(ascending=True).unique()
        else:
            selected_season = seasons[season_index]
            options = prof_df[(prof_df['season'] == selected_season) & (prof_df['team_name'] == team_value)]['player_name_season'].sort_values(ascending=True).unique()
    value = options[0] if len(options) > 0 else None
    return options, value

#building the player profile graph based on the player selected in the dropdown and the similar players selected in the table
@callback(
    Output('player_profile_graph', 'figure'),
    Input('player_profile_choice', 'value'),
    Input('similar_players_table', 'active_cell'),
    Input('team-dropdown', 'value'),
    State('similar_players_table', 'data'),
)
def update_player_profile_graph(choice, active_cell, team_value, table_data):
    if not choice:
        return go.Figure()
    player_name, season = choice.split(' (')
    season = season[:-1]

    #if team is All and player traded us the mean otherwise use team specific
    if team_value == 'All':
        main = profile_vector(player_name, season)
    else:
        main = profile_vector(player_name, season, team_value)
    
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

#callback to show correct table used to build radar graph
#if traded show mean between two when team is selected as All
#otherwise split into seperate teams 

@callback(
    Output('player_profile_table', 'data'),
    Input('player_profile_choice', 'value'),
    Input('team-dropdown', 'value')
)
def update_player_profile_table(choice, team_value):
    team = None if team_value == 'All' else team_value
    _, player_prof = get_player_profile(choice, team)
    if player_prof.empty:
        return []
    row = player_prof.iloc[0]
    data = [{"feature": "team", "value": team_label(choice, team)}]
    data += [
        {"feature": f, "value": row[f] if f == 'positions' else round(float(row[f]), 3)}
        for f in features
    ]
    return data

#creating table with differences for traded players
diff_features = features[1:]

@callback(
    Output('traded_diff_table', 'data'),
    Output('traded_diff_table', 'columns'),
    Output('traded_diff_table', 'style_data_conditional'),
    Output('traded_diff_container', 'style'),
    Input('player_profile_choice', 'value'),
)
def update_traded_diff(choice):
    hidden = {'display': 'none'}
    if not choice:
        return [], [], [], hidden

    name, season = choice.split(' (')
    season = season[:-1]
    
    player_df = prof_df[prof_df['player_name'] == name].reset_index()
    
    rows = player_df[player_df['season'] == season]
    
    if len(rows) < 2:
        return [], [], [], hidden

    columns = [{'name': 'Feature', 'id': 'feature'}]
    data = [{'feature': f} for f in diff_features]
    styles = []
    
    start, _ = rows.index
    
    old = player_df.iloc[start-1,:]
    
    traded_team = rows['team_id'] != old['team_id']
    
    new_index = traded_team[traded_team].index[0]
    
    new = rows.loc[new_index,:] 

    for k in range(1, len(rows)):
        
        cid = f'd{k}'
        columns.append({'name': f'{old["team_abbr"]} → {new["team_abbr"]}', 'id': cid})
        for rec, f in zip(data, diff_features):
            rec[cid] = round(float(new[f] - old[f]), 3)
        styles += [
            {'if': {'filter_query': f'{{{cid}}} < 0', 'column_id': cid},
             'backgroundColor': '#f8b4b4', 'color': '#7a1212'},
            {'if': {'filter_query': f'{{{cid}}} > 0', 'column_id': cid},
             'backgroundColor': '#b4cdf8', 'color': '#12307a'},
        ]

    return data, columns, styles, {'display': 'block'}
 
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

#showing correct player image based on the player selected in the dropdown
@callback(
    Output('player-profile-image', 'src'),
    Input('player_profile_choice', 'value')
)
def update_player_image(choice):    
    player_name, _ = choice.split(' (')
    
    player_prof = prof_df[prof_df['player_name'] == player_name]
    if player_prof.empty:
        return ''
    player_id = player_prof.iloc[0]['player_id']
    image_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    return image_url