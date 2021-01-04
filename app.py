# app.py
from flask import Flask, render_template, request, json
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.models.callbacks import CustomJS
from bokeh.models import TapTool, ColumnDataSource
from bokeh.models.tools import TapTool
from bokeh.plotting import figure, curdoc
from bokeh.layouts import column

import pandas as pd
from ast import literal_eval

from .components import base_map

app = Flask(__name__)
# Configurations
ALOWED_CORS_DOMAIN = 'http://localhost:8080'

@app.route('/', methods=(['GET']))
def home():
    fig = base_map.create_base_map()
    fig = base_map.add_public_transport(fig)
    fig = base_map.add_emergency_routes(fig)
    fig = base_map.draw_polygon(fig)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # # render template
    script, div = components(fig)

    return render_template(
        'index.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources
        )

@app.route('/building/<pand_id>', methods=(['GET']))
def get_information(pand_id):
    df       = pd.read_csv('./data/test.csv')

    building    = df[df['pand_id'] == float(pand_id)]
    coordinates = literal_eval(building.iloc[0]['WGS'])

    fig = base_map.create_zoomed_map(coordinates)
    fig = base_map.add_public_transport(fig)
    fig = base_map.add_emergency_routes(fig)
    fig = base_map.draw_polygon(fig)
    fig = base_map.draw_building_radius(fig, building)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # # render template
    script, div = components(fig)

    return render_template(
        'building.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources
    )

@app.route('/export', methods=(['GET']))
def export():
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    return render_template(
        'export.html',
        js_resources = js_resources,
        css_resources = css_resources,
        plot_script = None
    )


def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = ALOWED_CORS_DOMAIN
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers

    return response


app.after_request(add_cors_headers)

if __name__ == '__main__':
    app.run()
