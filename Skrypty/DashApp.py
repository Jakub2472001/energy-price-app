from dash import html, Input, Output,State, dash_table, dcc
import config as cfg
import numpy as np
import dash_bootstrap_components as dbc
from DataTransforms import calculate_residual_y, define_podaz_table, define_magazyny_table
from LoadData import podaz_df
from DashPlots import plot_podaz_popyt, annotate_plot
from Main import app

magazyny_table = html.Div([dash_table.DataTable(
    id='datatable-magazyny',
    columns=[{'name': i, 'id': i, 'deletable': True} for i in
             ['nazwa', cfg.pojemnosc_col, cfg.moc_zatl_col, cfg.moc_odb_col]],
    editable=False,
    sort_action="native",
    sort_mode='multi',
    style_table={
        'overflowX': 'auto',
        'maxWidth': '100%',  # Limit the width of the table
    },
    style_cell={
        'backgroundColor': '#2b2b2b',
        'color': '#f3f6fa',
        'textAlign': 'left',
        'whiteSpace': 'normal',  # Allow text to wrap
        'height': 'auto',  # Allow row height to adjust based on content
        'padding': '10px',  # Add some padding for better spacing
    },
    style_header={
        'backgroundColor': '#484848',
        'fontWeight': 'bold',
        'color': '#fec036',
        'whiteSpace': 'normal',  # Allow header text to wrap
        'textAlign': 'center',  # Center align header text
        'height': 'auto',  # Allow header height to adjust based on content
    },
),
    html.Link(rel='stylesheet', href='/assets/style.css')])

selected_style = {'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'}
# Define the layout of the app
app.layout = (
    html.Div(style={"backgroundColor": "#1e1e1e"}, children=[
        html.Link(rel='stylesheet', href='/assets/style.css'),
        dcc.Tabs([
            dcc.Tab(label='Założenia', style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                    selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'},
                    children=[
                        dbc.Container([
                            dbc.Row([
                                dbc.Col([
                                    html.H3("Źródła", style={"textAlign": "center", 'color': "#fec036"}),
                                    html.Div(define_podaz_table(podaz_df)),
                                    html.H3("Magazyny", style={"textAlign": "center", 'color': "#fec036"}),
                                    html.Div(magazyny_table),
                                    html.Button('Dodaj magazyn', id='editing-rows-button', n_clicks=0),
                                    dcc.Store(id='residual-calculation'),
                                    dcc.Store(id='year-df-datatable'),
                                    dcc.Store(id="results-datatable"),
                                ], width=3, style={"backgroundColor": "#1e1e1e"}),

                                dbc.Col([
                                    dcc.Dropdown(options=[
                                        {'label': 'Wysokie zapotrzebowanie w e.e.', 'value': cfg.scen_1_name},
                                        {'label': 'Niskie zapotrzebowanie w e.e.', 'value': cfg.scen_2_name},
                                        {'label': 'S3 zapotrzebowanie w e.e.', 'value': cfg.scen_3_name},
                                    ],
                                    value=cfg.scen_1_name, id='scenario-selector'),

                                    dcc.Dropdown(options=[
                                        {'label': 'Import w okresie zimowym', 'value': True},
                                        {'label': 'Brak importu w okresie zimowym', 'value': False},
                                    ],
                                    value=False, id='import-selector'),

                                    dcc.Dropdown(options=[
                                        {'label': 'Bazowy', 'value': 'bazowy.xlsx'},
                                        {'label': 'D1', 'value': 'D1.xlsx'},
                                        {'label': 'D2', 'value': 'D2.xlsx'},
                                        {'label': 'D3', 'value': 'D3.xlsx'},
                                        {'label': 'K1', 'value': 'K1.xlsx'},
                                        {'label': 'K2', 'value': 'K2.xlsx'},
                                        {'label': 'K3', 'value': 'K3.xlsx'},
                                        {'label': 'M1', 'value': 'M1.xlsx'},
                                    ],
                                    value='bazowy.xlsx', id='storage-investment-scenario'),

                                    dcc.Dropdown(options=[
                                        {'label': c, 'value': c} for c in podaz_df['źródło'] if c not in ['UA', 'SK (Vyrawa)']],
                                        multi=True, value=[c for c in podaz_df['źródło']], id='źródła-selector'),

                                    html.H3("Zródła gazu i zapotrzebowanie", style={"textAlign": "center", "color": "#fec036"}),
                                    dcc.Slider(id='year_slider', value=cfg.start_year, min=cfg.start_year, max=cfg.end_year, step=1,
                                               marks={int(y): str(int(y)) for y in np.arange(cfg.start_year, cfg.end_year + 1)}),
                                    dcc.Dropdown(options=[
                                        {'label': 'GWh', 'value': 1e3},
                                        {'label': 'mln m3', 'value': cfg.m3_to_kWh * 1e3},
                                    ],
                                    value=1e3, id='units-selector'),

                                    dcc.Loading(
                                        id="loading-podaz-popyt-figure",
                                        type="circle",
                                        children=[dcc.Graph(id="podaz-popyt-figure")]
                                    ),
                                    html.Div(id='output-container', style={'margin-top': '20px'}),

                                    dcc.Loading(
                                        id="loading-residual-figure",
                                        type="circle",
                                        children=[dcc.Graph(id="residual-figure")]
                                    ),
                                    html.Div(id='output-resid-container', style={'margin-top': '20px'}),
                                ], width=9, style={"backgroundColor": "#2b2b2b"}),
                            ])
                        ])
                    ]),

            dcc.Tab(label='Analiza wystarczalności 2025-2040', style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                    selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'},
                    children=[
                        dbc.Container([
                            dbc.Row([
                                html.Button('Wykonaj obliczenia', id='run-all_year-calc', n_clicks=0),
                            ]),
                            dbc.Row([
                                html.H3("Bilans energii", style={"textAlign": "center", 'color': "#fec036"}),
                                dcc.Loading(
                                    id="loading-year-barplots",
                                    type="circle",
                                    children=[dcc.Graph(id="year-barplots-figure")]
                                ),
                            ]),
                            dbc.Row([
                                html.H3("Bilans mocy", style={"textAlign": "center", 'color': "#fec036"}),
                                dcc.Loading(
                                    id="loading-year-moce",
                                    type="circle",
                                    children=[dcc.Graph(id="year-moce-figure")]
                                ),
                            ]),
                            dbc.Row([
                                dcc.Download(id="download-ts-results-csv"),
                                dcc.Download(id="download-yearly-results-xlsx"),
                            ])
                        ])
                    ]),

            dcc.Tab(label='Godzinowa symulacja magazynów', style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                    selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'},
                    children=[
                        dbc.Container([
                            dbc.Row(dcc.Slider(id='year-slider-secondary', value=cfg.start_year, min=cfg.start_year,
                                                max=cfg.end_year, step=1, marks={int(y): str(int(y)) for y in
                                                np.arange(cfg.start_year, cfg.end_year + 1)}),
                            ),
                            dbc.Row([
                                html.H3("Suma pracy i stanu naładowania magazynów", style={"textAlign": "center", 'color': "#fec036"}),
                                dcc.Loading(
                                    id="loading-opt-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="opt-storage-figure")]
                                ),
                                html.H3("Magazyny złożowe", style={"textAlign": "center", 'color': "#fec036"}),
                                dcc.Loading(
                                    id="loading-sanok-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="sanok-storage-figure")]
                                ),
                                dcc.Loading(
                                    id="loading-wierzchowice-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="wierzchowice-storage-figure")]
                                ),
                                html.H3("Magazyny kawernowe", style={"textAlign": "center", 'color': "#fec036"}),
                                dcc.Loading(
                                    id="loading-kosakowo-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="kosakowo-storage-figure")]
                                ),
                                dcc.Loading(
                                    id="loading-mogilno-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="mogilno-storage-figure")]
                                ),
                                dcc.Loading(
                                    id="loading-damaslawek-storage-figure",
                                    type="circle",
                                    children=[dcc.Graph(id="damasławek-storage-figure")]
                                )
                            ])
                        ])
                    ])
        ])
    ])
)



if __name__ == '__main__':
    app.run(host = "0.0.0.0", port =8502)
