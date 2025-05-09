import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
import pandas as pd
from pyproj import Transformer  # <-- Add this import
import mplcursors  # Add this import

def plot_graph(G, csuf_locations):
    # Correct: Longitude first, Latitude second
    Longitudes = []
    latitudes = []
    names = []

    for name, (lat, lon) in csuf_locations.items():   
        Longitudes.append(lon)  # longitude
        latitudes.append(lat)  # latitude
        names.append(name)

    df = pd.DataFrame({'name': names, 'lon': Longitudes, 'lat': latitudes})
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs="EPSG:4326")

    # Reproject to Web Mercator (meters)
    gdf = gdf.to_crs(epsg=3857)
    
    important_buildings = ["Titan Student Union", "McCarthy Hall", "Pollak Library", "Engineering Building", "College Park Building"]

    # Now plot
    fig, ax = plt.subplots(figsize=(10, 10))
    scatter = gdf.plot(ax=ax, color='red', markersize=5)

    # Draw the graph
    for x, y, label in zip(gdf.geometry.x, gdf.geometry.y, gdf['name']):
        if label in important_buildings:
           ax.text(x + 10, y + 10, label, fontsize=8, weight='bold', color='black') # Adjusted text position

    ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)

    plt.title("CSUF Buildings with Map Background")

    # ---------------------------
    # ADD THIS FOR LAT/LON DISPLAY
    # ---------------------------
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    def format_coord(x, y):
        lon, lat = transformer.transform(x, y)
        return f"longitude={lon:.5f}, latitude={lat:.5f}"

    ax.format_coord = format_coord

    # Add hover functionality
    cursor = mplcursors.cursor(ax.collections[0], hover=True)

    @cursor.connect("add")
    def on_add(sel):
        sel.annotation.set_text(gdf.iloc[sel.index]['name'])
        sel.annotation.get_bbox_patch().set(fc="yellow", alpha=0.8)

    # ---------------------------
    plt.show()
