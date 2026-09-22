# app.py
from dash import Dash, html, dcc
app = Dash(__name__, use_pages=True)

app.layout = html.Div([
    html.H1("NBA GRAPH NETWORKS"),
    dcc.Tabs(id='tabs', value=None, children=[
        dcc.Tab(label=page['name'], value=page['relative_path'])
        for page in dash.page_registry.values()
    ]),
    dash.page_container  # Dash swaps content here based on URL
])

if __name__ == "__main__":
    app.run(debug=True)