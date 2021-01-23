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
import time
import numpy as np

from .components import base_map

app = Flask(__name__)
# Configurations
ALOWED_CORS_DOMAIN = 'http://localhost:8080'

@app.route('/<heatmap>/<fire>/<focus>', methods=(['GET']))
def home(heatmap, fire, focus):
    # plot figure
    fig = base_map.create_base_map()
    fig = base_map.add_public_transport(fig)

    if heatmap == "map":
        fig = base_map.draw_polygon(fig, "not", "not")
    elif heatmap == "heatmap":
        fig = base_map.draw_heatmap(fig, fire, focus)

    # remove logo and toolbar
    fig.toolbar.logo = None
    fig.toolbar_location = None
    
    callback = CustomJS(args=dict(plot = fig), code="""
        sessionStorage.setItem('xstart', plot.x_range.start);
        sessionStorage.setItem('xend', plot.x_range.end);
        sessionStorage.setItem('ystart', plot.y_range.start);
        sessionStorage.setItem('yend', plot.y_range.end);
        console.log(sessionStorage);
    """)

    fig.x_range.js_on_change('start', callback)
    fig.y_range.js_on_change('start', callback)

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
    fig = base_map.draw_building_radius(fig, building, fire)
    fig = base_map.add_public_transport(fig)
    fig = base_map.draw_polygon(fig, float(pand_id), fire)
    fig, stations = base_map.draw_blocked_ov(fig, building, fire)
    fig, roads = base_map.draw_blocked_roads(fig, building, fire)

    # remove logo and toolbar
    fig.toolbar.logo = None
    fig.toolbar_location = None

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # render template
    script, div = components(fig)

    # get information to show on html
    building_functions, neighbor_functions, radius_info, amount_neighbors, amount_radius, complete_adress = base_map.get_info(pand_id, fire)

    link_small = ("/building/" + pand_id + "/small")
    link_big = ("/building/" + pand_id + "/big")
    
    if fire == "small":
        # UI
        small_active = "active"
        big_active = str()
        # score
        risk_score_default = round(building.norm_score_small_default.values[0], 2)
        risk_score_residential = round(building.norm_score_small_residential.values[0], 2)
        risk_score_road = round(building.norm_score_small_road.values[0], 2)
    else:
        # UI
        big_active = "active"
        small_active = str()
        # score
        risk_score_default = round(building.norm_score_big_default.values[0], 2)
        risk_score_residential = round(building.norm_score_big_residential.values[0], 2)
        risk_score_road = round(building.norm_score_big_road.values[0], 2)

    # give the full address of the building back
    building_address = building['full_adress'].values[0]
    if pd.isnull(building_address):
        print("this building has no adress")
        address = "Address unkown"
    else:
        address = str(building_address.replace("\n", "<br>"))
    
    print("done with loading building")

    # return html template and contents
    return render_template(
        'building.html',
        id=str(pand_id),
        link_small = link_small,
        link_big = link_big,
        small_active = small_active,
        big_active = big_active,
        adress = address,
        building_info = building_functions,
        neighbor_info = neighbor_functions,
        radius_info = radius_info,
        amount_adjacent = amount_neighbors,
        amount_radius = amount_radius,
        radius_adress=complete_adress,
        risk_score_default = risk_score_default,
        risk_score_residential = risk_score_residential,
        risk_score_road = risk_score_road,
        stations = stations,
        roads = roads,
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources
    )

@app.route('/FAQ', methods=(['GET']))
def FAQ():
    return render_template(
        'export.html'
    )


def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = ALOWED_CORS_DOMAIN
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers

    return response


# app.after_request(add_cors_headers)

if __name__ == '__main__':
    app.run()
