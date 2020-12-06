# app.py
from flask import Flask, render_template, request
from jinja2 import Template

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.tile_providers import get_provider, Vendors

app = Flask(__name__)
# Configurations
ALOWED_CORS_DOMAIN = 'http://localhost:8080'


@app.route('/', methods=(['GET']))
def home():
    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=(515919.90, 642740.25), y_range=(6095766.77, 6212052.13),
           x_axis_type="mercator", y_axis_type="mercator", plot_width=1000, plot_height=600)


    fig.add_tile(tile_provider)

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
        css_resources=css_resources)

@app.route('/export', methods=(['GET']))
def export():
    return 'Export!'


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
