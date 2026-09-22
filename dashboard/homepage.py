# app.py
import dash
from dash import Dash, html, dcc
app = Dash(__name__, use_pages=True,suppress_callback_exceptions=True)

app.layout = html.Div([
    html.H1("NBA GRAPH NETWORKS",
            style={
                "fontFamily": 'sans-serif',
                "fontWeight": 'bold'}),
    html.Div(
        "How are NBA Offenses different? Do teams follow a similar pattern? "
        "Do strategies change in the Playoffs? All these questions can be "
        "answered using network structure! This dashboard will display the "
        "results from a network for a given season and team.",
        style={
            "fontFamily": 'sans-serif',
            "fontSize": "20px",
            "marginTop": "0px"
        }
    ),
    html.Br(),
    html.Div([
        dcc.Link(page['name'], href=page['relative_path'])
        for page in dash.page_registry.values()
    ]),
    dash.page_container  # Dash swaps content here based on URL
])

if __name__ == "__main__":
    app.run(debug=True)