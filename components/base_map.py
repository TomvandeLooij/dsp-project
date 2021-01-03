import pandas as pd
import numpy as np
import pyclipper

from bokeh.plotting import figure, show
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models.callbacks import CustomJS
from bokeh.models import ColumnDataSource, TapTool, CustomJS, HoverTool, Line, MultiLine

from ast import literal_eval

from pyproj import Transformer, transform

TRAN_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

def create_base_map():
    """Create base map to show all information on, map of Amsterdam"""

    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=(530683.95, 555576.10), y_range=(6854570.54, 6876203.35),
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=900, plot_height=600,
                 tools="pan,wheel_zoom,reset", active_scroll='wheel_zoom')

    fig.add_tile(tile_provider)

    return fig

def create_zoomed_map(coordinates):
    """Makes the map zoom in on the selected building"""

    y_coord = coordinates[0][0]
    x_coord = coordinates[0][1]

    point1 = TRAN_4326_TO_3857.transform(y_coord - 0.0004, x_coord - 0.002)
    point2 = TRAN_4326_TO_3857.transform(y_coord + 0.0004, x_coord + 0.002)

    x_range = (point1[0], point2[0])
    y_range = (point1[1], point2[1])

    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=x_range, y_range=y_range,
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=900, plot_height=600,
                 tools="pan,wheel_zoom,reset", active_scroll='wheel_zoom')

    fig.add_tile(tile_provider)

    return fig

def draw_building_radius(fig, building):
    """Draws a radius around a building to show blockage by the fire department"""

    # radius in meters/kilometers
    radius = 25/100000

    # get coordintes and transforms them to be usable for the map
    coordinates = literal_eval(building.iloc[0]['wgs'])

    # calculate coordinates of radius around the building (on original coordinates not transformed)
    clipper_offset     = pyclipper.PyclipperOffset()
    coordinates_scaled = pyclipper.scale_to_clipper(coordinates)

    clipper_offset.AddPath(coordinates_scaled, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    new_coordinates    = clipper_offset.Execute(pyclipper.scale_to_clipper(radius))
    scaled_coordinates = pyclipper.scale_from_clipper(new_coordinates)
    scaled_coordinates = [TRAN_4326_TO_3857.transform(coord[0], coord[1]) for coord in scaled_coordinates[0]]

    # get x and y coordinates of radius
    x_coords_scaled = [c[1] for c in scaled_coordinates]
    y_coords_scaled = [c[0] for c in scaled_coordinates]

    # draw radius on map
    fig.patch(y_coords_scaled, x_coords_scaled, line_width=5, alpha = 0.2, color="red")

    return fig


def convert(test):
    """Convert string of coordinates to list of list (inner list is xy coordinates) and transforms them"""

    test = test.replace('"', '')
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

        for j in range(0, len(coords), 1):
            lijstx.append(coords[j][0])
            lijsty.append(coords[j][1])

        fig.line(lijstx, lijsty, line_color="coral", line_width=2, alpha=0.8)
    df = pd.read_csv('./data/TramMetroStations.csv', error_bad_lines=False, encoding="utf-8", delimiter=";")
    print(df.columns)

    df['WKT_stations'] = df['WKT_stations'].apply(convert)
    for i in range(len(df)):
        coords = df.iloc[i]['WKT_stations']
        # list with x-coordinates     
        lijstx = []
        # list with y-coordinates
        lijsty = []

        for j in range(0, len(coords), 1):
            lijstx.append(coords[j][0])
            lijsty.append(coords[j][1])
        fig.circle(lijstx, lijsty, alpha=0.8) 
        if df.iloc[i]['Modaliteit'] == 'Metro':
            fig.line(lijstx, lijsty, line_color="blue", line_width=2, alpha=0.8)
        else:
            fig.line(lijstx, lijsty, line_color="green", line_width=2, alpha=0.8)
    return fig

def draw_polygon(fig):
    """"Draws all polygons given in the dataset and makes them clickable"""

    # load data about buildings
    df = pd.read_csv("./data/final_csv_for_buildings.csv")

    x_coords = []
    y_coords = []

    # split coordinates to x and y coordinates
    for i in range(len(df)):
        coords = df.iloc[i]['wgs']
        coords = literal_eval(coords)
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df['pand_id']), 'functie':list(df['gebruiksdoelVerblijfsobject'])}

    # set source for polygons
    s1 = ColumnDataSource(data=data)

    # all buildings to be plotted on map
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
    fig.add_tools(tap)

    # create hovertool
    fig.add_tools(HoverTool(
        renderers=[glyph],
        tooltips=[
            # use @{ } for field names with spaces
            ( 'id'              , '@id'),
            ( 'gebruiksfunctie' , '@functie')
        ],
        formatters = {
            'id'        : 'printf',
            'functie'   : 'printf'
        }
    ))

    return fig
