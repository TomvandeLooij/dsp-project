import pandas as pd
import numpy as np
import pyclipper
from pyproj import Transformer, transform
from ast import literal_eval
from collections import Counter, OrderedDict
import colorcet as cc

# import bokeh modules
from bokeh.plotting import figure, show
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models.callbacks import CustomJS
from bokeh.models import ColumnDataSource, TapTool, CustomJS, HoverTool, Line, MultiLine, LinearColorMapper, BasicTicker, ColorBar

# reverse color map
cc.fire.reverse()

TRAN_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

def create_base_map():
    """Create base map to show all information on, map of Amsterdam"""

    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=(543910.459905604, 549882.1261916904), y_range=(6863397.16441418, 6867925.895324006),
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=800, plot_height=550,
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

    # create zoomed in figure
    fig = figure(x_range=x_range, y_range=y_range,
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=800, plot_height=550,
                 tools="pan,wheel_zoom,reset", active_scroll='wheel_zoom')

    fig.add_tile(tile_provider)

    return fig


def convert(test):
    """Convert string of coordinates to list of list (inner list is xy coordinates) and transforms them"""
    test  = test.replace('"', '')
    test2 = test.split(',')

    test3 = [x.split(' ') for x in test2]

    final = []
    for coord in test3:
        # only keep coordinates if not equal to ""
        if len(coord)>2:
            coord = [c for c in coord if c != ""]

        # transform coordinates to be able to be plotted on map
        transformed_coord = TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1]))
        final.append([transformed_coord[0], transformed_coord[1]])

    return final

def add_public_transport(fig):
    """"Draw all of the public transport lines and stations. Also creates hover function so """

    # put data about lines into frame and put to the rigth dtype
    df = pd.read_csv("./data/tram_metro_lijnen.csv")
    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(convert)

    # plot every line
    for i in df.itertuples():
        coordsx = []
        coordsy = []

        for coord in i.WKT_LAT_LNG:
            coordsx.append(coord[0])
            coordsy.append(coord[1])
        
        # put line information in the right format
        lijn = i.Lijn.replace(" ", '').split("|")
        
        if len(lijn) == 1:
            lijn = lijn[0]
        else: 
            lijn = ", ".join(lijn)
            k    = lijn.rfind(", ")
            lijn = lijn[:k] + " and " + lijn[k+1:]

        modaliteit = [i.Modaliteit] * len(coordsx)
        lijn       = [lijn] * len(coordsx)
        
        source = ColumnDataSource(data={"coordsx":coordsx, "coordsy":coordsy, "modality":modaliteit, "lijn":lijn})

        # add lines to plot
        if modaliteit[0] == "Tram":
            fig.line("coordsx", "coordsy", line_color="blue", line_width=2.5, alpha=0.8, name="ov", source=source, legend_label="Tram")
        elif modaliteit[0] == "Metro":
            fig.line("coordsx", "coordsy", line_color="green", line_width=2.5, alpha=0.8, name="ov", source=source, legend_label="Metro")

    # create hover tool for the lines
    fig.add_tools(HoverTool(
        names = ['ov'],
        tooltips = [
            ("line", "@modality @lijn ")
        ]
    ))

    # put data about stations into the frame and put columns in right dtype
    df = pd.read_csv('./data/TRAMMETRO_PUNTEN_2020.csv', error_bad_lines=False, encoding="utf-8", delimiter=";")
    
    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(lambda x: x.replace("POINT(", "").replace(")", ""))
    
    # plot every station
    for i in df.itertuples():
        coords            = i.WKT_LAT_LNG.split(",")
        transformed_coord = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))
        coordsx           = [transformed_coord[0]]
        coordsy           = [transformed_coord[1]]
        modaliteit        = [i.Modaliteit]
        
        lijn = i.Lijn.replace(" ", '').split("|")
        lijn = ", ".join(lijn)
        k    = lijn.rfind(", ")
        lijn = lijn[:k] + " and" + lijn[k+1:]

        lijn     = [lijn]
        stations = [i.Naam]

        source = ColumnDataSource(data={"coordsx":coordsx, "coordsy":coordsy, "modality":modaliteit, "lijn":lijn, "station":stations})

        # add stations to plot
        fig.circle("coordsx", "coordsy", alpha=0.8, name="stations", color="black", size=5, source=source)
    
    # create hover tool for stations
    fig.add_tools(HoverTool(
        names = ['stations'],
        tooltips = [
            ("station", "@station"),
            ("line", "@modality @lijn")
        ]
    ))

    return fig
