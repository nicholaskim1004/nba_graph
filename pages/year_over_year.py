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

pageranks['season_idx'] = pageranks['season'].map(season_to_idx)

#to make it numerical for plot
pageranks['season_start'] = pageranks['season'].str.split('-').str[0].astype(int)
shotnode_to_id = {s: i for i, s in enumerate(diff_shots)}

shot_mask = pageranks['node_name'].isin(diff_shots)
pageranks.loc[shot_mask, 'player_id'] = (
    pageranks.loc[shot_mask, 'team_id'] * 10 +
    pageranks.loc[shot_mask, 'node_name'].map(shotnode_to_id)
)

# now player_id is globally unique for both real players and shot nodes,
# so a plain groupby works for everyone
pageranks = pageranks.sort_values(by=['player_id', 'season_idx']).reset_index(drop=True)
pageranks['pagerank_yoy_diff'] = pageranks.groupby('player_id')['pagerank'].diff()

# keep the season-gap guard so skipped seasons don't get treated as a 1-year diff
season_gap = pageranks.groupby('player_id')['season_idx'].diff()
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
    html.Div("The graph below displays the pagerank over time, regardless of team, for the selected node. "
             "Instances of a double stacking shows that the player was traded/moved in between the season.",
             style={
                    "fontFamily": 'sans-serif',
                    "fontSize": "20px",
                    "marginTop": "0px"
                }
             ),
    html.Div(
        style={
        'display': 'flex',
        'flexDirection': 'row',
        'gap': '20px',
        'width': '100%'
    },
    children=[
        dcc.Graph(
                id = 'yoy_change',
                figure = {},
                style={'flex': '1 1 0', 'minWidth': '300px'},
                config={'responsive': True}
            ),
        dcc.Graph(id='yoy_heatmap', 
                  figure={},
                  style={'flex': '1 1 0', 'minWidth': '400px'},
                  config={'responsive': True}
                  )
    ]
    )
    
])

#update the options to the node list based on the team and season
@callback(
    Output('node_options', 'options'),
    Output('node_options', 'value'),
    Input('team-dropdown', 'value'),
    Input('season-slider', 'value')
)
def update_node_list_options(selected_team, selected_season):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()
    pageranks_yr = pageranks[
        (pageranks['season_idx'] <= selected_season) &
        (pageranks['team_id'] == teamid[0])
    ]

    # one row per player on this team/season window, label = name, value = player_id
    lookup = (
        pageranks_yr[['node_name', 'player_id']]
        .drop_duplicates()
        .sort_values('node_name')
    )

    options = [
        {'label': row.node_name, 'value': row.player_id}
        for row in lookup.itertuples()
    ]
    value = options[0]['value'] if options else None

    return options, value

#now to create figure
@callback(
    Output('yoy_change', 'figure'),
    Input('season-slider', 'value'),
    Input('node_options', 'value')
)
def update_yoy_fig(selected_season, selected_player_id):
    # no team filter at all now — full career history for that player_id
    node_yoy = pageranks[
        (pageranks['season_idx'] <= selected_season) &
        (pageranks['player_id'] == selected_player_id)
    ]

    fig = px.line(
        node_yoy.loc[:, ['season_start', 'pagerank']],
        x='season_start', y='pagerank',
        title='Pagerank over Time', markers=True
    )
    fig.update_layout(width=800, height=600)
    fig.update_xaxes(dtick=1)
    return fig

@callback(
    Output('yoy_heatmap', 'figure'),
    Input('team-dropdown', 'value'),
    Input('season-slider', 'value'),
    Input('node_options', 'value')
)
def update_yoy_heatmap(selected_team, selected_season, selected_player_id):
    teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()

    # Step 1: who is/was on this team's roster (within the season window)?
    roster_ids = pageranks.loc[
        (pageranks['season_idx'] == selected_season) &
        (pageranks['team_id'] == teamid[0]),
        'player_id'
    ].unique()

    # Step 2: pull each of those players' FULL season history, regardless of team
    team_yoy = pageranks[
        (pageranks['season_idx'] <= selected_season) &
        (pageranks['player_id'].isin(roster_ids))
    ]

    valid_seasons = sorted(team_yoy['season_start'].unique())
    valid_seasons = [s for s in valid_seasons if s != 2020] 

    pivot = team_yoy.pivot_table(
        index='node_name',
        columns='season_start',
        values='pagerank_yoy_diff',
        aggfunc='mean',
        observed=True
    ).reindex(columns=valid_seasons)

    pivot.columns = pivot.columns.astype(str)
    
    row_mean = pivot.mean(axis=1)
    row_std = pivot.std(axis=1)

    # Need at least 2 valid seasons to compute a meaningful per-player std;
    # otherwise just show the raw diff so the heatmap isn't blank
    enough_history = pivot.notna().sum(axis=1) >= 2
    row_std_safe = row_std.where(enough_history & (row_std != 0))

    pivot_z = pivot.sub(row_mean, axis=0).div(row_std_safe, axis=0)

    # For rows that couldn't be z-scored, fall back to the raw diff value itself
    pivot_display = pivot_z.where(enough_history, pivot)

    fig = px.imshow(
        pivot_display,
        color_continuous_scale='RdBu_r',
        color_continuous_midpoint=0,
        aspect='auto',
        labels=dict(x='Season', y='Player', color='YoY Δ'),
        title='Year-over-Year Pagerank Change by Player (Relative to Own History)'
    )

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
        width=750,
        height=max(400, 25 * pivot.shape[0]),
        uirevision=selected_season
    )

    # Outline the selected player: selected_player_id -> node_name -> row position
    node_lookup = pageranks.loc[
        pageranks['player_id'] == selected_player_id, 'node_name'
    ]
    if not node_lookup.empty:
        selected_node = node_lookup.iloc[0]
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