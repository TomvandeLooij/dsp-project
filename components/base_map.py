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
        if len(coord)>2:
            coord = [c for c in coord if c != ""]
        transformed_coord = TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1]))
        final.append([transformed_coord[0], transformed_coord[1]])

    return final

def add_public_transport(fig):
    # add lines to plot
    df = pd.read_csv("./data/tram_metro_lijnen.csv")
    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(convert)

    for i in df.itertuples():
        coordsx = []
        coordsy = []
        for coord in i.WKT_LAT_LNG:
            coordsx.append(coord[0])
            coordsy.append(coord[1])

        modaliteit = [i.Modaliteit] * len(coordsx)
        lijn = [i.Lijn] * len(coordsx)
        
        source = ColumnDataSource(data={"coordsx":coordsx, "coordsy":coordsy, "modality":modaliteit, "lijn":lijn})

        if modaliteit[0] == "Tram":
            fig.line("coordsx", "coordsy", line_color="blue", line_width=2.5, alpha=0.8, name="ov", source=source, legend_label="Tram")
        elif modaliteit[0] == "Metro":
            fig.line("coordsx", "coordsy", line_color="green", line_width=2.5, alpha=0.8, name="ov", source=source, legend_label="Metro")

    fig.add_tools(HoverTool(
        names=['ov'],
        tooltips=[
            ("line", "@lijn @modality")
        ]
    ))

    # add stations to plot
    df = pd.read_csv('./data/TRAMMETRO_PUNTEN_2020.csv', error_bad_lines=False, encoding="utf-8", delimiter=";")

    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(lambda x: x.replace("POINT(", "").replace(")", ""))
    
    for i in df.itertuples():
        coords = i.WKT_LAT_LNG.split(",")
        transformed_coord = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))
        coordsx = [transformed_coord[0]]
        coordsy = [transformed_coord[1]]
        modaliteit = [i.Modaliteit]
        lijn = [i.Lijn]
        stations = [i.Naam]

        source = ColumnDataSource(data={"coordsx":coordsx, "coordsy":coordsy, "modality":modaliteit, "lijn":lijn, "station":stations})

        fig.circle("coordsx", "coordsy", alpha=0.8, name="stations", color="black", size=5, source=source)
    
    fig.add_tools(HoverTool(
        names=['stations'],
        tooltips=[
            ("station", "@station"),
            ("line", "@lijn @modality")
        ]
    ))

    return fig

def draw_polygon(fig, building, fire):
    """"Draws all polygons given in the dataset and makes them clickable"""

    # load data about buildings
    fields = ['pand_id', 'wgs', 'full_adress']

    df = pd.read_csv("./data/city_area_buildings.csv")

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
        glyph_2 = fig.multi_polygons(xs='ys', ys='xs', color="red", name="pand", source=s2, alpha=0.5)

    x_coords = []
    y_coords = []

    # time save use apply function instead of looping 4 seconds just for this part
    # split coordinates to x and y coordinates
    df["wgs"] = df['wgs'].apply(lambda x:literal_eval(x))
    df['full_adress'] = df["full_adress"].apply(str)
    
    for i in df.itertuples():
        coords = i.wgs
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df["pand_id"]),  'full_adress':list(df['full_adress']), 
            'functions':list(df['gebruiksdoelVerblijfsobject'])}

    # print(data['full_adress'])
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

def draw_heatmap(fig, fire):
    """"Draws all polygons given in the dataset and makes them clickable"""

    # load data about buildings
    fields = ['pand_id', 'wgs', 'full_adress']

    df = pd.read_csv("./data/city_area_buildings.csv")
    risk_scores = pd.read_csv('./data/risk_scores.csv')

    x_coords = []
    y_coords = []

    # time save use apply function instead of looping 4 seconds just for this part
    # split coordinates to x and y coordinates
    df["wgs"] = df['wgs'].apply(lambda x:literal_eval(x))
    
    for i in range(len(df)):
        coords = df.iloc[i]['wgs']
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    if fire == 'small':
        scores            = risk_scores['risk_score_small']
        scores_normalized = risk_scores['small_normalized']
    else:
        scores            = risk_scores['risk_score_big']
        scores_normalized = risk_scores['big_normalized']

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df["pand_id"]), 'alpha': list(scores_normalized + 0.1), 'score':list(scores)}

    # set source for polygons
    s1 = ColumnDataSource(data=data)

    # all buildings to be plotted on map
    glyph = fig.multi_polygons(xs='ys', ys='xs', color="red", name="pand", source = s1, alpha='alpha')
    
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

    fig.add_tools(HoverTool(
        renderers=[glyph],
        tooltips=[
            ("score", "@score")
        ]
    ))

    return fig

def draw_blocked_ov(building, fig, fire):
    ov = pd.read_csv("./data/tram en metro lijnen plus stations.csv")

    # to show everyting red there are missing pieces in some lines...
    # ov["lijn_coordinaten"] = ov.lijn_coordinaten.apply(convert)

    # for i in ov.itertuples():
    #     coordsx = []
    #     coordsy = []
    #     for coord in i.lijn_coordinaten:
    #         coordsx.append(coord[0])
    #         coordsy.append(coord[1])

    #     fig.line(coordsx, coordsy, color="red")

    if fire == "big":
        numbers = building.ov_big.values[0]
        if numbers == "[]":
            return fig
        
        df = ov[ov.number.isin(literal_eval(numbers))]
        print(df)
    elif fire == "small":
        numbers = building.ov_small.values[0]
        if numbers == "[]":
            return fig
        
        df = ov[ov.number.isin(literal_eval(numbers))]
        print(df)

    df['lijn_coordinaten'] = df.lijn_coordinaten.apply(convert)
    
    blokkage = {}

    for i in df.itertuples():
        coordsx = []
        coordsy = []
        for coord in i.lijn_coordinaten:
            coordsx.append(coord[0])
            coordsy.append(coord[1])
        
        fig.line(coordsx, coordsy, line_color="red", line_width=2.5, alpha=1)

        # station 1
        coords = i.coords_s1.split(" ")
        transformed_coords = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))

        fig.circle(transformed_coords[0], transformed_coords[1], color="red", size=6)

        # station 2
        coords = i.coords_s2.split(" ")
        transformed_coords = TRAN_4326_TO_3857.transform(float(coords[0]), float(coords[1]))

        fig.circle(transformed_coords[0], transformed_coords[1], color="red", size=6)

        # give stations back
        stations = str(i.station1) + " - " + str(i.station2)

        # give lines back
        blokkage[stations] = str(i.modaliteit) + " " + str(i.lijn)

    return fig, blokkage

def get_info(building, fire):
    df = pd.read_csv("./data/city_area_buildings.csv", usecols=["pand_id", "gebruiksdoelVerblijfsobject", "neighbors", "linked_small", "linked_big"])
    
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
        column = "linked_small"
    elif fire == "big":
        column = "linked_big"

    linked_buildings = list(df[df.pand_id.isin(literal_eval(df_building[column].values[0]))].gebruiksdoelVerblijfsobject)
    linked_functions = [item for lijst in linked_buildings for item in literal_eval(lijst)]
    linked_functions = Counter(linked_functions)

    return dict(functions), dict(neighbor_functions), dict(linked_functions)