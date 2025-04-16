import numpy as np
import pandas as pd
import config as cfg

from LoadData import rezerwy_df


def read_efficiency(SoC, max_capacity, profil_sub_df):
    if max_capacity >0:
        eff = profil_sub_df.loc[round(SoC / max_capacity*100, -1)/100]
    else:
        eff=0
    return eff

def run_simulation_kawerna(residual, max_capacity, charging_power, discharging_power, percent_full, name, profil_dict, year):
    SoC = np.zeros(len(residual))
    SoC[0] = max_capacity * percent_full
    charging = np.zeros(len(residual))
    discharging = np.zeros(len(residual))
    power_profile = np.zeros(len(residual))

    # Iterate over hourly demand
    for t in range(len(residual)):
        ch_plus=0
        ch_minus=0
        idx = min(1, t) # condition for time t = 0, otherwise 1
        # Charging / Zatłaczanie
        if residual.iloc[t] < 0:
            ch_plus = np.min([max_capacity - SoC[t-idx], np.min([residual.iloc[t]*-1, charging_power * read_efficiency(SoC[t-idx], max_capacity, profil_dict[name]['zatłaczanie'])])])
            if SoC[t-idx] + ch_plus > max_capacity:
                ch_plus = max_capacity - SoC[t-idx]
            charging[t] = ch_plus
            power_profile[t] = ch_plus

        # Discharging / odbiór
        if residual.iloc[t] > 0 and SoC[t-idx] > max_capacity*rezerwy_df.loc[year, name]:
            ch_minus = np.max([0,np.min([SoC[t-idx], np.min([residual.iloc[t], discharging_power * read_efficiency(SoC[t-idx], max_capacity, profil_dict[name]['odbiór'])])])])
            if SoC[t-idx] - ch_minus < max_capacity*rezerwy_df.loc[year, name]:
                ch_minus = SoC[t-idx] - max_capacity*rezerwy_df.loc[year, name]

            discharging[t] = ch_minus*-1
            power_profile[t] = ch_minus*-1

        SoC[t] = SoC[t - idx] + ch_plus - ch_minus
    power_profile=pd.Series(power_profile, index=residual.index, name=cfg.demand_name)
    SoC=pd.Series(SoC, index=residual.index, name='SoC')

    return SoC, power_profile*-1

def run_simulation_złożowy(residual, max_capacity, charging_power, discharging_power, percent_full, name, profil_dict, year):
    SoC = np.zeros(len(residual))
    SoC[0] = max_capacity* percent_full
    charging = np.zeros(len(residual))
    discharging = np.zeros(len(residual))
    power_profile = np.zeros(len(residual))

    # Iterate over hourly demand
    for t in range(len(residual)):

        month = residual.index[t].month
        ch_plus_current = 0
        ch_minus_current = 0
        # Loading
        idx = min(1, t)
        if residual.iloc[t] < 0 and month in cfg.zatł_months:
            ch_plus_current = np.min([max_capacity - SoC[t-idx], np.min([residual.iloc[t]*-1, charging_power * read_efficiency(SoC[t-idx], max_capacity, profil_dict[name]['zatłaczanie'])])])

            if SoC[t-idx] + ch_plus_current > max_capacity:
                ch_plus_current = max_capacity - SoC[t-idx]

            charging[t] = ch_plus_current
            power_profile[t] = ch_plus_current

        # Unloading
        if residual.iloc[t]>0 and month in cfg.odb_months and SoC[t-idx] > max_capacity*rezerwy_df.loc[year, name]:
            ch_minus_current = np.max([0,np.min([SoC[t-idx], np.min([residual.iloc[t], discharging_power * read_efficiency(SoC[t-idx], max_capacity, profil_dict[name]['odbiór'])])])])

            if SoC[t-idx] - ch_minus_current < max_capacity*rezerwy_df.loc[year, name]:
                ch_minus_current = SoC[t-idx] - max_capacity*rezerwy_df.loc[year, name]

            discharging[t] = ch_minus_current*-1
            power_profile[t] = ch_minus_current*-1


        SoC[t] = SoC[t - idx] + ch_plus_current - ch_minus_current

    power_profile=pd.Series(power_profile, index=residual.index, name=cfg.demand_name)
    return SoC, power_profile*-1
