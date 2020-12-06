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
        final.append([float(coord[0]), float(coord[1])])

    return final

def add_public_transport(fig):
    lat, lon = 52.36, 4.9
    coord = TRAN_4326_TO_3857.transform(lat, lon)

    df = pd.read_csv('/home/tom/Documents/dsp-project/data/tram_metro_lijnen.csv')

    df['WKT_LAT_LNG'] = df['WKT_LAT_LNG'].apply(convert)

    coords = df.iloc[0]['WKT_LAT_LNG']

    for i in range(len(df)):
        coords = df.iloc[i]['WKT_LAT_LNG']

        for coord in coords:
            transformed_coord = TRAN_4326_TO_3857.transform(coord[0], coord[1])
            fig.circle(transformed_coord[0], transformed_coord[1], size = 5)

    return fig