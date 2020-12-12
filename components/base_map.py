import pandas as pd

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
