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

def draw_polygon(fig, building, fire):
    """"Draws all polygons given in the dataset and makes them clickable"""

    # read in data
    df = pd.read_csv("./data/city_area_buildings.csv")

    # if a building is selected
    if building != "not":
        df_building = df[df.pand_id == float(building)]
        df          = df[df.pand_id != building]
        
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

    # split coordinates to x and y coordinates
    df["wgs"] = df['wgs'].apply(lambda x:literal_eval(x))
    df['full_adress'] = df["full_adress"].apply(str)

    # put coordinates of buildings in right format for polygons
    for i in df.itertuples():
        coords = i.wgs
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df["pand_id"]),  'full_adress':list(df['full_adress']), 
            'functions':list(df['gebruiksdoelVerblijfsobject'])}

    # put address in right format for hovertool
    data['full_adress'] = [item.replace("\n", "<br>") for item in data['full_adress']]

    # count functions and put them in right format
    all_functions = []
    for item in data["functions"]:
        # count functions
        item   = dict(Counter(literal_eval(item)))
        string = str()
        
        for element in item:
            string = string + str(item[element]) + " "  + str(element) + "<br>"
        
        string = string 
        
        all_functions.append(string)


    data['functions'] = all_functions

    # set source for polygons
    s1 = ColumnDataSource(data=data)

    # all buildings to be plotted on map
    glyph = fig.multi_polygons(xs='ys', ys='xs', color="peru", name="pand", source=s1, alpha=0.3)

    # call back for when buildings are clicked
    call = CustomJS(args=dict(source=s1, fire=fire), code="""
            /* console.log(cb_data.source.selected.indices[0]); */

            let idx = cb_data.source.selected.indices[0];
            let pand_id = source.data.id[idx];
            console.log(pand_id);
            var url = '';

            /* here comes ajax callback, default fire size is small otherwise fire size is given*/
            if (fire == "not") {
                url = url.concat(window.location.origin , '/building/', pand_id , '/small')
                window.location.href = url
            } else {
                url = url.concat(window.location.origin , '/building/', pand_id , '/' , fire)
                window.location.href = url
            }
            """)

    # only make polygons clickable
    tap = TapTool(renderers=[glyph], callback=call)
    fig.add_tools(tap)


    # this is custom html for the hovertip (necassary to add "Click for more info...")
    TOOLTIPS = """
    <div class="bk" style="display: table; border-spacing: 2px;">
        <!-- one row -->
        <div class="bk" style="display: table-row;">
            <div class="bk bk-tooltip-row-label" style="display: table-cell;">Address:
            </div>
            <div class="bk bk-tooltip-row-value" style="display: table-cell;">
            <span class="bk" data-value="">@full_adress{safe}
            </span>
            <span class="bk bk-tooltip-color-block" data-swatch="" style="display: none;">
            </span>
            </div>
        </div>
        <!-- one row -->
        <div class="bk" style="display: table-row;">
            <div class="bk bk-tooltip-row-label" style="display: table-cell;">Functions in building: </div>
            <div class="bk bk-tooltip-row-value" style="display: table-cell;">
            <span class="bk" data-value="">@functions{safe}
            </span>
            <span class="bk bk-tooltip-color-block" data-swatch="" style="display: none;">
            </span>
            </div>
        </div>
        <!-- one row -->
        <div class="bk" style="display: table-row;">
            <div class="bk bk-tooltip-row-label" style="display: table-cell;"></div>
            <div class="bk bk-tooltip-row-value" style="display: table-cell; color:blue;">Click for more information <br> on building</div>
        </div>
    </div>
    """


    # add hovertool to map
    fig.add_tools(HoverTool(
        renderers = [glyph],
        tooltips = TOOLTIPS,
        formatters = {
            'full_adress'    : 'printf',
            'functions'      : 'printf'
        }
    ))

    return fig

def draw_radius(fig, building, fire):
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
    fig.patch(y_coords_scaled, x_coords_scaled, line_width=5, alpha = 0.2, color="red", legend_label=fire.capitalize() + " fire radius")

    return fig

def get_info(building, fire):
    """
    Get information abour function in building, functions about buildings in neighboring buildings and radius. How many neighboring 
    buildings and how many buildings are present in the radius and the full adresses.
    """
    # load data
    df = pd.read_csv("./data/city_area_buildings.csv", usecols=["pand_id", "gebruiksdoelVerblijfsobject", "neighbors", "linked_small", 
                                                                "linked_big", "full_adress"])
    
    # get all functions from building
    df_building        = df[df.pand_id == float(building)]
    functions_building = literal_eval(df_building.gebruiksdoelVerblijfsobject.values[0])
    functions          = Counter(functions_building)
    
    # get neighbors functions
    df_neighbors       = list(df[df.pand_id.isin(literal_eval(df_building.neighbors.values[0]))].gebruiksdoelVerblijfsobject)
    neighbor_functions = [item for lijst in df_neighbors for item in literal_eval(lijst)]
    neighbor_functions = Counter(neighbor_functions)

    # get linking for big or small fire
    if fire == "small":
        column = "linked_small"
    elif fire == "big":
        column = "linked_big"

    # put data in right format
    df_linked        = df[df.pand_id.isin(literal_eval(df_building[column].values[0]))] 
    linked_buildings = list(df_linked.gebruiksdoelVerblijfsobject)
    linked_functions = [item for lijst in linked_buildings for item in literal_eval(lijst)]
    linked_functions = Counter(linked_functions)
    
    # get number of buildings in jeopardy
    amount_neighbors = len(literal_eval(df_building.neighbors.values[0]))
    amount_radius    = len(literal_eval(df_building[column].values[0]))

    # get all adresses of buildings in jeopardy
    count_unkown = df_linked.full_adress.isnull().values.ravel().sum()
    all_adresses = list(df_linked.loc[df_linked['full_adress'].notnull(), 'full_adress'].values)

    # create complete address
    complete_adress = str()

    for adress in all_adresses:
        if "All in Amsterdam" in adress:
            adress           = adress.replace("All in Amsterdam", "")
            complete_adress += adress
        else:
            adress           = adress.replace("\n", " ").replace(" Amsterdam", "\n")
            complete_adress += adress
    
    complete_adress = complete_adress + "All in Amsterdam"

    if count_unkown > 0:
        complete_adress += "\n" + str(count_unkown) + " unkown adresses"
        
    complete_adress = complete_adress.replace("\n", "<br>")

    return dict(functions), dict(neighbor_functions), dict(linked_functions), amount_neighbors, amount_radius, complete_adress