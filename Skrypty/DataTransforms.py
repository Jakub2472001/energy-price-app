import pandas as pd
import numpy as np
import config as cfg
from Main import app
from dash import html, Input, Output,dash_table, State
from LoadData import joined_demand, load_magazyny_df
from SimulateStorage import run_simulation_złożowy, run_simulation_kawerna



def run_all_years_sim(popyt_ccgt_scen_name, imp_winter_off, podaz_df, zrodla_podazy, storage_investment_scenario):
    print('start run_all_years_sim')

    years = np.arange(cfg.start_year, cfg.end_year+1)

    yearly_summarry_df = pd.DataFrame(columns = ['dostarczony gaz z magazynów', 'niedostarczony gaz z magazynów', 'zapotrzebowanie na moc w magazynach', 'maksymalna moc magazynów'], index=years, dtype=np.float32)
    all_gas_demands = {}
    storage_results_dict = {}
    percent_full = 0.86
    all_year_dfs = {}
    magazyny_dict, profil_dict = load_magazyny_df(path=storage_investment_scenario)
    for y in years:
        magazyny_df = magazyny_dict[y].copy()

        residual, year_df, _= calc_resid_no_callback(podaz_df, popyt_ccgt_scen_name, imp_winter_off, y, zrodla_podazy)
        storage_operation, storage_SoC, all_SoC, all_pp, all_residual = calc_year_sim(residual, magazyny_df,profil_dict, percent_full, y)

        storage_results_dict[y] = pd.concat([all_SoC,all_pp, all_residual], axis=1)
        storage_results_dict[y].loc[:, 'rok'] = storage_results_dict[y].index.year
        storage_results_dict[y].loc[:, 'Magazyny łącznie' + cfg.residual_suffix] = residual.loc[:, cfg.demand_name]
        storage_results_dict[y].loc[:, 'Magazyny łącznie' + cfg.SoC_suffix] = storage_SoC
        storage_results_dict[y].loc[:, 'Magazyny łącznie' + cfg.pp_suffix] = storage_operation

        gas_demand = np.float32(residual[residual[cfg.demand_name] >0][cfg.demand_name].sum())
        gas_delivered = np.float32(storage_operation[storage_operation >0].sum())
        print(y, 'gas demand: ', gas_demand, 'gas_delivered: ', gas_delivered)#, 'percent covered: ',gas_delivered / gas_demand)
        yearly_summarry_df.loc[y, 'dostarczony gaz z magazynów'] = gas_delivered
        yearly_summarry_df.loc[y, 'niedostarczony gaz z magazynów'] = gas_demand - gas_delivered
        yearly_summarry_df.loc[y, 'zapotrzebowanie na moc w magazynach'] = np.float32(residual[cfg.demand_name].max())

        mag_moc = magazyny_df[cfg.moc_odb_col].sum()
        mag_pojemnosć =  magazyny_df['pojemność'].sum()
        yearly_summarry_df.loc[y, 'maksymalna moc magazynów'] =np.float32(mag_moc)

        all_gas_demands[y] = residual[residual[cfg.demand_name] >0][cfg.demand_name]


        min_SoC = storage_SoC.min()
        max_SoC = storage_SoC.max()

        yearly_summarry_df.loc[y, 'min SoC %'] = (min_SoC / mag_pojemnosć).round(2).values[0]
        yearly_summarry_df.loc[y, 'max SoC %'] = (max_SoC / mag_pojemnosć).round(2).values[0]

        yearly_summarry_df.loc[y, 'min SoC MWh'] = min_SoC.round(2).values[0]
        yearly_summarry_df.loc[y, 'max SoC MWh'] = max_SoC.round(2).values[0]

        percent_full = storage_SoC.iloc[-1] / mag_pojemnosć
        all_year_dfs[y] = year_df

    all_year_dfs_parsed = pd.concat(all_year_dfs, axis=0).reset_index(names = ['rok_auto', cfg.datetime_col_name +'_auto'])
    return yearly_summarry_df, all_gas_demands, pd.concat(storage_results_dict, axis=0).reset_index(names=['rok_auto', cfg.datetime_col_name]), all_year_dfs_parsed

def calc_year_sim(residual, magazyny_df, profil_dict, percent_full, year):
    print('start calc_year_sim')
    residual = pd.Series(residual.set_index(cfg.datetime_col_name)[cfg.demand_name])
    all_SoC = {}
    all_pp = {}
    all_residual = {}
    residual_after_calc = residual.copy()

    for name in cfg.mag_calc_order:
        mag = magazyny_df.loc[name]
        if name in cfg.złożowy_names:
            SoC, pp = run_simulation_złożowy(residual_after_calc, mag[cfg.pojemnosc_col], mag[cfg.moc_zatl_col],
                                             mag[cfg.moc_odb_col], percent_full, name,profil_dict, year)

        elif name in cfg.kawerna_names:
            SoC, pp = run_simulation_kawerna(residual_after_calc,  mag[cfg.pojemnosc_col], mag[cfg.moc_zatl_col],
                                             mag[cfg.moc_odb_col], percent_full, name,profil_dict, year)
        else:
            raise Exception("Name not foung in mag list or type not defined", name)

        all_SoC[name + cfg.SoC_suffix] = SoC
        all_pp[name + cfg.pp_suffix] = pp
        residual_after_calc -= pp
        if name == cfg.mag_calc_order[0]:
            all_residual[name + cfg.residual_suffix] = residual
        else:
            all_residual[name + cfg.residual_suffix] = residual_after_calc+pp

    storage_operation = pd.DataFrame(all_pp).sum(axis=1)
    storage_SoC = pd.DataFrame(all_SoC).sum(axis=1)

    return storage_operation, pd.DataFrame(storage_SoC), pd.DataFrame(all_SoC), pd.DataFrame(all_pp), pd.DataFrame(all_residual)



@app.callback(
Output('residual-calculation', 'data'),
Output('year-df-datatable', 'data'),
Output('datatable-podaz', 'data'),
Input(component_id='year_slider', component_property='value'),
Input(component_id='datatable-podaz', component_property='data'),
Input(component_id='scenario-selector', component_property='value'),
Input(component_id='import-selector', component_property='value'),
Input(component_id='źródła-selector', component_property='value'),

)
def calculate_residual_y(year, my_podaz_table, selected_scen, imp_winter, values):
    print('start calculate_residual_y')

    residual, year_df, podaz_df = calc_resid_no_callback(my_podaz_table,selected_scen, imp_winter, year, values)

    print('done calculating residual')

    return residual.to_dict('records'), year_df.to_dict('records'), podaz_df.reset_index(names='źródło').to_dict('records')

def calc_resid_no_callback(my_podaz_table, selected_scen, imp_winter, year, values):
    print('start calc_resid_no_callback')

    podaz_df = pd.DataFrame(my_podaz_table).set_index('źródło').loc[values,:]
    mask = (podaz_df['od'].astype(int) <= int(year)) & (podaz_df['do'].astype(int) >= int(year))
    summer_sources = podaz_df[mask].index
    if imp_winter == False and len(cfg.winter_off_sources)>0:
        winter_sources = podaz_df[mask].drop(cfg.winter_off_sources, axis=0).index
    else:
        winter_sources =summer_sources

    summer_moc_podazy = podaz_df.loc[summer_sources,:][cfg.base_unit].astype(int).sum()
    winter_moc_podazy = podaz_df.loc[winter_sources,:][cfg.base_unit].astype(int).sum()

    year_df = joined_demand[joined_demand['Rok'] == year].reset_index(names = cfg.datetime_col_name)
    year_df.loc[:, cfg.datetime_col_name] = pd.to_datetime(year_df.loc[:, cfg.datetime_col_name])

    base_podaz_hourly = pd.DataFrame(index = year_df[cfg.datetime_col_name], dtype=float)
    base_podaz_hourly.loc[:, 'month'] = base_podaz_hourly.index.month
    zatł_mask = base_podaz_hourly['month'].isin(cfg.zatł_months)
    odb_mask = base_podaz_hourly['month'].isin(cfg.odb_months)

    base_podaz_hourly[zatł_mask] = summer_moc_podazy
    base_podaz_hourly[odb_mask] = winter_moc_podazy

    #chosen_demand = ['cfg.przemysl_name, cfg.dystrybucja_name, cfg.ec_name,' selected_scen]
    chosen_demand = ['zap. bez e.e.MWh/h', selected_scen]
    base_popyt_hourly = pd.DataFrame(year_df.set_index(cfg.datetime_col_name)[chosen_demand].sum(axis=1), columns = ['value'])
    residual = (base_podaz_hourly.rename({'month':'value'}, axis=1) - base_popyt_hourly)*-1
    print('coś nie tak z indeksami - napraw to bo teraz przekazujesz values')
    year_df.loc[:,'suma podaży'] = base_podaz_hourly.values
    residual.loc[:, cfg.datetime_col_name] = year_df[cfg.datetime_col_name].values
    residual.columns = [cfg.demand_name, cfg.datetime_col_name]
    return residual, year_df, podaz_df

@app.callback(
Output('datatable-magazyny', 'data'),
Input(component_id='units-selector', component_property='value'),
State(component_id='units-selector', component_property='options'),
Input(component_id='year_slider', component_property='value'),
Input(component_id='storage-investment-scenario', component_property='value'))
def define_magazyny_table(units, opt, y, storage_investment_scenario):
    print('start define_magazyny_table')
    u_label = [x['label'] for x in opt if x['value'] == units][0]
    print(storage_investment_scenario)

    df,_ = load_magazyny_df(path=storage_investment_scenario)
    df = df[y]
    df = (df/units).round(2)
    #df.columns = [c+u_label for c in df.columns]
    df=df.reset_index(names = ['nazwa'])
    df = df.to_dict('records')
    print('done define_magazyny_table')
    return df


def define_podaz_table(df):
    print('start define_podaz_table')

    # Define the DataTable with styling
    podaz_table =html.Div([dash_table.DataTable(
        id='datatable-podaz',
        columns=[{'name': i, 'id': i, 'deletable': True} for i in
                 df[['źródło', cfg.base_unit, cfg.day_unit, 'od', 'do']].columns],
        data=df.to_dict('records'),
        editable=True,
        #filter_action="native",
        sort_action="native",
        sort_mode='multi',
        #row_selectable='multi',
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
    print('done define_podaz_table')
    return podaz_table

