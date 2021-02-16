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

def draw_blocked_ov(fig, building, fire):
    """Draws blocked public transport on top of other transport. Eliminates for extra hover tool."""

    # load data
    ov = pd.read_csv("./data/tram en metro lijnen plus stations.csv")
    
    # get blocked ov id's based on fire size
    if fire == "big":
        numbers = building.ov_big.values[0]
    elif fire == "small":
        numbers = building.ov_small.values[0]

    # if nothing blocked return
    if numbers == "[]":
        return fig, {"No blokked public transport.":""}

    # transform list to string    
    df = ov[ov.number.isin(literal_eval(numbers))]
    df['lijn_coordinaten'] = df.lijn_coordinaten.apply(convert)
    
    # go through every line with its corresponding stations
    blokkage = {}
    for i in df.itertuples():
        coordsx = []
        coordsy = []
        for coord in i.lijn_coordinaten:
            coordsx.append(coord[0])
            coordsy.append(coord[1])

        # draw the lines that are blocked
        fig.line(coordsx, coordsy, line_color="red", line_width=2.5, alpha=1, legend_label="Blocked public transport")

        # station 1
        coords = i.coords_s1.split(" ")
        transformed_coords = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))

        # draw station that is blocked
        fig.circle(transformed_coords[0], transformed_coords[1], color="red", size=6)

        # station 2
        coords = i.coords_s2.split(" ")
        transformed_coords = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))

        # draw station 2 blocked
        fig.circle(transformed_coords[0], transformed_coords[1], color="red", size=6)

        # give stations back
        stations = str(i.station1) + " - " + str(i.station2)

        # give lines back
        blokkage[stations] = str(i.modaliteit) + " " + str(i.lijn)

    return fig, blokkage

def draw_blocked_roads(fig, building, fire):
    """Draw all blocked roads"""

    # load data
    df = pd.read_csv("./data/all_roads_amsterdam.csv")

    # select road ids based on fire size
    if fire == "small":
        road_ids = literal_eval(building.roads_small.values[0])
    elif fire == "big":
        road_ids = literal_eval(building.roads_big.values[0])

    # if nothing is blocked return
    if len(road_ids) == 0:
        return fig, {"No blocked roads.":""}

    # put data in right format
    df_roads                = df[df.number.isin(road_ids)]
    df_roads['WKT_LAT_LNG'] = df.WKT_LAT_LNG.apply(convert)

    blocked_roads = {}
    for i in df_roads.itertuples():
        coordsx = []
        coordsy = []
        for coord in i.WKT_LAT_LNG:
            coordsx.append(coord[0])
            coordsy.append(coord[1])

        # select information about blocked roads
        names = [i.STT_NAAM] * len(coordsx)
        if i.AUTO == "calamiteit":
            types = ["calamiteiten route"] * len(coordsx)
            blocked_roads[i.STT_NAAM] = "calamiteiten route"
        elif i.AUTO == "hoofd":
            types = ["hoofdnet route"] * len(coordsx)
            blocked_roads[i.STT_NAAM] = "hoofdnet route"
        elif i.AUTO == "plus":
            types = ["plusnet route"] * len(coordsx)
            blocked_roads[i.STT_NAAM] = "plusnet route"

        source = ColumnDataSource(data={"coordsx":coordsx, "coordsy":coordsy, "name":names, "type":types})

        # add blocked line to figure
        fig.line('coordsx', 'coordsy', line_color="black", source=source, line_width=3, alpha=1, legend_label="Blocked roads", name="road")

    # add hover tool map
    fig.add_tools(HoverTool(
        names = ['road'],
        tooltips = [
            ("Road", "@name"),
            ("Type", "@type")
        ]
    ))
    
    return fig, blocked_roads
