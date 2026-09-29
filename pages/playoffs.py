import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]
import numpy as np # type: ignore[import-not-found]
import plotly.graph_objects as go
import plotly.express as px

import dash # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_playoffs_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_edge = "SELECT * FROM network_edges_playoffs"
edges_yr = pd.read_sql_query(query_edge, con)

#importing regular season data to build heatmap
query_page_reg = "SELECT * FROM pageranks_yr"
pageranks_yr_reg = pd.read_sql_query(query_page_reg, con)

query_player = "SELECT * FROM player_usage_yr"
player_usage = pd.read_sql_query(query_player, con)

query_player_play = "SELECT * FROM player_usage_yr_playoff"
player_usage_play = pd.read_sql_query(query_player_play, con)

query_playoff_res = "SELECT * FROM playoff_records_yr"
playoff_res = pd.read_sql_query(query_playoff_res, con)

playoff_res['win_team_short'] = playoff_res['winning_team'].str.split(" ")

query_team_records = "SELECT * FROM records_yr"
team_records = pd.read_sql_query(query_team_records, con)

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

dash.register_page(__name__, path='/playoffs', name='Playoffs', order = 1)

layout = html.Div([
    html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'row',
        'gap': '20px',
        'width': '100%'
    },
    children=[
        # LEFT: Cytoscape
        html.Div(
            cyto.Cytoscape(
                id='graph_networks_playoffs',
                elements=[],
                layout={'name': 'preset'},
                stylesheet=[
                    {
                        'selector': 'node',
                        'style': {
                            'label': 'data(label)',
                            'width': 'data(pagerank)',
                            'height': 'data(pagerank)'
                        }
                    },
                    {
                        'selector': '.shot',
                        'style': {
                            'background-color': '#FF2C2C',
                            'opacity': 0.95
                        }
                    },
                    {
                        'selector': '.player',
                        'style': {
                            'background-color': '#B6E3FF',
                            'opacity': 0.95
                        }
                    },
                    {
                        'selector': 'edge',
                        'style': {
                            'source-arrow-shape': 'triangle'
                        }
                    }
                ],
                style={
                    'width': '100%',
                    'height': '700px'
                }
            ),
            style={
                'width': '70%'
            }
        ),

        # RIGHT: PageRank table
        html.Div(
            dash_table.DataTable(
                id='pagerank_table_playoffs',
                data=[],
                columns=[
                    {'name': i, 'id': i}
                    for i in pageranks_yr.loc[:, ['season','node_name','pagerank']].columns
                ],
                style_data_conditional = [
                    {
                    'if': {'state': 'active'},
                    'backgroundColor': '#FF0000',
                    'color': 'white'
                    }
                ]
            ),
            style={
                'width': '30%'
            }
        )
    ]
    ),
    html.Div(
    id='passes_weight_container_play',
    children=[
        html.H2('Edge Weights',style={"fontFamily": 'sans-serif',"fontWeight": 'bold'}),
        dash_table.DataTable(
            id='passes_weight_table_play',
            data=[],
            columns=[{'name': i, 'id': i}
                    for i in ['season','node_name','edge_to','weight']]
        )
    ],
    style={'display': 'none'}  # hidden until something is selected
    ),

    html.Div(
        id='player_usage_container_play',
        children=[
            html.H2('Player Usage',style={"fontFamily": 'sans-serif',"fontWeight": 'bold'}),
            html.Div(
                "A single metric to measure how centeralized the offense is to a select few players. "
                "Will hopefully highlight teams that are star focused over team first basketball. "
                "Gini coeffiencent is a measure of inequality. Smaller means more EQUAL. "
                "Entropy is a measure of how unpredictable a teams offensive involement is. Higher means MORE unpredictable or in this case more DIVERSE. "
                "Effective number of players is determing how many players have a meaningul pagerank or involement. Here the higher means more DIVERSE.",
                style={
                    "fontFamily": 'sans-serif',
                    "fontSize": "20px",
                    "marginTop": "0px"
                }
            ),
            html.Br(),
            dash_table.DataTable(
                id='player_usage_table_play',
                data=[],
                columns=[{'name': i, 'id': i}
                        for i in ['season','gini','entropy','eff_num_players']]
            )
        ]
    ),
    
    html.Div(
        id='reg_v_play',
        children=[
            html.H2('Regular Season vs Playoffs',
                    style={"fontFamily": 'sans-serif',"fontWeight": 'bold'}
                    ),
            html.Div(
                "Heatmap to highlight the difference in playstyle from the regular season to Playoffs. "
                "The differences were then normalized within each column to highlight which ones took a step forward or back in respect to their own scale.",
                style={
                    "fontFamily": 'sans-serif',
                    "fontSize": "20px",
                    "marginTop": "0px"
                }
            ),
            dcc.Graph(id='reg_v_play_heatmap',
                      figure={})
        ]
    ),
    html.Div(
        children=[
            html.H2('Playoff Bracket',style={"fontFamily": 'sans-serif',"fontWeight": 'bold'}),
            dcc.Graph(id='playoff-bracket',
                      figure={})
        ]
    )
])


@callback(
    Output("graph_networks_playoffs", "elements"),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_network(selected_teams, selected_season):
    sel_teams_ids = team_df[team_df['full_name']==selected_teams]['id'].to_numpy()
    season = seasons[selected_season]
    
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==season)
    ]

    # Create nodes
    nodes = [
        {
            "data": {
                "id": str(row["node_name"]),
                "label": row["node_name"],
                "pagerank": float(row["pagerank"]) * 1000,
                "selected": False
            },
            "classes": "shot" if row["node_name"] in diff_shots else "player",
            "position": {
                "x": float(row["x_cord"]) * 800,
                "y": float(row["y_cord"]) * 800
            }
        }
        for _, row in selected_pageranks.iterrows()
    ]
    
    selected_edges = edges_yr[
        (edges_yr['team_id'].isin(sel_teams_ids))&(edges_yr['season']==season)
    ]
    
    edges = [{
        'data': {
            'source': row['source'],
            'target': row['target'],
            'weight': row['weight']
        }
    } for _, row in selected_edges.iterrows()]

    return nodes + edges

@callback(
    Output('pagerank_table_playoffs', 'data'),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_pagerank_table(selected_team, selected_season):
    sel_teams_ids = team_df[team_df['full_name']==selected_team]['id'].to_numpy()
    season = seasons[selected_season]
    
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==season)
    ]
    
    selected_pageranks['pagerank'] = selected_pageranks['pagerank'].round(4)
    
    return selected_pageranks.loc[:,['season','node_name','pagerank']].sort_values('pagerank',ascending=False).to_dict('records')

BASE_STYLESHEET = [
    {'selector': 'node',
     'style': {'label': 'data(label)',
               'width': 'data(pagerank)',
               'height': 'data(pagerank)'}},
    {'selector': '.shot',
     'style': {'background-color': '#FF2C2C', 'opacity': 0.95}},
    {'selector': '.player',
     'style': {'background-color': '#B6E3FF', 'opacity': 0.95}},
    {'selector': 'edge',
     'style': {'source-arrow-shape': 'triangle'}},
]


def with_highlight(node_name):
    return BASE_STYLESHEET + [{
        'selector': f'node[id = "{node_name}"]',
        'style': {
            'border-width': '12px',
            'border-color': '#172B3C',
            'background-color': '#172B3C',
            'opacity': 1,
        }
    }]

#highlights the correct node or element based on clicked node or element
@callback(
    Output('graph_networks_playoffs', 'stylesheet'),
    Output('pagerank_table_playoffs', 'active_cell'),
    Output('pagerank_table_playoffs', 'selected_cells'),
    Output('graph_networks_playoffs', 'tapNodeData'),
    Input('graph_networks_playoffs', 'tapNodeData'),
    Input('pagerank_table_playoffs', 'active_cell'),
    State('pagerank_table_playoffs', 'data'),
    prevent_initial_call=True,
)
def sync_selection(tap_node, active_cell, table_data):
    table_data = table_data or []

    if ctx.triggered_id == 'graph_networks_playoffs':
        if tap_node is None:
            # this is the reset pass firing back into us — ignore it
            return no_update, no_update, no_update, no_update

        name = tap_node['id']
        row = next((i for i, r in enumerate(table_data)
                    if r['node_name'] == name), None)
        if row is None:
            return BASE_STYLESHEET, None, [], None

        cell = {'row': row, 'column': 1, 'column_id': 'node_name'}
        return with_highlight(name), cell, [cell], None

    # table was clicked
    if active_cell is None or active_cell['row'] >= len(table_data):
        return BASE_STYLESHEET, no_update, no_update, None

    name = table_data[active_cell['row']]['node_name']
    return with_highlight(name), no_update, no_update, None

#show datatable with edge weights from node ordered from highest to lowest
@callback(
    Output('passes_weight_table_play', 'data'),
    Output('passes_weight_container_play', 'style'),
    Input("team-dropdown", "value"),
    Input("season-slider", "value"),
    Input('pagerank_table_playoffs', 'active_cell'),
    State('pagerank_table_playoffs', 'data')
)
def update_pass_table(selected_team, selected_season, active_cell, table_data):
    sel_teams_ids = team_df[team_df['full_name']==selected_team]['id'].to_numpy()

    if active_cell is None or not table_data:
        return [], {'display': 'none'}

    season = seasons[selected_season]
    name = table_data[active_cell['row']]['node_name']

    if name in diff_shots:
        weights = edges_yr[
            (edges_yr['season'] == season) &
            (edges_yr['team_id'].isin(sel_teams_ids)) &
            (edges_yr['target'] == name)
        ].sort_values('weight', ascending=False)
        weights = weights.rename(columns={'source': 'node_name', 'target': 'edge_to'})
        
        weights['weight'] = weights['weight'].round(4)
    else:
        weights = edges_yr[
            (edges_yr['season'] == season) &
            (edges_yr['team_id'].isin(sel_teams_ids)) &
            (edges_yr['source'] == name)
        ].sort_values('weight', ascending=False)
        weights = weights.rename(columns={'source': 'node_name', 'target': 'edge_to'})
        
        weights['weight'] = weights['weight'].round(4)
    if weights.empty:
        return [], {'display': 'none'}

    return weights[['season', 'node_name', 'edge_to', 'weight']].to_dict('records'), {'display': 'block'}


@callback(
    Output('player_usage_table_play','data'),
    Input('team-dropdown','value'),
    Input('season-slider','value')
) 
def get_player_usage_dat(selected_team, selected_season):
    season = seasons[selected_season]
    teamid = team_df[team_df['full_name']==selected_team]['id'].to_numpy()
    
    player_usage_play_fil = player_usage_play[(player_usage_play['season']==season)&(player_usage_play['team_id'].isin(teamid))]
    
    player_usage_play_fil['gini'] = player_usage_play_fil['gini'].round(4)
    player_usage_play_fil['entropy'] = player_usage_play_fil['entropy'].round(4)
    player_usage_play_fil['eff_num_players'] = player_usage_play_fil['eff_num_players'].round(4)
    
    return player_usage_play_fil.to_dict('records')

#creating the regular season vs playoff difference dataframe
@callback(
    Output('reg_v_play_heatmap', 'figure'),
    Input('team-dropdown', 'value'),
    Input('season-slider', 'value')
)
def update_reg_v_play_fig(selected_team, selected_season):
    season = seasons[selected_season]
    node_cols = diff_shots + ['gini', 'entropy', 'eff_num_players']

    # ---- regular season: shot pageranks + usage metrics, wide format ----
    reg_shots = pageranks_yr_reg[
        (pageranks_yr_reg['season'] == season) &
        (pageranks_yr_reg['node_name'].isin(diff_shots))
    ][['team_id', 'node_name', 'pagerank']]
    
    reg_usage_long = player_usage[player_usage['season'] == season].melt(
        id_vars=['team_id'], value_vars=['gini', 'entropy', 'eff_num_players'],
        var_name='node_name', value_name='pagerank'
    )

    reg_wide = pd.concat([reg_shots, reg_usage_long], ignore_index=True) \
                 .pivot(index='team_id', columns='node_name', values='pagerank')

    # ---- playoffs: same shape, only playoff teams will exist here ----
    play_shots = pageranks_yr[
        (pageranks_yr['season'] == season) &
        (pageranks_yr['node_name'].isin(diff_shots))
    ][['team_id', 'node_name', 'pagerank']]

    play_usage_long = player_usage_play[player_usage_play['season'] == season].melt(
        id_vars=['team_id'], value_vars=['gini', 'entropy', 'eff_num_players'],
        var_name='node_name', value_name='pagerank'
    )

    play_wide = pd.concat([play_shots, play_usage_long], ignore_index=True) \
                  .pivot(index='team_id', columns='node_name', values='pagerank')

    # align both to playoff teams only + fixed column order
    play_wide = play_wide.reindex(columns=node_cols)
    reg_wide_aligned = reg_wide.reindex(index=play_wide.index, columns=node_cols)

    diff = (play_wide - reg_wide_aligned).fillna(0)

    # normalize each column by its own max absolute value (same as your seaborn version)
    col_max = diff.abs().max()
    col_max = col_max.replace(0, 1)  # avoid divide-by-zero for an all-zero column
    diff_norm = diff.div(col_max)  # default axis='columns' aligns Series index to DataFrame columns

    id_to_name = team_df.set_index('id')['full_name']
    row_labels = diff.index.map(id_to_name)

    fig = px.imshow(
        diff_norm.to_numpy(),
        x=node_cols,
        y=row_labels,
        color_continuous_scale='RdBu_r',
        zmin=-1,
        zmax=1,
        aspect='auto'
    )

    # color comes from diff_norm, but the text shown on each cell is the raw diff value
    fig.update_traces(
        text=diff.round(3).to_numpy(),
        texttemplate='%{text}',
        hovertemplate='%{y} — %{x}<br>raw diff: %{text}<br>normalized: %{z:.2f}<extra></extra>'
    )

    fig.update_layout(
        coloraxis_colorbar=dict(title='Normalized diff'),
        height=max(400, 25 * len(row_labels))
    )
    
    row_labels_list = list(row_labels)
    if selected_team in row_labels_list:
        row_idx = row_labels_list.index(selected_team)
        fig.add_shape(
            type='rect',
            x0=-0.5, x1=len(node_cols) - 0.5,
            y0=row_idx - 0.5, y1=row_idx + 0.5,
            line=dict(color='black', width=3),
            fillcolor='rgba(0,0,0,0)',
            layer='above'
        )
    return fig

#dynamically display playoff bracket
BOX_W, ROW_H = 360, 34
BOX_H = ROW_H * 2
COL_GAP = 90
ROW_GAP = 24
CENTER_GAP = BOX_W + COL_GAP * 2  # reserved space in the middle for the Finals box
LOGO_SIZE = 200  # change this once, offsets below stay correct automatically


ROUND_ORDER = ['first_round', 'conf_semi_final', 'conf_final']


def team_logo(team_name):
    return f"/assets/logos/{team_name.split()[-1].lower()}.png"


def build_conference_bracket(df_season, conference):
    seed_order = [1, 8, 4, 5, 3, 6, 2, 7]
    prev_center = {}
    rounds_out = []

    conf_rounds = [r for r in ROUND_ORDER if r in df_season['round'].unique()]

    for rnd_idx, rnd in enumerate(conf_rounds):
        games = df_season[(df_season['round'] == rnd) & (df_season['conference'] == conference)].copy()

        if rnd_idx == 0:
            games['_slot'] = games.apply(
                lambda r: seed_order.index(min(r['seed_win'], r['seed_lose'])) // 2, axis=1
            )
            games = games.sort_values('_slot').reset_index(drop=True)
            centers = [i * (BOX_H + ROW_GAP) for i in range(len(games))]
        else:
            centers = [
                (prev_center[r['winning_team']] + prev_center[r['losing_team']]) / 2
                for _, r in games.iterrows()
            ]

        round_games = []
        for (_, r), y in zip(games.iterrows(), centers):
            round_games.append({
                'y': y, 'winning_team': r['winning_team'], 'seed_win': r['seed_win'],
                'losing_team': r['losing_team'], 'seed_lose': r['seed_lose'], 'series': r['series']
            })
            prev_center[r['winning_team']] = y
            prev_center[r['losing_team']] = y

        rounds_out.append(round_games)

    return rounds_out


def draw_box(fig, x, y_center, winning_team, seed_win, losing_team, seed_lose, series):
    y0, y1 = y_center - BOX_H / 2, y_center + BOX_H / 2

    fig.add_shape(type='rect', x0=x, x1=x + BOX_W, y0=y0, y1=y1,
                  line=dict(color='#D0D0D0', width=1.5), fillcolor='white')
    fig.add_shape(type='line', x0=x, x1=x + BOX_W, y0=y_center, y1=y_center,
                  line=dict(color='#E8E8E8', width=1))

    fig.add_layout_image(dict(source=team_logo(winning_team), x=x + 6, y=y0 + ROW_H / 2,
                               xref='x', yref='y', sizex=22, sizey=22, xanchor='left', yanchor='middle'))
    fig.add_annotation(x=x + 32, y=y0 + ROW_H / 2, xref='x', yref='y',
                        text=f"{winning_team} ({seed_win})", showarrow=False,
                        font=dict(size=12, color='#172B3C', family='sans-serif'), xanchor='left')

    fig.add_layout_image(dict(source=team_logo(losing_team), x=x + 6, y=y0 + ROW_H + ROW_H / 2,
                               xref='x', yref='y', sizex=22, sizey=22, xanchor='left', yanchor='middle'))
    fig.add_annotation(x=x + 32, y=y0 + ROW_H + ROW_H / 2, xref='x', yref='y',
                        text=f"{losing_team} ({seed_lose})", showarrow=False,
                        font=dict(size=12, color='#AAAAAA', family='sans-serif'), xanchor='left')

    fig.add_trace(go.Scatter(
        x=[x + BOX_W / 2], y=[y_center], mode='markers', marker=dict(opacity=0), showlegend=False,
        hovertext=[f"{series}: {winning_team} def. {losing_team}"], hoverinfo='text'
    ))


def draw_conference(fig, rounds_data, x_for_col, total_cols, finals_x=None, finals_y=None):
    for col, games in enumerate(rounds_data):
        x = x_for_col(col)
        for g in games:
            draw_box(fig, x, g['y'], g['winning_team'], g['seed_win'], g['losing_team'], g['seed_lose'], g['series'])

        if col < total_cols - 1:
            next_x = x_for_col(col + 1)
            from_edge = x + BOX_W if next_x > x else x
            to_edge = next_x if next_x > x else next_x + BOX_W
            mid_x = (from_edge + to_edge) / 2

            next_games = rounds_data[col + 1]
            for g in games:
                target = next((ng for ng in next_games
                               if g['winning_team'] in (ng['winning_team'], ng['losing_team'])), None)
                if not target:
                    continue
                fig.add_shape(type='line', x0=from_edge, x1=mid_x, y0=g['y'], y1=g['y'], line=dict(color='#D0D0D0', width=1.5))
                fig.add_shape(type='line', x0=mid_x, x1=mid_x, y0=g['y'], y1=target['y'], line=dict(color='#D0D0D0', width=1.5))
                fig.add_shape(type='line', x0=mid_x, x1=to_edge, y0=target['y'], y1=target['y'], line=dict(color='#D0D0D0', width=1.5))

    # connector from each conference's last round into the finals box
    if finals_x is not None and rounds_data and rounds_data[-1]:
        last_x = x_for_col(total_cols - 1)
        for g in rounds_data[-1]:
            from_edge = last_x + BOX_W if finals_x > last_x else last_x
            to_edge = finals_x if finals_x > last_x else finals_x + BOX_W
            mid_x = (from_edge + to_edge) / 2
            fig.add_shape(type='line', x0=from_edge, x1=mid_x, y0=g['y'], y1=g['y'], line=dict(color='#D0D0D0', width=1.5))
            fig.add_shape(type='line', x0=mid_x, x1=mid_x, y0=g['y'], y1=finals_y, line=dict(color='#D0D0D0', width=1.5))
            fig.add_shape(type='line', x0=mid_x, x1=to_edge, y0=finals_y, y1=finals_y, line=dict(color='#D0D0D0', width=1.5))


def make_bracket_figure(season):
    df_season = playoff_res[playoff_res['season'] == season]
    west = build_conference_bracket(df_season, 'west')
    east = build_conference_bracket(df_season, 'east')
    total_cols = max(len(west), len(east))

    west_last_x = (total_cols - 1) * (BOX_W + COL_GAP)
    east_start_x = west_last_x + BOX_W + CENTER_GAP  # east's LAST round lands just right of the center gap

    def west_x(col):
        return col * (BOX_W + COL_GAP)

    def east_x(col):
        return east_start_x + (total_cols - 1 - col) * (BOX_W + COL_GAP)

    finals_x = west_last_x + BOX_W + COL_GAP
    west_final_y = west[-1][0]['y'] if west and west[-1] else 0
    east_final_y = east[-1][0]['y'] if east and east[-1] else 0
    finals_y = (west_final_y + east_final_y) / 2

    fig = go.Figure()
    draw_conference(fig, west, west_x, total_cols, finals_x=finals_x, finals_y=finals_y)
    draw_conference(fig, east, east_x, total_cols, finals_x=finals_x, finals_y=finals_y)

    if west:
        fig.add_annotation(x=west_x(0) + BOX_W / 2, y=-70, text='WESTERN CONFERENCE', showarrow=False,
                            font=dict(size=16, family='sans-serif', color='#172B3C'))
    if east:
        fig.add_annotation(x=east_x(0) + BOX_W / 2, y=-70, text='EASTERN CONFERENCE', showarrow=False,
                            font=dict(size=16, family='sans-serif', color='#172B3C'))

    finals_row = playoff_res[(playoff_res['season'] == season) & (playoff_res['round'] == 'finals')]
    if not finals_row.empty:
        row = finals_row.iloc[0]
        draw_box(fig, finals_x, finals_y, row['winning_team'], row['seed_win'],
                 row['losing_team'], row['seed_lose'], row['series'])

        fig.add_layout_image(dict(
            source=team_logo(row['winning_team']),
            x=finals_x + BOX_W / 2 - LOGO_SIZE / 2,
            y=finals_y + BOX_H / 2 + 25,
            xref='x', yref='y',
            sizex=LOGO_SIZE, sizey=LOGO_SIZE
        ))
        fig.add_annotation(x=finals_x + BOX_W / 2, y=finals_y + BOX_H / 2 + 60,
                            text=f"🏆 {row['winning_team']}", showarrow=False,
                            font=dict(size=15, color='#B8860B', family='sans-serif'))

    all_games = [g for r in west + east for g in r]
    max_y = max((g['y'] for g in all_games), default=BOX_H) + BOX_H
    max_x = east_x(0) + BOX_W

    fig.update_layout(
        xaxis=dict(visible=False, range=[-20, max_x + 20]),
        yaxis=dict(visible=False, range=[max_y + 40, -110]),
        plot_bgcolor='white', height=max(500, max_y + 150),
        margin=dict(l=10, r=10, t=20, b=10), showlegend=False
    )
    return fig


@callback(
    Output('playoff-bracket', 'figure'),
    Input('season-slider', 'value')
)
def update_playoff_bracket(selected_season):
    season = seasons[selected_season]
    return make_bracket_figure(season)