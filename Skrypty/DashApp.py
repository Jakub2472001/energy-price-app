from dash import html, Input, Output, State, dash_table, dcc
import config as cfg
import numpy as np
import dash_bootstrap_components as dbc
from DataTransforms import calculate_residual_y, define_podaz_table, define_magazyny_table
#from LoadData import podaz_df,load_podaz_df
from LoadData import load_podaz_df
from DashPlots import plot_podaz_popyt, annotate_plot
from Main import app
import os
import base64
from flask import send_from_directory



magazyny_table = html.Div([dash_table.DataTable(
    id='datatable-magazyny',
    columns=[{'name': i, 'id': i, 'deletable': True} for i in
             ['nazwa', cfg.pojemnosc_col, cfg.moc_zatl_col, cfg.moc_odb_col]],
    editable=False,
    sort_action="native",
    sort_mode='multi',
    style_table={
        'overflowX': 'auto',
        'maxWidth': '100%',
    },
    style_cell={
        'backgroundColor': '#2b2b2b',
        'color': '#f3f6fa',
        'textAlign': 'left',
        'whiteSpace': 'normal',
        'height': 'auto',
        'padding': '10px',
    },
    style_header={
        'backgroundColor': '#484848',
        'fontWeight': 'bold',
        'color': '#fec036',
        'whiteSpace': 'normal',
        'textAlign': 'center',
        'height': 'auto',
    },
),
    html.Link(rel='stylesheet', href='/assets/style.css')])

selected_style = {'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'}

# Define the layout of the app
app.layout = (
    html.Div(style={"backgroundColor": "#1e1e1e"}, children=[
        dcc.Store(id='is-calculating', data=False),
        dcc.Store(id='uploaded-files-store'),
        html.Link(rel='stylesheet', href='/assets/style.css'),
        dcc.Tabs([
            dcc.Tab(label='Założenia', style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                    selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'},
                    children=[
                        dbc.Container([
                            dbc.Row([
                                dbc.Col([
                                    html.H3("Źródła", style={"textAlign": "center", 'color': "#fec036"}),
                                    #html.Div(define_podaz_table(podaz_df)),
                                    dcc.Loading(
                                        id="loading-podaz-table", type="circle", children=[
                                            html.Div(id='output-datatable-podaz', children=define_podaz_table(load_podaz_df()))  # Tabela w Div
                                        ]
                                    ),
                                    html.H3("Magazyny", style={"textAlign": "center", 'color': "#fec036"}),

                                    dcc.Upload(
                                        id='upload-data',
                                        children=html.Div([
                                            'Załącz pliki .xlsx ze scenariuszami z listy [bazowy, D1, D2, D3, K1, K2, K3, M1]',
                                        ]),
                                        style={
                                            'textAlign': 'center',
                                            'margin': '10px'
                                        },
                                        multiple=True
                                    ),
                                    html.Div(id='output-div'),
                                    html.Div(id='output-datatable'),

                                    #html.Div(magazyny_table),

                                    dcc.Loading(
                                        id="loading-magazyny-table", type="circle", children=[
                                            html.Div(id='output-datatable-magazyny', children=magazyny_table)
                                        ]
                                    ),

                                    html.Button('Dodaj magazyn', id='editing-rows-button', n_clicks=0),
                                    dcc.Store(id='residual-calculation'),
                                    dcc.Store(id='year-df-datatable'),
                                    dcc.Store(id="results-datatable"),
                                ], width=3, style={"backgroundColor": "#1e1e1e"}),

                                dbc.Col([
                                    dcc.Upload(
                                        id='upload-main-data',
                                        children=html.Div([
                                            'Załącz plik .xlsx z założeniami',
                                        ]),
                                        style={
                                            'textAlign': 'center',
                                            'margin': '10px'
                                        },
                                            multiple=True
                                    ),
                                    html.Div(id='output-div-main'),

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

                                    dcc.Dropdown(id='storage-investment-scenario', options=[], value=None),  # Dropdown z plikami

                                    dcc.Dropdown(options=[
                                        {'label': c, 'value': c} for c in load_podaz_df()['źródło'] if
                                        c not in ['UA', 'SK (Vyrawa)']],
                                        multi=True, value=[c for c in load_podaz_df()['źródło']], id='źródła-selector'),

                                    html.H3("Zródła gazu i zapotrzebowanie",
                                            style={"textAlign": "center", "color": "#fec036"}),
                                    dcc.Slider(id='year_slider', value=cfg.start_year, min=cfg.start_year,
                                               max=cfg.end_year, step=1,
                                               marks={int(y): str(int(y)) for y in
                                                      np.arange(cfg.start_year, cfg.end_year + 1)}),
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
                                    dcc.Loading(
                                        id="loading-residual-figure",
                                        type="circle",
                                        children=[dcc.Graph(id="residual-figure")]
                                    ),
                                    html.Div(id='output-resid-container', style={'margin-top': '20px'}),
                                ], width=9, style={"backgroundColor": "#2b2b2b"}),
                            ])
                        ]),

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


def get_available_files(data_folder):
    available_files = ["bazowy.xlsx", "D1.xlsx", "D2.xlsx", "D3.xlsx", "K1.xlsx", "K2.xlsx", "K3.xlsx", "M1.xlsx"]
    existing_files = [f for f in available_files if f in os.listdir(data_folder)]
    return existing_files


@app.callback(
    Output('output-div', 'children'),
    Output('uploaded-files-store', 'data'),
    Output('storage-investment-scenario', 'options'),
    Output('storage-investment-scenario', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('upload-data', 'last_modified'))
def display_uploaded_file(list_of_contents, list_of_names, list_of_dates):
    data_subfolder_scenarios = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage_Scenarios'))

    if list_of_contents is not None and list_of_names is not None:

        # Usunięcie wszystkich plików z podfolderu Usage_Scenarios
        for filename in os.listdir(data_subfolder_scenarios):
            file_path = os.path.join(data_subfolder_scenarios, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        saved_files = []

        for content, name in zip(list_of_contents, list_of_names):
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)

            file_path = os.path.join(data_subfolder_scenarios, name)
            with open(file_path, 'wb') as f:
                f.write(decoded)

            saved_files.append(name)

        # Generowanie opcji dla dropdowna
        options = [{'label': name.replace('.xlsx', ''), 'value': name} for name in saved_files]

        return (
            [html.A(name, href=f'/download_scenarios/{name}', style={
                'border': '1px dashed #007eff',
                'padding': '5px',
                'borderRadius': '5px',
                'backgroundColor': '#2b2b2b',
                'fontSize': '14px',
                'display': 'block',
                'color': 'white',
                'textDecoration': 'underline',
            }) for name in saved_files],
            saved_files,
            options,
            options[0]['value'] if options else None
        )

    # Sprawdzenie dostępnych plików
    existing_files = get_available_files(data_subfolder_scenarios)

    if existing_files:
        return (
            [html.A(name, href=f'/download_scenarios/{name}', style={
                'border': '1px dashed #007eff',
                'padding': '5px',
                'borderRadius': '5px',
                'backgroundColor': '#2b2b2b',
                'fontSize': '14px',
                'display': 'block',
                'color': 'white',
                'textDecoration': 'underline',
            }) for name in existing_files],
            [],
            [{'label': name.replace('.xlsx', ''), 'value': name} for name in existing_files],
            existing_files[0] if existing_files else None
        )

    return (
        html.H4("Nie załączono żadnego pliku.", style={
            'border': '1px dashed #007eff',
            'padding': '5px',
            'borderRadius': '5px',
            'backgroundColor': '#2b2b2b',
            'fontSize': '12px',
        }),
        [],
        [],
        None
    )


@app.server.route('/download_scenarios/<filename>')
def download_file_scenarios(filename):
    data_subfolder_scenarios = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage_Scenarios'))
    return send_from_directory(data_subfolder_scenarios, filename, as_attachment=True)


@app.callback(
    Output('output-div-main', 'children'),
    Input('upload-main-data', 'contents'),
    State('upload-main-data', 'filename'),
    State('upload-main-data', 'last_modified'))
def display_uploaded_main_file(list_of_contents, list_of_names, list_of_dates):
    #data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane'))
    data_subfolder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage'))

    if isinstance(list_of_names, str):
        list_of_names = [list_of_names]

    if list_of_contents is not None and list_of_names is not None and len(list_of_names) > 0:

        # Usunięcie wszystkich plików z podfolderu Usage
        for filename in os.listdir(data_subfolder):
            file_path = os.path.join(data_subfolder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        saved_files = []

        for content, name in zip(list_of_contents, list_of_names):
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)

            file_path = os.path.join(data_subfolder, name)  # Zmiana na data_subfolder

            with open(file_path, 'wb') as f:
                f.write(decoded)
                saved_files.append(name)

            #if name == "2025_04_15_Model pracy PMG_założenia.xlsx":
            #    global podaz_df
            #    podaz_df = load_podaz_df()  # Wczytaj nowe dane
            #    updated_table = define_podaz_table(podaz_df)

        return (
            [html.A(name, href=f'/download/{name}', style={
                'border': '1px dashed #007eff',
                'padding': '5px',
                'borderRadius': '5px',
                'backgroundColor': '#2b2b2b',
                'fontSize': '14px',
                'display': 'block',
                'color': 'white',
                'textDecoration': 'underline',
            }) for name in saved_files]
        )

    # Sprawdzenie, czy istnieje plik z "Model pracy PMG_założenia" w nazwie
    existing_files = [f for f in os.listdir(data_subfolder) if "Model pracy PMG_założenia" in f]

    if existing_files:
        return (
            [html.A(name, href=f'/download/{name}', style={
                'border': '1px dashed #007eff',
                'padding': '5px',
                'borderRadius': '5px',
                'backgroundColor': '#2b2b2b',
                'fontSize': '14px',
                'display': 'block',
                'color': 'white',
                'textDecoration': 'underline',
            }) for name in existing_files]
        )

    return (
        html.H4("Nie załączono żadnego pliku.", style={
            'border': '1px dashed #007eff',
            'padding': '5px',
            'borderRadius': '5px',
            'backgroundColor': '#2b2b2b',
            'fontSize': '12px',
        }),
        [],
    )


@app.server.route('/download/<filename>')
def download_file(filename):
    data_subfolder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage'))
    return send_from_directory(data_subfolder, filename, as_attachment=True)


@app.callback(
    Output('output-datatable-podaz', 'children'),
    Input('upload-main-data', 'contents')
)
def update_table(contents):
    print("UPDATE TABELI PODAŻOWEJ")
    df = load_podaz_df()
    return define_podaz_table(df)



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8502)