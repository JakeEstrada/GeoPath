import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
import pandas as pd
from pyproj import Transformer
import mplcursors
import networkx as nx

def plot_graph(G, csuf_locations, route=None):
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Prepare data for GeoDataFrame
    names = []
    latitudes = []
    longitudes = []
    
    for name, (lat, lon) in csuf_locations.items():
        names.append(name)
        latitudes.append(lat)
        longitudes.append(lon)
    
    df = pd.DataFrame({'name': names, 'lat': latitudes, 'lon': longitudes})
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs="EPSG:4326")
    
    # Reproject to Web Mercator (meters)
    gdf = gdf.to_crs(epsg=3857)
    
    # Add building labels for important buildings
    important_buildings = [
        "Titan Student Union",
        "McCarthy Hall",
        "Pollak Library",
        "Engineering Building",
        "College Park Building"
    ]
    
    # Plot all buildings
    # First plot non-important buildings in gray
    non_important_mask = ~gdf['name'].isin(important_buildings)
    gdf[non_important_mask].plot(ax=ax, color='gray', markersize=5)
    
    # Then plot important buildings in black
    important_mask = gdf['name'].isin(important_buildings)
    gdf[important_mask].plot(ax=ax, color='black', markersize=8)
    
    # Plot route if provided
    if route:
        route_points = []
        route_names = []
        
        for building in route:
            lat, lon = csuf_locations[building]
            route_points.append((lon, lat))
            route_names.append(building)
        
        route_df = pd.DataFrame({'name': route_names, 'lon': [p[0] for p in route_points], 'lat': [p[1] for p in route_points]})
        route_gdf = gpd.GeoDataFrame(route_df, geometry=gpd.points_from_xy(route_df['lon'], route_df['lat']), crs="EPSG:4326")
        route_gdf = route_gdf.to_crs(epsg=3857)
        
        # Plot route points
        route_gdf.plot(ax=ax, color='red', markersize=8)
        
        # Draw lines connecting route points
        for i in range(len(route_gdf) - 1):
            x1, y1 = route_gdf.geometry.iloc[i].x, route_gdf.geometry.iloc[i].y
            x2, y2 = route_gdf.geometry.iloc[i+1].x, route_gdf.geometry.iloc[i+1].y
            ax.plot([x1, x2], [y1, y2], 'b-', linewidth=2, alpha=0.7)
    
    # Add building labels for important buildings
    important_buildings = [
        "Titan Student Union",
        "McCarthy Hall",
        "Pollak Library",
        "Engineering Building",
        "College Park Building"
    ]
    
    # Create a dictionary to store text positions to avoid overlap
    text_positions = {}
    
    for x, y, label in zip(gdf.geometry.x, gdf.geometry.y, gdf['name']):
        if label in important_buildings:
            # Calculate offset based on building position
            offset_x = 20
            offset_y = 20
            
            # Check if this position would overlap with existing text
            while any(abs(x + offset_x - pos_x) < 50 and abs(y + offset_y - pos_y) < 50 
                     for pos_x, pos_y in text_positions.values()):
                offset_x += 10
                offset_y += 10
            
            # Store the position
            text_positions[label] = (x + offset_x, y + offset_y)
            
            # Add the text with a white background for better visibility
            ax.text(x + offset_x, y + offset_y, label, 
                   fontsize=9, weight='bold', color='black',
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=2))
    
    # Add map background
    ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
    
    plt.title("CSUF Buildings with Map Background")
    
    # Add coordinate display
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    
    def format_coord(x, y):
        lon, lat = transformer.transform(x, y)
        return f"longitude={lon:.5f}, latitude={lat:.5f}"
    
    ax.format_coord = format_coord
    
    # Add hover functionality for all points
    cursor = mplcursors.cursor(ax.collections[0], hover=True)
    
    @cursor.connect("add")
    def on_add(sel):
        building_name = gdf.iloc[sel.index]['name']
        if building_name in important_buildings:
            sel.annotation.set_text(building_name)
        sel.annotation.get_bbox_patch().set(fc="yellow", alpha=0.8)
        else:
            sel.annotation.set_visible(False)
    
    # If there's a route, add hover functionality for route points too
    if route:
        cursor2 = mplcursors.cursor(ax.collections[1], hover=True)
        
        @cursor2.connect("add")
        def on_add_route(sel):
            sel.annotation.set_text(route_gdf.iloc[sel.index]['name'])
            sel.annotation.get_bbox_patch().set(fc="yellow", alpha=0.8)
    
    plt.show()
