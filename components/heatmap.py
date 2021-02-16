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

def draw_heatmap(fig, fire, score_type):
    """"Draws all polygons given in the dataset and makes them clickable"""
    
    # load data
    df = pd.read_csv("./data/city_area_buildings.csv")

    x_coords = []
    y_coords = []

    # split coordinates to x and y coordinates
    df["wgs"]         = df['wgs'].apply(lambda x:literal_eval(x))
    df['full_adress'] = df["full_adress"].apply(str)
    
    for i in range(len(df)):
        coords = df.iloc[i]['wgs']
        coords = [TRAN_4326_TO_3857.transform(float(coord[0]), float(coord[1])) for coord in coords]
        x_coords.append([[[c[1] for c in coords]]])
        y_coords.append([[[c[0] for c in coords]]])

    # identify score and fire type and select scores based on that
    if score_type == 'default':
        if fire == "small":
            scores            = df['score_small_default']
            scores_normalized = df['norm_score_small_default']
        elif fire == "big":
            scores            = df['score_big_default']
            scores_normalized = df['norm_score_big_default']
    elif score_type == 'residential':
        if fire == "small":
            scores            = df['score_small_residential']
            scores_normalized = df['norm_score_small_residential']
        elif fire == "big":
            scores            = df['score_big_residential']
    elif score_type == 'roads': 
        if fire == "small":
            scores            = df['score_small_road']
            scores_normalized = df['norm_score_small_road']
        elif fire == "big":
            scores            = df['score_big_road']
            scores_normalized = df['norm_score_big_road']

    # put all selected data into dictionary
    data = {'xs': x_coords, 'ys': y_coords, 'id':list(df["pand_id"]), 'scores':list(scores), 'norm_scores':list(scores_normalized), 
            'full_adress':list(df['full_adress']), 'functions':list(df['gebruiksdoelVerblijfsobject'])}
    
    # set full adress in proper form for hovertool
    data['full_adress'] = [item.replace("\n", "<br>") for item in data['full_adress']]

    # set functions in proper form for hovertool
    all_functions = []

    for item in data["functions"]:
        item   = dict(Counter(literal_eval(item)))
        string = str()

        for element in item:
            string = string + str(item[element]) + " " + str(element) + "<br>"
        
        all_functions.append(string)

    data['functions'] = all_functions

    # create color mapper for plotting
    exp_cmap = LinearColorMapper(palette=cc.fire, 
                             low = min(scores_normalized), 
                             high = max(scores_normalized))

    # set source for polygons
    s1 = ColumnDataSource(data=data)

    # all buildings to be plotted on map
    glyph = fig.multi_polygons(xs='ys', ys='xs', color={"field":"norm_scores", "transform":exp_cmap}, name="pand", 
                                source = s1, alpha=0.8, line_color="black", line_width=0.05)
    
    # callback when a building is clicked
    call = CustomJS(args=dict(source=s1, fire=fire), code="""
            /* console.log(cb_data.source.selected.indices[0]); */

            let idx = cb_data.source.selected.indices[0];
            let pand_id = source.data.id[idx];
            console.log(pand_id);

            /* here comes ajax callback, default fire size is small*/
            if (fire == "not") {
                window.location = ("/building/" + pand_id + "/small")
            } else {
                window.location = ("/building/" + pand_id + "/" + fire)
            }
            """)

    # only make polygons clickable
    tap = TapTool(renderers=[glyph], callback=call)
    fig.add_tools(tap)

    # custom hovertool (necessary for "Click for more info..." part)
    TOOLTIPS="""
    <div class="bk" style="display: table; border-spacing: 2px;">
        <!-- one row -->
        <div class="bk" style="display: table-row;">
            <div class="bk bk-tooltip-row-label" style="display: table-cell;">Score:
            </div>
            <div class="bk bk-tooltip-row-value" style="display: table-cell;">
            <span class="bk" data-value="">@norm_scores{0.2f}
            </span>
            <span class="bk bk-tooltip-color-block" data-swatch="" style="display: none;">
            </span>
            </div>
        </div>
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
        renderers=[glyph],
        tooltips=TOOLTIPS
    ))

    # create and add colorbar to map
    bar = ColorBar(color_mapper=exp_cmap, location=(0,0), major_label_overrides={0:"0   Low effect", 1:"1   High effect"}, major_label_text_align="left")
    fig.add_layout(bar, "right")

    return fig