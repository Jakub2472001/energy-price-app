import pandas as pd
import config as cfg
import os


data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Dane'))

main_path = "2025_04_15_Model pracy PMG_założenia.xlsx"
main_file_path = os.path.join(data_folder, main_path)

nowy_popyt_path = "Zapotrzebowanie godzinowe dystrybucja, przemysł, ciepłownictwo 15_04_2025.xlsx"
nowy_popyt_file_path = os.path.join(data_folder, nowy_popyt_path)


def load_magazyny_df(path):
    mld_m3_to_MWh = 1e6 * cfg.m3_to_kWh
    conversion_dict= {
        cfg.pojemnosc_col : mld_m3_to_MWh,
        cfg.moc_zatl_col: 1/24*1e3,
        cfg.moc_odb_col: 1 / 24 * 1e3
    }
    full_path = os.path.join(data_folder, path)
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
    pse_df = pd.read_excel(main_file_path, index_col=0, parse_dates=True, sheet_name='Dane PSE')
    pse_df.index = pd.to_datetime(pse_df.index)
    pse_df.loc[:, 'Rok'] = pse_df.index.year


    pse_df.loc[:,cfg.scen_1_name] = pse_df.loc[:,cfg.scen_1_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    pse_df.loc[:,cfg.scen_2_name] = pse_df.loc[:,cfg.scen_2_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    pse_df.loc[:,cfg.scen_3_name] = pse_df.loc[:,cfg.scen_3_name]/ cfg.srednia_sprawnosc_el_ec_gazowych
    return pse_df

def load_rezerwy_data():
    rezerwy_df = pd.read_excel(main_file_path, index_col=0,  sheet_name='zapas obowiązkowy').T
    return rezerwy_df

def load_dystr_przem_data():
    popyt_df = pd.read_excel(main_file_path, index_col=0,  sheet_name='Strona popytowa').T
    # Zmień z mld m3/rok na MWh/h
    popyt_df = popyt_df *cfg.m3_to_kWh*1e6/8760
    return popyt_df

def load_new_zap_data():

    new_popyt_ts = pd.read_excel(nowy_popyt_file_path, index_col=0,  header=0, parse_dates=True)
    new_popyt_ts_long = new_popyt_ts.reset_index(names='dt').melt(var_name='rok', value_name='mln m3', id_vars='dt')
    new_popyt_ts_long['rok'] = new_popyt_ts_long['rok'].astype(int)  # Ensure 'rok' is integer
    new_popyt_ts_long['dt'] = new_popyt_ts_long.apply(lambda row: row['dt'].replace(year=row['rok']), axis=1)
    new_popyt_ts_long = new_popyt_ts_long.drop('rok', axis =1)
    # Zmień z mln m3/h na MWh/h
    new_popyt_ts_long.loc[:, 'MWh/h'] = new_popyt_ts_long['mln m3'] *cfg.m3_to_kWh*1e3
    new_popyt_ts_long.columns = ['dt','zap. bez e.e. mln m3', 'zap. bez e.e.MWh/h' ]

    return new_popyt_ts_long

def join_data():
    popyt_df = load_dystr_przem_data()
    sezon_df = pd.read_excel(main_file_path, sheet_name='Profil sezonowy')
    sezon_df = sezon_df.reset_index(names='miesiąc int')
    sezon_df = sezon_df.drop('miesiąc',axis=1)
    sezon_df.loc[:,'miesiąc int'] = sezon_df.loc[:,'miesiąc int'] +1
    sezon_long = pd.melt(sezon_df, id_vars='miesiąc int', value_name='procent zap', var_name='Rok')


    pse_df = load_pse_data()
    calk_zap = pd.merge(pse_df, popyt_df, left_on='Rok', right_index=True)
    calk_zap.loc[:, 'miesiąc int'] = calk_zap.index.month
    new_popyt_ts_long = load_new_zap_data()

    calk_zap_merged = pd.merge(calk_zap, sezon_long, left_on=['Rok', 'miesiąc int'],  right_on=['Rok', 'miesiąc int'])

    calk_zap_merged.loc[:,cfg.dystrybucja_name] = calk_zap_merged.loc[:, cfg.dystrybucja_name]*  calk_zap_merged.loc[:, 'procent zap']
    calk_zap_merged.loc[:, cfg.przemysl_name] = calk_zap_merged.loc[:, cfg.przemysl_name]*  calk_zap_merged.loc[:, 'procent zap']
    calk_zap_merged.loc[:, cfg.ec_name] = calk_zap_merged.loc[:, cfg.ec_name]*  calk_zap_merged.loc[:, 'procent zap']
    calk_zap_merged = calk_zap_merged.set_index(calk_zap.index)
    calk_zap_merged_new = calk_zap_merged.merge(new_popyt_ts_long, left_index=True, right_on='dt', how='right').set_index('dt')
    #calk_zap_merged_new.loc[:, 'zap. bez e.e.MWh/h'] = calk_zap_merged_new.loc[:, 'zap. bez e.e.MWh/h'] *0
    return calk_zap_merged_new

def load_podaz_df():
    podaz_df = pd.read_excel(main_file_path, index_col=0, header=0, sheet_name='Źródła podaży')
    podaz_df.loc[:, 'MWh/h'] = (podaz_df['mln m3 na dobę'] / 24 * cfg.m3_to_kWh *1e3).round(0)
    podaz_df =podaz_df.rename({'mln m3 na dobę' : 'mln m3/24h'}, axis=1)
    podaz_df.loc[:, ['mln m3/24h', 'MWh/h']] = podaz_df.loc[:, ['mln m3/24h', 'MWh/h']]  * cfg.zrodla_podazowe_dostepnosc
    podaz_df.loc['Źródła krajowe', ['mln m3/24h', 'MWh/h']] = podaz_df.loc['Źródła krajowe', ['mln m3/24h', 'MWh/h']] / cfg.zrodla_podazowe_dostepnosc
    return podaz_df.reset_index(names='źródło')

joined_demand = join_data()
podaz_df = load_podaz_df()
rezerwy_df = load_rezerwy_data()
max_demand = joined_demand.loc[:, [cfg.scen_1_name, 'zap. bez e.e.MWh/h']].sum(axis=1).max()

