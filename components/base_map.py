import pandas as pd
import pyclipper

from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors

from pyproj import Transformer, transform

TRAN_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

def create_base_map():
    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    fig = figure(x_range=(530683.95, 555576.10), y_range=(6854570.54, 6876203.35),
                 x_axis_type="mercator", y_axis_type="mercator", plot_width=1000, plot_height=600)

    fig.add_tile(tile_provider)

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
    df = pd.read_csv('/home/tom/Documents/dsp-project/data/tram_metro_lijnen.csv')
    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(convert)

    for i in range(len(df)):
        coords = df.iloc[i]['WKT_LAT_LNG']

        for j in range(0, len(coords), 4):
            coord = coords[j]
            fig.circle(coord[0], coord[1], size=3)

    return fig

def draw_polygon(fig):
    # test data for a house/building
    coordinates             = [[52.31960, 4.81197], [52.31961, 4.81205], [52.31968, 4.81202], [52.31967, 4.81194], [52.31960, 4.81197]]
    transformed_coordinates = [TRAN_4326_TO_3857.transform(coord[0], coord[1]) for coord in coordinates]
    
    x_coords = [c[1] for c in transformed_coordinates]
    y_coords = [c[0] for c in transformed_coordinates]

    fig.patch(y_coords, x_coords, line_width=5, color="red")

    clipper_offset     = pyclipper.PyclipperOffset()
    coordinates_scaled = pyclipper.scale_to_clipper(coordinates)

    clipper_offset.AddPath(coordinates_scaled, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    new_coordinates    = clipper_offset.Execute(pyclipper.scale_to_clipper(.0001))
    scaled_coordinates = pyclipper.scale_from_clipper(new_coordinates)
    scaled_coordinates = [TRAN_4326_TO_3857.transform(coord[0], coord[1]) for coord in scaled_coordinates[0]]

    x_coords_scaled = [c[1] for c in scaled_coordinates]
    y_coords_scaled = [c[0] for c in scaled_coordinates]

    fig.patch(y_coords_scaled, x_coords_scaled, line_width=5, alpha = 0.2, color="navy")

    return fig
