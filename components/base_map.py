import pandas as pd
import numpy as np
import pyclipper

from bokeh.plotting import figure, show
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models.callbacks import CustomJS
from bokeh.models import ColumnDataSource, TapTool, CustomJS, HoverTool, Line, MultiLine

from pyproj import Transformer, transform
from ast import literal_eval
from collections import Counter, OrderedDict

# can be deleted at the end
import time


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

def draw_building_radius(fig, building, fire):
    """Draws a radius around a building to show blockage by the fire department"""
    
    # radius in meters/kilometers based on fire size
    if fire == "small":
        radius = 10/100000
    elif fire == "big":
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

def draw_polygon(fig, building, fire):
    """"Draws all polygons given in the dataset and makes them clickable"""
    print(building)

    # load data about buildings
    fields = ['pand_id', 'wgs', 'full_adress']

    df = pd.read_csv("./data/final_csv_for_buildings.csv")

    # if a building is selected
    if building != "not":
        df_building = df[df.pand_id == float(building)]
        df = df[df.pand_id != building]
        
        x_coords = []
        y_coords = []

        # split coordinates to x and y coordinates
        for i in range(len(df_building)):
            coords = df_building.iloc[i]['wgs']
            coords = literal_eval(coords)
            coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
            x_coords.append([[[c[1] for c in coords]]])
            y_coords.append([[[c[0] for c in coords]]])
        
        data = {'xs': x_coords, 'ys': y_coords, 'id':list(df_building["pand_id"]),  'full_adress':list(df_building['full_adress'])}

        # # set source for polygons
        s2 = ColumnDataSource(data=data)

        # # all buildings to be plotted on map
        glyph_2 = fig.multi_polygons(xs='ys', ys='xs', color="red", name="pand", source=s2, alpha=1)

    x_coords = []
    y_coords = []

    start = time.time()
    print("time elapsed:", end="")

    # time save use apply function instead of looping 4 seconds just for this part
    # split coordinates to x and y coordinates
    for i in range(len(df)):
        coords = df.iloc[i]['wgs']
        coords = literal_eval(coords)
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])
    
    end = time.time()
    print(end - start)

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df["pand_id"]),  'full_adress':list(df['full_adress']), 
            'functions':list(df['gebruiksdoelVerblijfsobject'])}

    data['full_adress'] = [item.replace("\n", "<br>") for item in data['full_adress']]
    
    # set functions in proper form for hovertool
    all_functions = []
    for item in data["functions"]:
        item = dict(Counter(literal_eval(item)))
        string = str()
        for element in item:
            string = string + str(element) + " " + str(item[element]) + "<br>"
        all_functions.append(string)


    data['functions'] = all_functions

    # set source for polygons
    s1 = ColumnDataSource(data=data)

    # all buildings to be plotted on map
    glyph = fig.multi_polygons(xs='ys', ys='xs', color="navy", name="pand", source=s1, alpha=0.3)

    # what happens in the call
    call = CustomJS(args=dict(source=s1, fire=fire), code="""
            /* console.log(cb_data.source.selected.indices[0]); */

            let idx = cb_data.source.selected.indices[0];
            let pand_id = source.data.id[idx];
            console.log(pand_id);

            /* here comes ajax callback, default fire size is small*/
            if (fire == "not") {
                window.location = ("http://127.0.0.1:5000/building/" + pand_id + "/small")
            } else {
                window.location = ("http://127.0.0.1:5000/building/" + pand_id + "/" + fire)
            }
            """)

    # only make polygons clickable
    tap = TapTool(renderers=[glyph], callback=call)
    fig.add_tools(tap)

    # create hovertool
    fig.add_tools(HoverTool(
        renderers=[glyph],
        tooltips=
        # """
        # adress: <br> @full_adress{safe}
        # """,
        
        [
            # use @{ } for field names with spaces
            ( 'adress'          , '@full_adress{safe}'),
            ( 'functions',          '@functions{safe}')
        ],
        formatters = {
            'full_adress'    : 'printf',
            'functions'      : 'printf'
        }
    ))

    return fig

def get_info(building, fire):
    df = pd.read_csv("./data/final_csv_for_buildings.csv", usecols=["pand_id", "gebruiksdoelVerblijfsobject", "neighbors", "small_linked", "big_linked"])
    
    # get all functions from building
    df_building = df[df.pand_id == float(building)]
    functions_building = literal_eval(df_building.gebruiksdoelVerblijfsobject.values[0])
    functions = Counter(functions_building)
    
    # get neighbors functions
    df_neighbors = list(df[df.pand_id.isin(literal_eval(df_building.neighbors.values[0]))].gebruiksdoelVerblijfsobject)
    neighbor_functions = [item for lijst in df_neighbors for item in literal_eval(lijst)]
    neighbor_functions = Counter(neighbor_functions)

    # get linking for big or small fire
    if fire == "small":
        column = "small_linked"
    elif fire == "big":
        column = "big_linked"

    linked_buildings = list(df[df.pand_id.isin(literal_eval(df_building[column].values[0]))].gebruiksdoelVerblijfsobject)
    linked_functions = [item for lijst in linked_buildings for item in literal_eval(lijst)]
    linked_functions = Counter(linked_functions)

    return dict(functions), dict(neighbor_functions), dict(linked_functions)