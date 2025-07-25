from dash import html, Input, Output, State, dash_table, dcc
from Skrypty import config as cfg
import numpy as np
import dash_bootstrap_components as dbc
from Skrypty.Main import app
import os
import base64
from flask import send_from_directory
import pandas as pd
import io
import dash
from dash import callback_context

from dash.dash_table.Format import Format, Scheme
from dash_ag_grid import AgGrid
from datetime import datetime
from Skrypty.backend.postgres_db import save_df_to_db, load_df_from_db, load_df_from_query
from dash.exceptions import PreventUpdate
import json

empty_df = pd.DataFrame(columns=["Rok", "Cena energii [PLN/MWh]", "Cena gazu [PLN/MWh]"])

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

        dcc.Store(id='podaz-store'), #TODO: (2)
        dcc.Store(id='joined-store'), #TODO: (3)
        dcc.Store(id='rezerwy-store'), #TODO: (4)!

        dcc.Store(id='stored-uploaded-excel', storage_type='session'),
        dcc.Store(id='db-refresh-trigger', data=0, storage_type='session'),

        html.Link(rel='stylesheet', href='/assets/style.css'),
        dcc.Tabs([
            dcc.Tab(label='Dane wejściowe do modelu ze ścieżkami',
                style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'},
                children=[
                    dbc.Container([
                        html.H3("Wczytaj plik Excel (Parameters)", style={"textAlign": "center", "color": "#fec036"}),

                        dcc.Upload(
                            id='upload-energy-prices',
                            children=html.Div([
                                'Przeciągnij i upuść lub kliknij, aby załadować plik .xlsx z danymi wejściowymi'
                            ]),
                            style={
                                'textAlign': 'center',
                                'margin': '10px',
                                'padding': '10px',
                                'border': '1px dashed #fec036',
                                'color': 'white',
                                'backgroundColor': '#2b2b2b',
                            },
                            multiple=False
                        ),

                        dcc.Interval(id='interval-startup', interval=1000, n_intervals=0, max_intervals=1),

                        html.Button("📥 Pobierz załadowany plik Excel", id='download-entire-excel', style={'marginBottom': '10px'}),
                        dcc.Download(id='download-entire-excel-data'),

                        html.Hr(),
                        html.H4("Arkusz: Ceny 2020–2050", style={"color": "#fec036"}),
                        #html.Div(id='output-sheet-ceny'),
                        dcc.Loading(
                            id="loading-output-sheet-ceny",
                            type="circle",
                            children=html.Div(id='output-sheet-ceny')
                        ),

                        html.Hr(),
                        html.H4("Arkusz: Cenotworstwo", style={"color": "#fec036"}),
                        #html.Div(id='output-sheet-cenotworstwo'),
                        dcc.Loading(
                            id="output-sheet-cenotworstwo",
                            type="circle",
                            children=html.Div(id='output-sheet-cenotworstwo')
                        ),

                        html.Hr(),
                        html.H4("Arkusz: Energy_mix", style={"color": "#fec036"}),
                        #html.Div(id='output-sheet-energy-mix'),
                        dcc.Loading(
                            id="loading-output-sheet-energy-mix",
                            type="circle",
                            children=html.Div(id='output-sheet-energy-mix')
                        ),

                        html.Hr(),
                        html.H4("Arkusz: Do ebitda", style={"color": "#fec036"}),
                        #html.Div(id='output-sheet-do-ebitda'),
                        dcc.Loading(
                            id="loading-output-sheet-do-ebitda",
                            type="circle",
                            children=html.Div(id='output-sheet-do-ebitda')
                        ),

                        html.Hr(),
                        html.H4("Arkusz: Zmienne sterujące", style={"color": "#fec036"}),
                        #html.Div(id='output-sheet-zmienne-sterujace'),
                        dcc.Loading(
                            id="loading-output-sheet-zmienne-sterujace",
                            type="circle",
                            children=html.Div(id='output-sheet-zmienne-sterujace')
                        ),
                        html.Hr(),
                    ])
                ]),

            dcc.Tab(label='Historia zmian', style={'backgroundColor': '#1e1e1e', 'color': 'white'},
                    selected_style={'backgroundColor': '#1e1e1e', 'color': 'white', 'borderTop': '4px solid #fec036'}, children=[
                html.Div([
                    html.H3("Historia zmian danych", style={"textAlign": "center", "color": "#fec036"}),
                    dcc.Dropdown(
                        id='history-table-selector',
                        options=[
                            {'label': 'Ceny 2020–2050', 'value': 'ceny_history'},
                            {'label': 'Cenotworstwo', 'value': 'cenotworstwo_history'},
                            {'label': 'Energy_mix', 'value': 'energy_mix_history'},
                            {'label': 'Do ebitda', 'value': 'do_ebitda_history'},
                            {'label': 'Zmienne sterujące', 'value': 'zmienne_sterujace_history'},
                        ],
                        value='cenotworstwo_history'
                    ),
                    html.Br(),
                    html.Button("Załaduj historię", id="load-history-btn", n_clicks=0),
                    html.Br(),
                    dcc.Loading(
                        id="loading-history-table",
                        type="circle",
                        children=html.Div(id='history-table-output')
                    )
                ])
            ])

        ])
    ])
)


@app.callback(
    Output('output-sheet-ceny', 'children'),
    Input('interval-startup', 'n_intervals'),
    Input('db-refresh-trigger', 'data'),
    prevent_initial_call=False
)
def update_ceny_from_db(_, __):
    try:
        df = load_df_from_db("ceny_2020_2050")
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania z bazy danych: {str(e)}")

    return dash_table.DataTable(
        id='energy-parameters-table',
        data=df.to_dict('records'),
        columns=[
            {"name": i, "id": i,
             "type": "numeric",
             "format": Format(precision=2, scheme=Scheme.fixed)}
            if df[i].dtype.kind in 'fi' else {"name": i, "id": i}
            for i in df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={'backgroundColor': '#2b2b2b', 'color': 'white', 'textAlign': 'center'},
        style_header={'backgroundColor': '#484848', 'fontWeight': 'bold', 'color': '#fec036'},
        editable=False,
        row_deletable=False,
    )


@app.callback(
    Output('output-sheet-cenotworstwo', 'children'),
    Input('interval-startup', 'n_intervals'),
    Input('db-refresh-trigger', 'data'),
    prevent_initial_call=False
)
def update_cenotworstwo_from_db(_, __):
    try:
        df = load_df_from_db("cenotworstwo")
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania z bazy danych: {str(e)}")

    return dash_table.DataTable(
        id='energy-cenotworstwo-table',
        data=df.to_dict('records'),
        columns=[
            {"name": i, "id": i,
             "type": "numeric",
             "format": Format(precision=2, scheme=Scheme.fixed)}
            if df[i].dtype.kind in 'fi' else {"name": i, "id": i}
            for i in df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': '#2b2b2b',
            'color': 'white',
            'textAlign': 'center'
        },
        style_header={
            'backgroundColor': '#484848',
            'fontWeight': 'bold',
            'color': '#fec036'
        },
        editable=False,
        row_deletable=False,
    )


@app.callback(
    Output('output-sheet-energy-mix', 'children'),
    Input('interval-startup', 'n_intervals'),
    Input('db-refresh-trigger', 'data'),
    prevent_initial_call=False
)
def update_energy_mix_from_db(_, __):
    try:
        df = load_df_from_db("energy_mix")
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania z bazy danych: {str(e)}")

    return dash_table.DataTable(
        id='energy-energy_mix-table',
        data=df.to_dict('records'),
        columns=[
            {"name": i, "id": i,
             "type": "numeric",
             "format": Format(precision=2, scheme=Scheme.fixed)}
            if df[i].dtype.kind in 'fi' else {"name": i, "id": i}
            for i in df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': '#2b2b2b',
            'color': 'white',
            'textAlign': 'center'
        },
        style_header={
            'backgroundColor': '#484848',
            'fontWeight': 'bold',
            'color': '#fec036'
        },
        editable=False,
        row_deletable=False,
    )


@app.callback(
    Output('output-sheet-do-ebitda', 'children'),
    Input('interval-startup', 'n_intervals'),
    Input('db-refresh-trigger', 'data'),
    prevent_initial_call=False
)
def update_do_ebitda_from_db(_, __):
    try:
        df = load_df_from_db("do_ebitda")
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania z bazy danych: {str(e)}")

    return dash_table.DataTable(
        id='energy-do_ebitda-table',
        data=df.to_dict('records'),
        columns=[
            {"name": i, "id": i,
             "type": "numeric",
             "format": Format(precision=2, scheme=Scheme.fixed)}
            if df[i].dtype.kind in 'fi' else {"name": i, "id": i}
            for i in df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': '#2b2b2b',
            'color': 'white',
            'textAlign': 'center'
        },
        style_header={
            'backgroundColor': '#484848',
            'fontWeight': 'bold',
            'color': '#fec036'
        },
        editable=False,
        row_deletable=False,
    )


@app.callback(
    Output('output-sheet-zmienne-sterujace', 'children'),
    Input('interval-startup', 'n_intervals'),
    Input('db-refresh-trigger', 'data'),
    prevent_initial_call=False
)
def update_zmienne_sterujace_from_db(_, __):
    try:
        df = load_df_from_db("zmienne_sterujace")
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania z bazy danych: {str(e)}")

    return dash_table.DataTable(
        id='energy-zmienne_sterujace-table',
        data=df.to_dict('records'),
        columns=[
            {"name": i, "id": i,
             "type": "numeric",
             "format": Format(precision=2, scheme=Scheme.fixed)}
            if df[i].dtype.kind in 'fi' else {"name": i, "id": i}
            for i in df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': '#2b2b2b',
            'color': 'white',
            'textAlign': 'center'
        },
        style_header={
            'backgroundColor': '#484848',
            'fontWeight': 'bold',
            'color': '#fec036'
        },
        editable=False,
        row_deletable=False,
    )


@app.callback(
    Output("download-entire-excel-data", "data"),
    Input("download-entire-excel", "n_clicks"),
    State("stored-uploaded-excel", "data"),
    prevent_initial_call=True,
)
def download_entire_excel(n_clicks, stored_base64_data):
    if not stored_base64_data:
        raise dash.exceptions.PreventUpdate

    decoded_bytes = base64.b64decode(stored_base64_data)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
    filename = f"Zaladowany_plik_{timestamp}.xlsx"

    return dcc.send_bytes(lambda buffer: buffer.write(decoded_bytes), filename=filename)


@app.callback(
    Output('db-refresh-trigger', 'data'),
    Input('upload-energy-prices', 'contents'),
    State('upload-energy-prices', 'filename'),
    State('db-refresh-trigger', 'data')
)
def handle_excel_upload(contents, filename, refresh_state):
    if contents is None:
        raise dash.exceptions.PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        xls = pd.ExcelFile(io.BytesIO(decoded))

        df_ceny = pd.read_excel(xls, sheet_name="Ceny 2020-2050")
        df_cenotworstwo = pd.read_excel(xls, sheet_name="Cenotworstwo")
        df_mix = pd.read_excel(xls, sheet_name="Energy_mix")
        df_do_ebitda = pd.read_excel(xls, sheet_name="do ebitda")
        df_zmienne_sterujace = pd.read_excel(xls, sheet_name="zmienne sterujące")

        # Walidacja (opcjonalnie twarde asserty)

        save_df_to_db(df_ceny, "ceny_2020_2050")
        save_df_to_db(df_cenotworstwo, "cenotworstwo")
        save_df_to_db(df_mix, "energy_mix")
        save_df_to_db(df_do_ebitda, "do_ebitda")
        save_df_to_db(df_zmienne_sterujace, "zmienne_sterujace")

        return refresh_state + 1  # trigger refresh

    except Exception as e:
        print(f"Błąd: {str(e)}")
        raise dash.exceptions.PreventUpdate


@app.callback(
    Output('stored-uploaded-excel', 'data'),
    Input('upload-energy-prices', 'contents'),
)
def store_uploaded_file(contents):
    if contents is None:
        raise dash.exceptions.PreventUpdate

    try:
        _, content_string = contents.split(',')
        return content_string
    except Exception as e:
        print(f"❌ Błąd przy zapisywaniu pliku do Store: {e}")
        raise dash.exceptions.PreventUpdate



@app.callback(
    Output('history-table-output', 'children'),
    Input('load-history-btn', 'n_clicks'),
    State('history-table-selector', 'value'),
)
def load_history(n_clicks, table_name):
    if n_clicks == 0:
        raise dash.exceptions.PreventUpdate

    # Proste zapytanie bez dodatkowych filtrów
    query = f"""
        SELECT *
        FROM {table_name}
        ORDER BY changed_at DESC
    """

    try:
        df = load_df_from_query(query)
    except Exception as e:
        return html.Div(f"❌ Błąd podczas ładowania historii: {e}")

    if df.empty:
        return html.Div("Brak wyników.")

    # Obsługa historii cenotworstwa (parsowanie JSON)
    if table_name == 'cenotworstwo_history' and "old_data" in df.columns:
        try:
            def try_parse(x):
                if isinstance(x, str):
                    cleaned = x.replace('""', '"')
                    return json.loads(cleaned)
                elif isinstance(x, dict):
                    return x
                else:
                    return None

            df["old_data_parsed"] = df["old_data"].apply(try_parse)
            df = df[df["old_data_parsed"].notnull()]
            old_data_expanded = pd.json_normalize(df["old_data_parsed"])
            df = pd.concat([df.drop(columns=["old_data", "old_data_parsed"]), old_data_expanded], axis=1)

            # Uporządkuj kolumny
            meta_cols = ["id", "changed_at", "changed_by", "action_type"]
            fixed_cols = ["jednostka", "Dodatki do cenotwórstwa w rozbiciu na lata"]
            year_cols = [str(y) for y in range(2022, 2061)]
            desired_order = meta_cols + fixed_cols + [col for col in year_cols if col in df.columns]
            df = df[[col for col in desired_order if col in df.columns]]

            for col in year_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

        except Exception as e:
            return html.Div(f"❌ Błąd przy przetwarzaniu kolumny 'old_data': {e}")

    # Tabela wyjściowa
    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns],
        style_table={'overflowX': 'auto', 'maxWidth': '100%'},
        style_cell={
            'backgroundColor': '#2b2b2b',
            'color': 'white',
            'textAlign': 'center',
            'whiteSpace': 'normal',
            'wordBreak': 'break-word',
            'minWidth': '25px',
            'maxWidth': '200px',
            'fontSize': '10px',    
            'padding': '1px', 
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Dodatki do cenotwórstwa w rozbiciu na lata'},
                'textAlign': 'left',
                'minWidth': '180px',
                'maxWidth': '600px',
                'whiteSpace': 'normal',
            },
            {
                'if': {'column_id': 'changed_at'},
                'minWidth': '100px',
                'maxWidth': '150px',
            },
            {
                'if': {'column_id': 'changed_by'},
                'minWidth': '100px',
                'maxWidth': '150px',
            },
        ],
        style_data={'height': '16px', 'lineHeight': '8px'},
        style_header={
            'backgroundColor': '#484848',
            'fontWeight': 'bold',
            'color': '#fec036',
            'textAlign': 'center',
            'fontSize': '9px', 
            'padding': '1px', 
        },
    )




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8502)