import pandas as pd
import config as cfg
import os



data_folder_scenarios = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage_Scenarios'))

data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage'))

def get_available_files(data_folder):
    return [f for f in os.listdir(data_folder) if f.endswith('.xlsx')]

def get_file_path():
    data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane/Usage'))
    available_files = get_available_files(data_folder)

    if available_files:
        main_path = available_files[0]
        main_file_path = os.path.join(data_folder, main_path)
        #print(f"Wybrany plik: {main_file_path}")
        return main_file_path
    else:
        print("Brak dostępnych plików w folderze.")





def load_magazyny_df(path):
    mld_m3_to_MWh = 1e6 * cfg.m3_to_kWh
    conversion_dict= {
        cfg.pojemnosc_col : mld_m3_to_MWh,
        cfg.moc_zatl_col: 1/24*1e3,
        cfg.moc_odb_col: 1 / 24 * 1e3
    }
    full_path = os.path.join(data_folder_scenarios, path)
    magazyny_df = pd.read_excel(full_path, sheet_name=[cfg.pojemnosc_col, cfg.moc_zatl_col, cfg.moc_odb_col], index_col=0, header=0)
    yearly_magazyny_dict = {y:pd.DataFrame() for y in magazyny_df[next(iter(magazyny_df))].drop('jednostka', axis=1)}
    for key, df in magazyny_df.items():
        for year in df.drop('jednostka', axis=1).columns:
            yearly_magazyny_dict[year].loc[:, key] = df.loc[:, year]* conversion_dict[key]

    zatł_ciągły  = 'profil zatł. w trybie ciągłym'
    zatł_przeryw = 'profil zatł. w trybie przer.'
    odb_przeryw = 'profil odbioru w trybie przer.'
    odb_ciągły = 'profil odbioru w trybie ciągłym'

    profil_dict = pd.read_excel(full_path, sheet_name=[zatł_ciągły, zatł_przeryw, odb_przeryw, odb_ciągły], index_col=0, header=0)
    profile_mag_dict = {}
    profile_mag_dict[cfg.sanok_name] = {'odbiór':  profil_dict[odb_ciągły][cfg.sanok_name] , 'zatłaczanie':profil_dict[zatł_ciągły][cfg.sanok_name]}
    profile_mag_dict[cfg.wierzchowice_name] = {'odbiór': profil_dict[odb_ciągły][cfg.wierzchowice_name], 'zatłaczanie':profil_dict[zatł_ciągły][cfg.wierzchowice_name]}
    profile_mag_dict[cfg.mogilno_name] = {'odbiór': profil_dict[odb_przeryw][cfg.mogilno_name] , 'zatłaczanie':profil_dict[zatł_przeryw][cfg.mogilno_name] }
    profile_mag_dict[cfg.kosakowo_name] = {'odbiór': profil_dict[odb_przeryw][cfg.kosakowo_name], 'zatłaczanie':profil_dict[zatł_przeryw][cfg.kosakowo_name]}
    profile_mag_dict[cfg.damaslawek_name] = {'odbiór': profil_dict[odb_przeryw][cfg.damaslawek_name], 'zatłaczanie':profil_dict[zatł_przeryw][cfg.damaslawek_name]}

    return yearly_magazyny_dict, profile_mag_dict

def load_pse_data():
    #Przejdz z produkcji e.e. na jednostki zapotrzebowania na gaz
    #pse_df = pd.read_excel(main_file_path, index_col=0, parse_dates=True, sheet_name='Dane PSE')
    pse_df = pd.read_excel(get_file_path(), index_col=0, parse_dates=True, sheet_name='Dane PSE')
    pse_df.index = pd.to_datetime(pse_df.index)
    pse_df.loc[:, 'Rok'] = pse_df.index.year


    pse_df.loc[:,cfg.scen_1_name] = pse_df.loc[:,cfg.scen_1_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    pse_df.loc[:,cfg.scen_2_name] = pse_df.loc[:,cfg.scen_2_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    pse_df.loc[:,cfg.scen_3_name] = pse_df.loc[:,cfg.scen_3_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    return pse_df

def load_rezerwy_data():
    #rezerwy_df = pd.read_excel(main_file_path, index_col=0,  sheet_name='zapas obowiązkowy').T
    rezerwy_df = pd.read_excel(get_file_path(), index_col=0,  sheet_name='zapas obowiązkowy').T
    rezerwy_df.reset_index(inplace=True)  # TODO: (4)!
    return rezerwy_df

def load_new_zap_data():
    #new_popyt_ts = pd.read_excel(main_file_path, index_col=0,  header=0, parse_dates=True, sheet_name='Dane')
    new_popyt_ts = pd.read_excel(get_file_path(), index_col=0,  header=0, parse_dates=True, sheet_name='Dane')
    new_popyt_ts_long = new_popyt_ts.reset_index(names='dt').melt(var_name='rok', value_name='mln m3', id_vars='dt')
    new_popyt_ts_long['rok'] = new_popyt_ts_long['rok'].astype(int)  # Ensure 'rok' is integer
    new_popyt_ts_long['dt'] = new_popyt_ts_long.apply(lambda row: row['dt'].replace(year=row['rok']), axis=1)
    new_popyt_ts_long = new_popyt_ts_long.drop('rok', axis =1)
    # Zmień z mln m3/h na MWh/h
    new_popyt_ts_long.loc[:, 'MWh/h'] = new_popyt_ts_long['mln m3'] *cfg.m3_to_kWh*1e3
    new_popyt_ts_long.columns = ['dt','zap. bez e.e. mln m3', 'zap. bez e.e.MWh/h' ]

    return new_popyt_ts_long

def join_data():
    print(f"Wywołanie: join_data()")
    pse_df = load_pse_data()
    new_popyt_ts_long = load_new_zap_data()

    calk_zap_merged = pse_df

    calk_zap_merged_new = calk_zap_merged.merge(new_popyt_ts_long, left_index=True, right_on='dt', how='right').set_index('dt')

    calk_zap_merged_new.reset_index(inplace=True) #TODO: (3)
    return calk_zap_merged_new

def load_podaz_df():
    print(f"Wywołanie: load_podaz_df()")
    #podaz_df = pd.read_excel(main_file_path, index_col=0, header=0, sheet_name='Źródła podaży')
    podaz_df = pd.read_excel(get_file_path(), index_col=0, header=0, sheet_name='Źródła podaży')
    podaz_df.loc[:, 'MWh/h'] = (podaz_df['mln m3 na dobę'] / 24 * cfg.m3_to_kWh *1e3).round(0)
    podaz_df =podaz_df.rename({'mln m3 na dobę' : 'mln m3/24h'}, axis=1)
    podaz_df.loc[:, ['mln m3/24h', 'MWh/h']] = podaz_df.loc[:, ['mln m3/24h', 'MWh/h']]  * cfg.zrodla_podazowe_dostepnosc
    podaz_df.loc['Źródła krajowe', ['mln m3/24h', 'MWh/h']] = podaz_df.loc['Źródła krajowe', ['mln m3/24h', 'MWh/h']] / cfg.zrodla_podazowe_dostepnosc
    podaz_df = podaz_df.drop(index=["UA", "SK (Vyrawa)"], errors='ignore')

    return podaz_df.reset_index(names='źródło')

def get_max_demand(df):
    max_demand = df.loc[:, [cfg.scen_1_name, 'zap. bez e.e.MWh/h']].sum(axis=1).max()
    return max_demand