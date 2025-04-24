from Styling import main_layout
import plotly.express as px
import pandas as pd
import config as cfg
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from Main import app
from dash import Input, Output, ctx, State
from dash.exceptions import PreventUpdate
from DataTransforms import calc_year_sim, run_all_years_sim
#from LoadData import load_magazyny_df, max_demand
from LoadData import load_magazyny_df, get_max_demand, join_data #TODO: POPRAWIONE

from LoadData import load_rezerwy_data
from dash import html
from dash import Dash, dcc


@app.callback(
    Output("year-barplots-figure", "figure"),
    Output("year-moce-figure", "figure"),
    Output("results-datatable", "data"),
    Output("download-yearly-results-xlsx", "data"),
    Output('is-calculating', 'data'),
    Input('scenario-selector', 'value'),
    Input('import-selector', 'value'),
    Input('run-all_year-calc', 'n_clicks'),
    Input('datatable-podaz', 'data'),
    Input('źródła-selector', 'value'),
    Input('storage-investment-scenario', 'value'),
    State('is-calculating', 'data')  # Sprawdzamy stan obliczeń
)
def plot_all_years_bars(popyt_ccgt_scen_name, import_selector, n_clicks, podaz_df, zrodla, storage_investment_scenario,
                        is_calculating):
    if is_calculating:
        raise PreventUpdate

    if storage_investment_scenario is None:
        raise PreventUpdate  # Zatrzymaj, jeśli nie wybrano pliku

    is_calculating = True

    print('start plot_all_years_bars')

    if ctx.triggered_id == 'run-all_year-calc':
        print('rozpoczynam roczne wyliczenia')

        results_df, all_gas_demands, storage_results_df, all_years_h = run_all_years_sim(popyt_ccgt_scen_name,
                                                                                         import_selector, podaz_df,
                                                                                         zrodla,
                                                                                         storage_investment_scenario)

        ts_save = pd.merge(storage_results_df, all_years_h, left_on=cfg.datetime_col_name,
                           right_on=cfg.datetime_col_name)
        results_df_excel = results_df.T

        results_long = pd.melt(results_df.reset_index(names='rok'), id_vars='rok',
                               value_vars=['dostarczony gaz z magazynów', 'niedostarczony gaz z magazynów'])
        results_long['rok'] = results_long['rok'].astype(str)

        fig4 = px.bar(results_long, x="rok", y="value", color='variable', text_auto='.2s',
                      title="zapotrzebowanie i produkcja z magazynów")
        fig4.update_layout(main_layout)
        fig4.update_xaxes(showgrid=False, showline=False)
        fig4.update_yaxes(showgrid=False)
        fig4.update_layout(yaxis_title='MWh')

        moce_long = pd.melt(results_df.reset_index(names='rok'), id_vars='rok',
                            value_vars=['maksymalna moc magazynów', 'zapotrzebowanie na moc w magazynach'])
        moce_long['rok'] = moce_long['rok'].astype(str)
        fig5 = px.line(moce_long, x="rok", y="value", color='variable', title="Wystarczalność mocy")
        fig5.update_layout(main_layout)
        fig5.update_xaxes(showgrid=False, showline=False)
        fig5.update_yaxes(showgrid=False)
        fig5.update_layout(yaxis_title='MW')

        print('skonczony roczny wykres')

        # Ustaw is-calculating na False
        is_calculating = False

        return fig4, fig5, storage_results_df.to_dict('records'), dcc.send_data_frame(results_df_excel.to_excel,
                                                                                      'yearly_%s_wint_imp_%s_infr_%s.xlsx' % (
                                                                                      popyt_ccgt_scen_name,
                                                                                      import_selector,
                                                                                      storage_investment_scenario)), is_calculating
    else:
        raise PreventUpdate


def plot_residual(residual, units, u_label):
    print('start plot_residual')
    residual.loc[:, cfg.datetime_col_name] = pd.to_datetime(residual[cfg.datetime_col_name],
                                                            format=cfg.datetime_format_dash)
    residual.loc[:, cfg.demand_name] = (residual.loc[:, cfg.demand_name] / units).round(2)
    fig = px.line(residual, x=cfg.datetime_col_name, y=cfg.demand_name, title=cfg.demand_name,
                  color_discrete_sequence=['darkorange'])

    fig.update_layout(main_layout)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update(layout_showlegend=False)

    fig.update_layout(yaxis_title='Zapotrzebowanie do magazynów [%s/h]' % u_label)
    print('done plotting residual')

    return fig


@app.callback(
    Output("podaz-popyt-figure", "figure"),
    Output("residual-figure", "figure"),
    Input('year-df-datatable', 'data'),
    Input('residual-calculation', 'data'),
    Input('scenario-selector', 'value'),
    Input('units-selector', 'value'),
    State('units-selector', 'options'),
)
def plot_podaz_popyt(year_df, residual, scen_name, units, opt):
    print('start plot_podaz_popyt')
    u_label = [x['label'] for x in opt if x['value'] == units][0]

    year_df = pd.DataFrame(year_df)
    residual = pd.DataFrame(residual)

    chosen_demand = ['zap. bez e.e.MWh/h', scen_name]
    year_df.loc[:, chosen_demand] = (year_df.loc[:, chosen_demand] / units).round(2)
    year_df.loc[:, 'suma podaży'] = (year_df.loc[:, 'suma podaży'] / units).round(2)

    plot_df = year_df.melt(id_vars=cfg.datetime_col_name, value_vars=chosen_demand)
    fig = px.area(plot_df, x=cfg.datetime_col_name, y='value', color="variable",
                  category_orders={'variable': chosen_demand})
    fig2 = px.line(year_df, x=cfg.datetime_col_name, y='suma podaży')
    fig2.update_traces(line=dict(color='white', dash='dash', width=2), name='dostępne źródła', showlegend=True)

    subfig = make_subplots()
    subfig.add_traces(fig.data + fig2.data)

    subfig.update_layout(main_layout)
    subfig.update_xaxes(showgrid=False, showline=False)
    subfig.update_yaxes(showgrid=False)
    subfig.update_layout(yaxis_title='Zapotrzebowanie na gaz [%s/h]' % u_label)
    subfig.update_yaxes(range=[0, get_max_demand(join_data()) / units]) #TODO: POPRAWIONE

    resid_plot = plot_residual(residual, units, u_label)
    print('done plotting podaz popyt')

    return subfig, resid_plot


@app.callback(
    Output("opt-storage-figure", "figure"),
    Output("sanok-storage-figure", "figure"),
    Output("wierzchowice-storage-figure", "figure"),
    Output("kosakowo-storage-figure", "figure"),
    Output("mogilno-storage-figure", "figure"),
    Output("damasławek-storage-figure", "figure"),
    Input('results-datatable', 'data'),
    Input('year-slider-secondary', 'value'),
    Input('units-selector', 'value'),
    State('units-selector', 'options'),
    Input('storage-investment-scenario', 'value'),
)
def plot_opt_storage(storage_results_table, year, units, opt, storage_investment_scenario):
    print('start calc_opt_storage: ', ctx.triggered_id)

    if ctx.triggered_id is not None and ctx.triggered_id != 'datatable-magazyny' and len(
            pd.DataFrame(storage_results_table)) > 0:
        u_label = [x['label'] for x in opt if x['value'] == units][0]

        magazyny_df, _ = load_magazyny_df(path=storage_investment_scenario)
        magazyny_y_df = magazyny_df[year]
        magazyny_y_df.loc['Magazyny łącznie', :] = magazyny_y_df.sum(axis=0)
        results_df = pd.DataFrame(storage_results_table)
        results_df.loc[:, cfg.datetime_col_name] = pd.to_datetime(results_df.loc[:, cfg.datetime_col_name],
                                                                  format=cfg.datetime_format_dash)
        results_df = results_df.set_index(cfg.datetime_col_name)
        y_mask = results_df['rok'] == year
        results_df = results_df[y_mask]

        # Magazyny po kolei zdejmują zapotrzebowania z całkowitego zapotrzebowania do magazynów.
        storage_op_fig = make_storage_fig(results_df, 'Magazyny łącznie', magazyny_y_df, units, u_label, year)
        sanok_fig = make_storage_fig(results_df, cfg.sanok_name, magazyny_y_df, units, u_label, year)
        wierzchowice_fig = make_storage_fig(results_df, cfg.wierzchowice_name, magazyny_y_df, units, u_label, year)
        kosakowo_fig = make_storage_fig(results_df, cfg.kosakowo_name, magazyny_y_df, units, u_label, year)
        mogilno_fig = make_storage_fig(results_df, cfg.mogilno_name, magazyny_y_df, units, u_label, year)
        damaslawek_fig = make_storage_fig(results_df, cfg.damaslawek_name, magazyny_y_df, units, u_label, year)
        print('done calculating opt storage')

        return storage_op_fig, sanok_fig, wierzchowice_fig, kosakowo_fig, mogilno_fig, damaslawek_fig
    else:
        raise PreventUpdate


def make_storage_fig(results_df, title, magazyny_y_df, units, u_label, year):
    print('start make_storage_fig:', title)

    residual = results_df[title + cfg.residual_suffix] / units
    pp = results_df[title + cfg.pp_suffix] / units
    SoC = results_df[title + cfg.SoC_suffix] / units

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Scatter(x=results_df.index, y=residual, mode='lines', name='Zap. do magazynów'), row=1, col=1)
    fig.add_trace(go.Scatter(x=results_df.index, y=pp, mode='lines', name='Punkty pracy'), row=1, col=1)
    fig.add_trace(go.Scatter(x=results_df.index, y=SoC, mode='lines', name='Stan naładowania'), row=2, col=1)

    fig.add_hline(y=magazyny_y_df.loc[title, cfg.moc_odb_col] / units, name='moc odbioru i zatłaczania', line_width=1,
                  line_dash="dash", line_color="white", row=1, col=1, showlegend=True)
    fig.add_hline(y=magazyny_y_df.loc[title, cfg.moc_zatl_col] * -1 / units, line_width=1, line_dash="dash",
                  line_color="white", row=1, col=1)
    fig.add_hline(y=magazyny_y_df.loc[title, cfg.pojemnosc_col] / units, name='pojemność', line_width=1,
                  line_dash="dash", line_color="white", row=2, col=1, showlegend=True)

    if title in cfg.mag_calc_order:
        fig.add_hline(y=magazyny_y_df.loc[title, cfg.pojemnosc_col] / units * load_rezerwy_data().loc[year, title],
                      name='pojemność', line_width=1, line_dash="dash", line_color="white", row=2, col=1,
                      showlegend=True)

    fig.update_layout(main_layout)
    fig.update_layout(title={'text': title})

    fig.update_yaxes(title_text=u_label + '/h', row=1, col=1)
    fig.update_yaxes(title_text=u_label, row=2, col=1)
    fig.update_yaxes(range=[0, magazyny_y_df.loc[title, cfg.pojemnosc_col] / units + 1], row=2, col=1)

    return fig


@app.callback(
    Output('output-container', 'children'),
    Input("podaz-popyt-figure", 'relayoutData'),
    Input('year-df-datatable', 'data'),
    Input('units-selector', 'value'),
    State('units-selector', 'options'),
)
def annotate_plot(relayoutData, year_dt, units, opt):
    if relayoutData is None or 'xaxis.range[0]' not in relayoutData:
        return "Zaznacz okres by pokazać wyniki"

    year_df = pd.DataFrame(year_dt)
    used_cols = [cfg.scen_1_name, 'zap. bez e.e.MWh/h']
    year_df.loc[:, used_cols] = year_df.loc[:, used_cols] / units
    u_label = [x['label'] for x in opt if x['value'] == units][0]

    # Get the current x-axis range
    start_x, end_x = relayoutData['xaxis.range[0]'], relayoutData['xaxis.range[1]']
    # Filter the DataFrame based on the x-axis range
    filtered_df = year_df[(year_df[cfg.datetime_col_name] >= start_x) & (year_df[cfg.datetime_col_name] <= end_x)]

    # Calculate the sum of the values in the filtered DataFrame
    total_sum = filtered_df[used_cols].sum().sum()
    sum_bez_ee = filtered_df[used_cols].sum()['zap. bez e.e.MWh/h']
    sum_ee = filtered_df[used_cols].sum()[cfg.scen_1_name]

    return html.Div([
        f"Dla okresu od {pd.to_datetime(start_x).date()} do {pd.to_datetime(end_x).date()} zapotrzebowanie wynosi",
        html.Br(),
        f"zapotrzebowanie całkowite: {int(total_sum)} {u_label},",
        html.Br(),
        f"z czego bez e.e.: {int(sum_bez_ee)} {u_label},",
        html.Br(),
        f"sama e.e.: {int(sum_ee)} {u_label}"
    ])


@app.callback(
    Output('output-resid-container', 'children'),
    Input("residual-figure", 'relayoutData'),
    Input('residual-calculation', 'data'),
    Input('units-selector', 'value'),
    State('units-selector', 'options'),
)
def annotate_residual(relayoutData, residual_dt, units, opt):
    if relayoutData is None or 'xaxis.range[0]' not in relayoutData:
        return "Zaznacz okres by pokazać wyniki"

    residual_series = pd.DataFrame(residual_dt)
    residual_series.loc[:, cfg.demand_name] = residual_series.loc[:, cfg.demand_name] / units
    u_label = [x['label'] for x in opt if x['value'] == units][0]

    # Get the current x-axis range
    start_x, end_x = relayoutData['xaxis.range[0]'], relayoutData['xaxis.range[1]']
    # Filter the DataFrame based on the x-axis range
    filtered_df = residual_series[
        (residual_series[cfg.datetime_col_name] >= start_x) & (residual_series[cfg.datetime_col_name] <= end_x)]

    # Calculate the sum of the values in the filtered DataFrame
    total_sum = filtered_df.loc[:, cfg.demand_name].sum()

    return html.Div([
        f"Dla okresu od {pd.to_datetime(start_x).date()} do {pd.to_datetime(end_x).date()} zapotrzebowanie wynosi: {int(total_sum)} {u_label}",
    ])