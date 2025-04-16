import matplotlib.pyplot as plt
from LoadData import load_pse_data
import config as cfg
plt.style.use('ggplot')
pse_df = load_pse_data()

def plot_ts(df, year):

    fig, axes = plt.subplots()
    df_y = df[df['Rok'] == year]
    axes.plot(df_y[cfg.war_1_name], label = 'prognoza PSE', color = 'gold')
    axes.set_title('Zap PSE Wariant 1 (EL+EC)')
    axes.set_ylabel('Zapotrzebowanie na gaz [MWh]')
    axes.set_xlabel('data i godzina')
    axes.axhline(457000, linestyle = '--', label = 'baza', color= 'k')
    axes.legend()

plot_ts(pse_df, 2035)
plt.show()