import pandas as pd
import numpy as np
import pyclipper

from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models.callbacks import CustomJS
from bokeh.models import ColumnDataSource, TapTool, CustomJS

from ast import literal_eval

from pyproj import Transformer, transform

TRAN_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

def create_base_map():
    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=(530683.95, 555576.10), y_range=(6854570.54, 6876203.35),
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=1000, plot_height=600,
                 tools="pan,wheel_zoom,reset")

    fig.add_tile(tile_provider)

    return fig

def create_zoomed_map(coordinates):
    y_coord = coordinates[0][0]
    x_coord = coordinates[0][1]

    point1 = TRAN_4326_TO_3857.transform(y_coord - 0.0004, x_coord - 0.002)
    point2 = TRAN_4326_TO_3857.transform(y_coord + 0.0004, x_coord + 0.002)

    x_range = (point1[0], point2[0])
    y_range = (point1[1], point2[1])

    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=x_range, y_range=y_range,
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=1000, plot_height=600,
                 tools="pan,wheel_zoom,reset")

    fig.add_tile(tile_provider)

    return fig

def draw_building_radius(fig, building):
    coordinates = literal_eval(building.iloc[0]['WGS'])

    transformed_coordinates = [TRAN_4326_TO_3857.transform(coord[0], coord[1]) for coord in coordinates]
    
    x_coords = [c[1] for c in transformed_coordinates]
    y_coords = [c[0] for c in transformed_coordinates]

    clipper_offset     = pyclipper.PyclipperOffset()
    coordinates_scaled = pyclipper.scale_to_clipper(coordinates)

    clipper_offset.AddPath(coordinates_scaled, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    new_coordinates    = clipper_offset.Execute(pyclipper.scale_to_clipper(.00025))
    scaled_coordinates = pyclipper.scale_from_clipper(new_coordinates)
    scaled_coordinates = [TRAN_4326_TO_3857.transform(coord[0], coord[1]) for coord in scaled_coordinates[0]]

    x_coords_scaled = [c[1] for c in scaled_coordinates]
    y_coords_scaled = [c[0] for c in scaled_coordinates]

    fig.patch(y_coords_scaled, x_coords_scaled, line_width=5, alpha = 0.2, color="red")

    return fig


def convert(test):
    test2 = test.split(',')

    test3 = [x.split(' ') for x in test2]

    final = []
    for coord in test3:
        transformed_coord = TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1]))
        final.append([transformed_coord[0], transformed_coord[1]])

    return final

def add_public_transport(fig):
    df = pd.read_csv('./data/tram_metro_lijnen.csv')
    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(convert)

    for i in range(len(df)):
        coords = df.iloc[i]['WKT_LAT_LNG']
        # list with x-coordinates
        lijstx = []
        # list with y-coordinates
        lijsty = []

        for j in range(0, len(coords), 4):
            coord = coords[j]
            transformed_coord = TRAN_4326_TO_3857.transform(coord[0], coord[1])
            lijstx.append(transformed_coord[0])
            lijsty.append(transformed_coord[1])

        fig.line(lijstx, lijsty, line_color="coral", line_width=2, alpha=0.8)

    return fig

def draw_polygon(fig):
    # load data about buildings
    df = pd.read_csv("./data/test.csv")
    print(len(df))

    x_coords = []
    y_coords = []

    for i in range(len(df)):
        coords = df.iloc[i]['WGS']
        coords = literal_eval(coords)
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df['pand_id'])}
    names = list(df['pand_id'])

    s1 = ColumnDataSource(data=data)

    # name is id number of building, tags to identify type of glyph
    glyph = fig.multi_polygons(xs='ys', ys='xs', color="navy", name="pand", source=s1, alpha=0.3)

    # what happens in the call
    call = CustomJS(args=dict(source=s1), code="""
            /* console.log(cb_data.source.selected.indices[0]); */

            let idx = cb_data.source.selected.indices[0];
            let pand_id = source.data.id[idx];
            console.log(pand_id);

            /* here comes ajax callback*/
            window.location = ("http://127.0.0.1:5000/building/" + pand_id)
            """)

    # only make polygons clickable
    tap = TapTool(renderers=[glyph], callback=call)
    fig.tools.append(tap)

    return fig

