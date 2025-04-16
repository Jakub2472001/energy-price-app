
from dash import Dash
import dash_bootstrap_components as dbc

# Initialize the Dash app with Bootstrap stylesheet
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
