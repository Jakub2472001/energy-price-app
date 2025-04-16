import os


data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Data'))

winter_off_sources = ['DE (Mallnow, Lasów)', 'CZ (Cieszyn)']
#winter_off_sources = []

zrodla_podazowe_dostepnosc = 0.95

sanok_name = 'GIM Sanok'
wierzchowice_name = 'IM Wierzchowice'
mogilno_name = 'KPMG Mogilno'
kosakowo_name = 'KPMG Kosakowo'
damaslawek_name = 'KPMG Damasławek'
mag_calc_order = [sanok_name, wierzchowice_name, kosakowo_name, mogilno_name, damaslawek_name]

scen_1_name = 'CCGT scen. energetyka +'
scen_2_name = 'CCGT scen. bazowy'
scen_3_name = 'CCGT scen. 20 GW'

przemysl_name = 'Przemysł'
dystrybucja_name = 'Dystrybucja'
ec_name = 'EC i ciepłownie'

demand_name = 'Zapotrzebowanie do magazynów'
m3_to_kWh = 11.6
kWh_to_m3 = 1/m3_to_kWh
srednia_sprawnosc_el_ec_gazowych = 0.5

start_year = 2025
end_year = 2040

# base_year = 2040

pp_suffix = ' punkty pracy'
SoC_suffix = ' stan naładowania'
residual_suffix = ' zapotrzebowanie dla magazynu'

base_unit = 'MWh/h'
day_unit = 'mln m3/24h'
datetime_col_name = 'data i godzina'

paper_bgcolor = "#1e1e1e"
plot_bgcolor = "#1e1e1e"
backgroundColor="#2b2b2b"

moc_zatl_col = 'moc-zatłaczanie'
moc_odb_col = 'moc-odbiór'
pojemnosc_col = 'pojemność'

złożowy_name = 'złożowy'
złożowy_names = [sanok_name, wierzchowice_name]

kawerna_name = 'kawerna'
kawerna_names = [mogilno_name, kosakowo_name, damaslawek_name]

datetime_format_dash = '%Y-%m-%dT%H:%M:%S'

zatł_months = [4,5,6,7,8,9]
odb_months = [1,2,3,10,11,12]



# tab:blue : #1f77b4
# tab:orange : #ff7f0e
# tab:green : #2ca02c
# tab:red : #d62728
# tab:purple : #9467bd
# tab:brown : #8c564b
# tab:pink : #e377c2
# tab:gray : #7f7f7f
# tab:olive : #bcbd22
# tab:cyan : #17becf
