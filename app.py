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
    fig = base_map.draw_polygon(fig, "not", "not")

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

@app.route('/building/<pand_id>/<fire>', methods=(['GET']))
def get_information(pand_id, fire):
    df       = pd.read_csv('./data/city_area_buildings.csv')

    building    = df[df['pand_id'] == float(pand_id)]
    coordinates = literal_eval(building.iloc[0]['wgs'])

    # plot figure
    fig = base_map.create_zoomed_map(coordinates)
    fig = base_map.add_public_transport(fig)
    fig = base_map.draw_polygon(fig, float(pand_id), fire)
    fig = base_map.draw_building_radius(fig, building, fire)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # render template
    script, div = components(fig)

    # get information to show on html
    building_functions, neighbor_functions, radius_info = base_map.get_info(pand_id, fire)

    link_small = ("http://127.0.0.1:5000/building/" + pand_id + "/small")
    link_big = ("http://127.0.0.1:5000/building/" + pand_id + "/big")

    risk_scores = pd.read_csv('./data/risk_scores.csv')
    
    if fire == "small":
        small_active = "active"
        big_active = str()
        risk_score = risk_scores[risk_scores['pand_id'] == float(pand_id)]['risk_score_small'].values[0]
    else:
        big_active = "active"
        small_active = str()
        risk_score = risk_scores[risk_scores['pand_id'] == float(pand_id)]['risk_score_big'].values[0]


    return render_template(
        'building.html',
        id=str(pand_id),
        link_small = link_small,
        link_big = link_big,
        small_active = small_active,
        big_active = big_active,
        adress = str(building['full_adress'].values[0].replace("\n", "<br>")),
        building_info = building_functions,
        neighbor_info = neighbor_functions,
        radius_info = radius_info,
        risk_score = risk_score,
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

@app.route('/heatmap/<fire>', methods=(['GET']))
def heatmap(fire):
    fig = base_map.create_base_map()
    fig = base_map.draw_heatmap(fig, fire)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # # render template
    script, div = components(fig)

    link_small = ("http://127.0.0.1:5000/heatmap/small")
    link_big = ("http://127.0.0.1:5000/heatmap/big")

    return render_template(
        'heatmap.html',
        plot_script=script,
        plot_div=div,
        link_small = link_small,
        link_big = link_big,
        js_resources=js_resources,
        css_resources=css_resources
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
