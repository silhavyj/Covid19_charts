#!/bin/python3

from urllib.request import urlopen
import dash_html_components as html
import dash_core_components as dcc
from dash_html_components.Br import Br
from dash_html_components.Link import Link
import plotly.graph_objects as go
from configparser import RawConfigParser
import statistics
import dash
import json
import math
from datetime import datetime

CONFIG_FILE = 'config.ini'

parser = RawConfigParser()
parser.read(CONFIG_FILE)

BIND_IP                 = parser['network']['bind_ip']
BIND_PORT               = parser['network']['bind_port']
RAW_JSON_DATA_URL       = parser['network']['data_url']
SOURCE_CODE_URL         = parser['network']['source_code_url']

DAYS_BACK               = int(parser['general']['days_back'])
NORM_POPULATION         = int(parser['general']['norm_population'])
CUMULATIVE_DAYS         = int(parser['general']['cumulative_days'])
DEFAULT_COLOR           = parser['general']['default_color']

DEFAULT_COUNTRY         = parser['countries']['default']
COUNTRIES_IN_LINE_CHART = parser['countries']['list'].split(',')

time_now = datetime.now()
dt_string = time_now.strftime("%d/%m/%Y %H:%M")
countries = {}

class bcolors:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'

class Country:
    def __init__(self, shortcut, name, population, daily_cases, vaccination, dates):
        self.shortcut    = shortcut
        self.name        = name
        self.population  = population
        self.daily_cases = daily_cases
        self.dates       = dates
        self.vaccination = self.normalizeVaccination(vaccination, population)
        self.cumulative  = self.get_cumulative(days=CUMULATIVE_DAYS, dates=self.dates, daily_cases=self.daily_cases, population=self.population)
        self.progress    = self.get_progress(self.cumulative, days=CUMULATIVE_DAYS)
        self.cumulative_sum = sum(self.cumulative)

    def normalizeVaccination(self, data, population):
        vaccination = []
        prev_val = 0
        for val in data:
            prev_val = prev_val + (val * NORM_POPULATION) / population
            vaccination.append(prev_val)
        return vaccination
    
    def get_cumulative(self, days, dates, daily_cases, population):
        cumulative = []
        for i in range(days, len(dates)):
            current_day = 0
            for j in range(i, i - days, -1):
                current_day = current_day + daily_cases[j]
            current_day = (current_day * NORM_POPULATION) / population
            cumulative.append(current_day)
        return cumulative

    def get_progress(self, cumulative, days):
        values = []
        for i in range(0, days):
            if cumulative[-i-2] == 0:
                values.append(math.inf)
                continue
            progress = (100 * cumulative[-i-1]) / cumulative[-i-2]

            if progress < 100:
                progress = 100 - progress
            elif progress > 100:
                progress = -(progress - 100)

            values.append(progress)
        return statistics.median(values)
            

print("downloading data...")
json_data = urlopen(RAW_JSON_DATA_URL).read().decode('utf-8')
loaded_json = json.loads(json_data)
print(bcolors.OKGREEN + '[+] ' + bcolors.ENDC + 'data successfully downloaded')

print('starting processing countries...')
for country in loaded_json:
    full_name = loaded_json[country]['location']
    if 'population' in loaded_json[country]:
        population = loaded_json[country]['population']
        if population == 0:
            print(bcolors.WARNING + "[!] " + bcolors.ENDC + "country '{0}' has 0 population!".format(full_name))
            continue
    else:
        print(bcolors.WARNING + "[!] " + bcolors.ENDC + "country '{0}' doesn't have a population!".format(full_name))
        continue

    daily_cases = []
    dates = []
    vaccination = []

    for record in loaded_json[country]['data']:
        if 'new_cases' in record:
            daily_cases.append(record['new_cases'])
        else:
            daily_cases.append(0)
        date_parts = record['date'].split('-')
        dates.append(date_parts[2] + '.' + date_parts[1] + '.')

        if 'new_vaccinations' in record:
            vaccination.append(record['new_vaccinations'])
        else:
            vaccination.append(0)

    try:
        country_ins = Country(shortcut=country,
                          name=full_name,
                          population=population,
                          daily_cases=daily_cases,
                          vaccination=vaccination,
                          dates=dates)
    except:
        print(bcolors.FAIL + "[-] " + bcolors.ENDC + "error occurred while processing '{0}'".format(full_name))
        continue
    countries[country] = country_ins

print(bcolors.OKGREEN + '[+] ' + bcolors.ENDC + 'processing countries finished')
predefined_colors = {}
for color_key in parser['countries_colors']:
    color_key = color_key.upper()
    predefined_colors[countries[color_key].name] = parser['countries_colors'][color_key]

def show_bar_chart(x_data, y_data, title, colors):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_data, y=y_data, marker_color=colors))
    fig.update_layout(
    title=title,
    xaxis_tickfont_size=12,
    yaxis=dict(
        titlefont_size=14,
        tickfont_size=12,
    ),
    legend=dict(
        x=0,
        y=1.0,
        bgcolor='rgba(255, 255, 255, 0)',
        bordercolor='rgba(255, 255, 255, 0)'
    ),
    barmode='group',
    bargap=0.15,
    bargroupgap=0.1
    )
    return fig

def show_daily_cases_of_country(shortcut):
    colors = []
    for i in range(0, len(countries[shortcut].dates)):
        colors.append(DEFAULT_COLOR)
    
    return show_bar_chart(x_data=countries[shortcut].dates[-DAYS_BACK:],
                          y_data=countries[shortcut].daily_cases[-DAYS_BACK:],
                          title='Daily New Cases - ' + countries[shortcut].name,
                          colors=colors)

def show_current_cumulative_number():
    data = {}
    for key in COUNTRIES_IN_LINE_CHART:
        data[countries[key].name] = countries[key].cumulative[-1]

    countries_names = []
    last_cumulative_num = []
    colors = []

    for w in sorted(data, key=data.get, reverse=True):
        countries_names.append(w)
        last_cumulative_num.append(round(data[w], 2))

        if w in predefined_colors:
            colors.append(predefined_colors[w])
        else:
            colors.append(DEFAULT_COLOR)
    
    return show_bar_chart(x_data=countries_names,
                          y_data=last_cumulative_num,
                          title = str(CUMULATIVE_DAYS) + '-day Cumulative Number of Cases per ' + str(NORM_POPULATION),
                          colors=colors)

def show_line_chart():
    fig = go.Figure()

    fig.update_layout(
        title = str(CUMULATIVE_DAYS) + '-day Cumulative Number of Cases per ' + str(NORM_POPULATION),
    )

    for country in COUNTRIES_IN_LINE_CHART:
        x_data = countries[country].dates[-DAYS_BACK:]
        y_data = countries[country].cumulative[-DAYS_BACK:]
        name   = countries[country].name

        fig.add_trace(go.Scatter(x=x_data, y=y_data,
                                 mode='lines+markers',
                                 name=name))
    return fig

def show_vaccination_line_chart():
    fig = go.Figure()

    fig.update_layout(
        title = 'Number of Vaccinations Carried Out per ' + str(NORM_POPULATION),
    )

    for country in COUNTRIES_IN_LINE_CHART:
        x_data = countries[country].dates[-DAYS_BACK:]
        y_data = countries[country].vaccination[-DAYS_BACK:]
        name   = countries[country].name

        fig.add_trace(go.Scatter(x=x_data, y=y_data,
                                 mode='lines+markers',
                                 name=name))
    return fig

def show_progress_bar_char():
    data = {}
    for key in COUNTRIES_IN_LINE_CHART:
        data[countries[key].name] = countries[key].progress

    countries_names = []
    progress_value = []
    colors = []

    for w in sorted(data, key=data.get, reverse=True):
        countries_names.append(w)
        progress_value.append(round(data[w], 2))
        if progress_value[-1] < 0:
            colors.append('rgb(255, 0, 0)')
        else:
             colors.append('rgb(0, 153, 0)')
    
    return show_bar_chart(x_data=countries_names,
                          y_data=progress_value,
                          title='Progress of Individual Countries Within the Last ' + str(CUMULATIVE_DAYS) + ' days [%]',
                          colors=colors)

def show_total_sum():
    data = {}
    for key in COUNTRIES_IN_LINE_CHART:
        data[countries[key].name] = countries[key].cumulative_sum

    countries_names = []
    cumulative_sum = []
    colors = []

    for w in sorted(data, key=data.get, reverse=True):
        countries_names.append(w)
        cumulative_sum.append(round(data[w], 2))

        if w in predefined_colors:
            colors.append(predefined_colors[w])
        else:
            colors.append(DEFAULT_COLOR)
    
    return show_bar_chart(x_data=countries_names,
                          y_data=cumulative_sum,
                          title = 'Total Sum of Cumulative Number of Cases per ' + str(NORM_POPULATION),
                          colors=colors)

app = dash.Dash(__name__)

def create_charts():
    app.layout = html.Div(style={
        'width'                  : '80%',
        'margin'                 : 'auto'
    }, children=[
        html.H1(children='Covid19-related data', style={
			'text-align'         : 'center',
			'color'              : 'rgb(55, 83, 109)'
        }),
        html.H3(children='updated: ' + dt_string, style={
			'text-align'         : 'center',
			'color'              : 'rgb(55, 83, 109)'
        }),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '50px',
            'margin-bottom'      : '30px'
        }, children=[
            dcc.Graph(
                figure=show_progress_bar_char()
            )
        ]),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '30px',
            'margin-bottom'      : '50px',
        }, children=[
            dcc.Dropdown(id='dropdown', options=[{'label':countries[country].name, 'value':country} for country in COUNTRIES_IN_LINE_CHART], value = DEFAULT_COUNTRY),
            html.Div(id='graph-court', children=[
                dcc.Graph(
                    figure=show_daily_cases_of_country(DEFAULT_COUNTRY)
                )
            ])
        ]),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '30px',
            'margin-bottom'      : '30px'
        }, children=[
            dcc.Graph(
                figure=show_current_cumulative_number()
            )
        ]),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '30px',
            'margin-bottom'      : '30px'
        }, children=[
            dcc.Graph(
                figure=show_total_sum()
            )
        ]),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '50px',
            'margin-bottom'      : '50px'
        }, children=[
            dcc.Graph(
                figure=show_line_chart()
            )
        ]),
        html.Div(style={
            'width'              : '100%',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '50px',
            'margin-bottom'      : '50px'
        }, children=[
            dcc.Graph(
                figure=show_vaccination_line_chart()
            )
        ]),
        html.Div(style={
            'width'              : '100%',
            'text-align'         : 'center',
            '-webkit-box-shadow' : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            '-moz-box-shadow'    : '0px 0px 25px 1px rgba(0,0,0,0.15)',
            'box-shadow'         : '0px 0px 25px 1px rgba(0,0,0,0.15)', 
            'margin-top'         : '30px',
            'margin-bottom'      : '50px',
        }, children=[
            html.A('Navigate to source code', href=SOURCE_CODE_URL, target='_blank', style={
			    'text-align'         : 'center',
			    'color'              : 'rgb(55, 83, 109)',
                'margin-bottom'      : '10px'
            }),
            html.Br(),
            html.A('Navigate to raw JSON data', href=RAW_JSON_DATA_URL, target='_blank', style={
			    'text-align'         : 'center',
			    'color'              : 'rgb(55, 83, 109)'
            })
        ])
    ])
    app.run_server(debug=True, host=BIND_IP, port=BIND_PORT)

@app.callback(
dash.dependencies.Output('graph-court', 'children'),
[dash.dependencies.Input('dropdown', 'value')])
def update_output(value):
    return dcc.Graph(figure=show_daily_cases_of_country(value))

create_charts()