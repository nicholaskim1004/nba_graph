import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

from nba_api.stats.static import teams
from nba_api.stats.endpoints import playergamelog

import plotly.graph_objects as go

import dash  # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx  # type: ignore[import-not-found]


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

prof_df = pd.read_sql_query("SELECT * FROM player_profiles", con)

teams_nba = pd.DataFrame(teams.get_teams())
seasons = prof_df['season'].unique()

# merging team names & abbreviation to player profiles
prof_df = (
    prof_df.merge(teams_nba[['id', 'full_name', 'abbreviation']],
                  left_on='team_id', right_on='id', how='left')
           .drop(columns=['id'])
           .rename(columns={'full_name': 'team_name', 'abbreviation': 'team_abbr'})
)

features = ['positions', 'pagerank_scaled', 'def_rating_per_rank', 'AST_PCT', 'USG',
            'paint_prop', 'mid_range_prop', 'left_corner_prop', 'right_corner_prop', 'above_break_prop']
num_features = features[1:]

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), num_features),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

prof_df = prof_df.dropna(subset=features).reset_index(drop=True)
X = preprocessor.fit_transform(prof_df[features])

# column used in the dropdowns, e.g. "Nikola Jokic (2023-24)"
prof_df['player_name_season'] = prof_df['player_name'] + ' (' + prof_df['season'] + ')'


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def parse_choice(choice):
    """'Name (2023-24)' -> ('Name', '2023-24')"""
    name, season = choice.rsplit(' (', 1)
    return name, season.rstrip(')')


def get_rows(name, season, team=None):
    """Rows for one player-season. If a team is given and the player has rows
    on that team, only those rows are used; otherwise all rows are returned
    (e.g. a traded player, or a compare player who is on a different team)."""
    rows = prof_df[(prof_df['player_name'] == name) & (prof_df['season'] == season)]
    if team and team != 'All':
        on_team = rows[rows['team_name'] == team]
        if not on_team.empty:
            return on_team
    return rows


def profile_vector(choice, team=None):
    """Feature vector for one player-season (averaged if multiple rows)."""
    name, season = parse_choice(choice)
    rows = get_rows(name, season, team)
    if rows.empty:
        return None
    return rows[num_features].mean(axis=0)


def profile_table_data(choice, team=None):
    """Rows for the Feature/Value DataTable of one player-season."""
    name, season = parse_choice(choice)
    rows = get_rows(name, season, team)
    if rows.empty:
        return []
    vec = rows[num_features].mean(axis=0)
    # 'ORL' for one team, 'ORL/DEN' if traded and no team filter applies
    team_abbrs = '/'.join(rows['team_abbr'].dropna().unique())
    data = [
        {'feature': 'team', 'value': team_abbrs},
        {'feature': 'positions', 'value': rows.iloc[0]['positions']},
    ]
    data += [{'feature': f, 'value': round(float(vec[f]), 3)} for f in num_features]
    return data


def headshot_url(choice):
    name, season = parse_choice(choice)
    rows = prof_df[(prof_df['player_name'] == name) & (prof_df['season'] == season)]
    if rows.empty:
        return ''
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{rows.iloc[0]['player_id']}.png"


def similar(player_id, season, n=5):
    i = prof_df.index[(prof_df.player_id == player_id) & (prof_df.season == season)][0]

    # distance from the query row to every row
    dist = np.linalg.norm(X - X[i], axis=1)

    # exclude every row belonging to this player (other seasons and the row itself)
    dist[(prof_df['player_id'] == player_id).to_numpy()] = np.inf

    idx = np.argsort(dist)[:n]
    return prof_df.iloc[idx].assign(distance=dist[idx])


def build_radar(traces, title):
    """traces: list of (label, pd.Series of feature values)."""
    theta = num_features
    fig = go.Figure()
    for label, s in traces:
        r = s.values.tolist()
        fig.add_trace(go.Scatterpolar(
            r=r + r[:1],  # repeat first point to close the loop
            theta=theta + theta[:1],
            fill='toself',
            opacity=0.4,
            name=label,
        ))
    fig.update_layout(title=title,
                      showlegend=True,
                      polar=dict(radialaxis=dict(range=[0, 1], visible=True)))
    return fig


# ----------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------
LABEL_STYLE = {'fontFamily': 'sans-serif', 'fontWeight': 'bold'}

# Side panels (main player / compare player) share the same sizing so the
# two headshots and tables always line up. Hiding only flips 'display' and
# keeps the rest of the style, so the flex sizing is never lost.
SIDE_STYLE = {'flex': '1 1 0', 'minWidth': 0, 'maxWidth': '300px'}
SIDE_HIDDEN_STYLE = {**SIDE_STYLE, 'display': 'none'}
CENTER_STYLE = {'flex': '3 1 0', 'minWidth': 0}

IMG_STYLE = {
    'width': '100%',
    'height': 'auto',
    'aspectRatio': '1040 / 760',  # reserves space so the layout doesn't jump while loading
    'objectFit': 'contain',
}

# one style pair for the similar-player tables
SIM_STYLE = {'flex': '1 1 0', 'minWidth': 0}
SIM_HIDDEN_STYLE = {**SIM_STYLE, 'display': 'none'}


def profile_panel(img_id, table_id):
    """Headshot + feature table. Used for both the main and the compare player."""
    return [
        html.Img(id=img_id, src='', style=IMG_STYLE),
        dash_table.DataTable(
            id=table_id,
            columns=[{'name': 'Feature', 'id': 'feature'},
                     {'name': 'Value', 'id': 'value'}],
            style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif', 'padding': '4px 8px'},
            style_header={'fontWeight': 'bold'},
            data=[],
        ),
    ]


dash.register_page(__name__, path='/player_profiles', name='Player Profiles', order=4)

layout = html.Div([
    html.Div(
        style={'display': 'flex', 'justifyContent': 'space-between', 'width': '100%'},
        children=[
            html.Div(
                style={'width': '20%'},
                children=[
                    html.Label('Choice:', style=LABEL_STYLE),
                    dcc.Dropdown(id='player_profile_choice',
                                 options=prof_df['player_name_season'].unique(),
                                 value=prof_df['player_name_season'].unique()[0],
                                 style={'fontFamily': 'sans-serif'}),
                ]
            ),
            html.Div(
                style={'width': '20%'},
                children=[
                    html.Label('+ Compare with:', style=LABEL_STYLE),
                    dcc.Dropdown(id='compare-choice',
                                 options=[],
                                 value=None,
                                 clearable=True,
                                 placeholder='None',
                                 style={'fontFamily': 'sans-serif'}),
                ]
            ),
        ]
    ),
    html.Br(),
    html.Div(
        style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-start',
               'gap': '20px', 'width': '100%'},
        children=[
            # LEFT: main player
            html.Div(children=profile_panel('player-profile-image', 'player_profile_table'),
                     style=SIDE_STYLE),

            # CENTER: radar + trade diff
            html.Div(
                style=CENTER_STYLE,
                children=[
                    dcc.Graph(id='player_profile_graph',
                              style={'height': '600px', 'width': '100%'},
                              config={'responsive': True}),
                    html.Div(
                        id='traded_diff_container',
                        style={'display': 'none'},
                        children=[
                            html.H5('Change after trade', style={'fontFamily': 'sans-serif'}),
                            dash_table.DataTable(
                                id='traded_diff_table',
                                columns=[],
                                data=[],
                                style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif', 'padding': '4px 8px'},
                                style_header={'fontWeight': 'bold'},
                            ),
                        ],
                    ),
                ]
            ),

            # RIGHT: compare player (hidden until one is chosen)
            html.Div(id='compare-container',
                     children=profile_panel('compare-player-image', 'compare-player-table'),
                     style=SIDE_HIDDEN_STYLE),
        ]
    ),
    html.Br(),
    html.Label('Similar Players:', style=LABEL_STYLE),
    dcc.Dropdown(id='num_similar_players',
                 options=[5, 10, 15, 20],
                 value=5,
                 style={'fontFamily': 'sans-serif', 'width': '10%'}),
    html.Br(),
    html.Div(
    children=[
        html.Div(
            style = SIM_STYLE,
            children = [
                html.Label(id='sim_label_main',children=[],style=LABEL_STYLE),
                dash_table.DataTable(
                    id='similar_players_table',
                    columns=[{'name': i, 'id': i} for i in ['player_name', 'season', 'team_name', 'distance']],
                    style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif'},
                    style_header={'fontWeight': 'bold'},
                    data=[])
                ]
            ),
        
        #RIGHT table for compare player if chosen
        html.Div(
            id = 'sim_table_comparison',
            children = [
                html.Label(id='sim_label_comp',children=[],style=LABEL_STYLE),
                dash_table.DataTable(
                    id='similar_players_table_comparison',
                    columns=[{'name': i, 'id': i} for i in ['player_name', 'season', 'team_name', 'distance']],
                    style_cell={'textAlign': 'left', 'fontFamily': 'sans-serif'},
                    style_header={'fontWeight': 'bold'},
                    data=[])
                ],
            style = SIM_HIDDEN_STYLE
            )
        ],
    style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-start','gap': '20px', 'width': '100%'},    )
])


# ----------------------------------------------------------------------------
# callbacks
# ----------------------------------------------------------------------------
# main player dropdown follows the season slider & team dropdown
@callback(
    Output('player_profile_choice', 'options'),
    Output('player_profile_choice', 'value'),
    Input('season-slider', 'value'),
    Input('team-dropdown', 'value'),
)
def update_player_dropdown(season_index, team_value):
    df = prof_df
    if team_value != 'All':
        df = df[df['team_name'] == team_value]
    if season_index < len(seasons):  # otherwise the "All" option is selected
        df = df[df['season'] == seasons[season_index]]

    options = sorted(df['player_name_season'].unique())
    return options, (options[0] if options else None)


# compare dropdown: same season filter, but NOT limited to the selected team
# (so you can compare against players on other teams), excluding the main player
@callback(
    Output('compare-choice', 'options'),
    Output('compare-choice', 'value'),
    Input('player_profile_choice', 'value'),
    Input('season-slider', 'value'),
    State('compare-choice', 'value'),
)
def update_compare_dropdown(choice, season_index, current_compare):
    df = prof_df
    if season_index < len(seasons):
        df = df[df['season'] == seasons[season_index]]

    options = sorted(o for o in df['player_name_season'].unique() if o != choice)
    value = current_compare if current_compare in options else None
    return options, value


# radar graph for the main player, plus the clicked similar player and/or the compare player
@callback(
    Output('player_profile_graph', 'figure'),
    Input('player_profile_choice', 'value'),
    Input('compare-choice', 'value'),
    Input('similar_players_table', 'active_cell'),
    Input('similar_players_table_comparison', 'active_cell'),
    Input('team-dropdown', 'value'),
    State('similar_players_table', 'data'),
    State('similar_players_table_comparison', 'data')
)
def update_player_profile_graph(choice, compare_choice, active_cell, comp_active, team_value, table_data, comp_table):
    if not choice:
        return go.Figure()

    main = profile_vector(choice, team_value)
    if main is None:
        return go.Figure()

    traces = [(choice, main)]

    # only add the similar-player trace if the click came from the table
    if active_cell and table_data and ctx.triggered_id == 'similar_players_table':
        row = table_data[active_cell['row']]
        label = f"{row['player_name']} ({row['season']})"
        other = profile_vector(label, row['team_name'])
        if other is not None:
            traces.append((label, other))
    
    #same for the comparison player similar table    
    if comp_active and comp_table and ctx.triggered_id == 'similar_players_table_comparison':
        row = comp_table[comp_active['row']]
        label = f"{row['player_name']} ({row['season']})"
        other = profile_vector(label, row['team_name'])
        if other is not None:
            traces.append((label, other))

    if compare_choice:
        other = profile_vector(compare_choice, team_value)
        if other is not None:
            traces.append((compare_choice, other))

    name, _ = parse_choice(choice)
    return build_radar(traces, f'{name} Player Profile')


# feature tables for the main and compare players; show/hide the compare panel
@callback(
    Output('player_profile_table', 'data'),
    Output('compare-player-table', 'data'),
    Output('compare-container', 'style'),
    Input('player_profile_choice', 'value'),
    Input('compare-choice', 'value'),
    Input('team-dropdown', 'value'),
)
def update_player_profile_tables(choice, compare_choice, team_value):
    main_data = profile_table_data(choice, team_value) if choice else []
    compare_data = profile_table_data(compare_choice, team_value) if compare_choice else []

    style = SIDE_STYLE if compare_data else SIDE_HIDDEN_STYLE
    return main_data, compare_data, style


# headshots for the main and compare players
@callback(
    Output('player-profile-image', 'src'),
    Output('compare-player-image', 'src'),
    Input('player_profile_choice', 'value'),
    Input('compare-choice', 'value'),
)
def update_player_images(choice, compare_choice):
    main_url = headshot_url(choice) if choice else ''
    compare_url = headshot_url(compare_choice) if compare_choice else ''
    return main_url, compare_url


# table with differences for traded players
diff_features = num_features


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

    name, season = parse_choice(choice)

    player_df = prof_df[prof_df['player_name'] == name].reset_index()
    rows = player_df[player_df['season'] == season]

    if len(rows) < 2:
        return [], [], [], hidden

    columns = [{'name': 'Feature', 'id': 'feature'}]
    data = [{'feature': f} for f in diff_features]
    styles = []

    start = rows.index[0]

    # if there's no earlier season row, find the team they started with from the first games of the year
    if start == 0:
        playid = player_df.loc[0, 'player_id']
        season_gamelog = playergamelog.PlayerGameLog(player_id=playid, season=season).get_data_frames()[0]
        # gamelog is newest-first, so tail() is the earliest games.
        # MATCHUP looks like "LAL vs. BOS" / "LAL @ BOS": the first token is the player's own team
        first_games = season_gamelog.tail()
        old_team_abbr = first_games['MATCHUP'].str.split(' ').str[0].mode().iloc[0]

        old = player_df[player_df['team_abbr'] == old_team_abbr].iloc[0, :]
    else:
        old = player_df.iloc[start - 1, :]

    traded_team = rows['team_id'] != old['team_id']
    new_index = traded_team[traded_team].index[0]
    new = rows.loc[new_index, :]

    for k in range(1, len(rows)):
        cid = f'd{k}'
        columns.append({'name': f'{old["team_abbr"]} → {new["team_abbr"]}', 'id': cid})
        for rec, f in zip(data, diff_features):
            rec[cid] = round(float(new[f] - old[f]), 3)
        styles += [
            {'if': {'filter_query': f'{{{cid}}} > 0', 'column_id': cid},
             'backgroundColor': '#f8b4b4', 'color': '#7a1212'},
            {'if': {'filter_query': f'{{{cid}}} < 0', 'column_id': cid},
             'backgroundColor': '#b4cdf8', 'color': '#12307a'},
        ]

    return data, columns, styles, {'display': 'block'}


@callback(
    Output('similar_players_table', 'data'),
    Output('similar_players_table', 'active_cell'),
    Output('sim_label_main','children'),
    Output('similar_players_table_comparison', 'data'),
    Output('similar_players_table_comparison', 'active_cell'),
    Output('sim_label_comp','children'),
    Output('sim_table_comparison', 'style'),
    Input('player_profile_choice', 'value'),
    Input('compare-choice', 'value'),
    Input('num_similar_players', 'value'),
)
def update_similar_players_table(choice, compare_choice, num_similar):
    if not choice and not compare_choice:
        return [], None, None, [], None, None, SIDE_HIDDEN_STYLE

    name, season = parse_choice(choice)
    player_prof = prof_df[(prof_df['player_name'] == name) & (prof_df['season'] == season)]
    
    if compare_choice == None:
        if player_prof.empty:
            return [], None, None, [], None, None, SIDE_HIDDEN_STYLE

        player_id = player_prof.iloc[0]['player_id']
        similar_players = similar(player_id, season, num_similar)
        
        compare_id = compare_prof.iloc[0]['player_id']
        similar_players_comp = similar(compare_id, season_compare, num_similar)
        return similar_players[['player_name', 'season', 'team_name', 'distance']].to_dict('records'), None, f'{name}', [], None, None, SIDE_HIDDEN_STYLE
    else:
        compare_name, season_compare = parse_choice(compare_choice)
        compare_prof = prof_df[(prof_df['player_name'] == compare_name) & (prof_df['season'] == season_compare)]
        
    similar_players['distance'] = similar_players['distance'].round(2)
    similar_players_comp['distance'] = similar_players_comp['distance'].round(2)
    
    return similar_players[['player_name', 'season', 'team_name', 'distance']].to_dict('records'), None, f'{name}', similar_players_comp[['player_name', 'season', 'team_name', 'distance']].to_dict('records'), None, f'{compare_name}', SIM_STYLE