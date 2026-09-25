import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]
import numpy as np # type: ignore[import-not-found]

import dash # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
import plotly.express as px
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
            dcc.Graph(id='reg_v_play_heatmap',
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
    
    player_usage_play_fil = player_usage_play[(player_usage_play['season']==season)&(player_usage_play['team_id']==teamid)]
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

    # team_id -> full_name for row labels, keeping diff's row order
    id_to_name = team_df.set_index('id')['full_name']
    row_labels = diff.index.map(id_to_name)

    zmax = diff.abs().to_numpy().max() if diff.size else 1
    zmax = zmax if zmax > 0 else 1

    fig = px.imshow(
        diff.to_numpy(),
        x=node_cols,
        y=row_labels,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        zmin=-zmax,
        zmax=zmax,
        aspect='auto'
    )
    fig.update_layout(
        coloraxis_colorbar=dict(title='Playoffs − Reg'),
        height=max(400, 25 * len(row_labels))
    )

    # ---- highlight the selected team's row ----
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