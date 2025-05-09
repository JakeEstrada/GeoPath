import json
import networkx as nx
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two coordinates using the Haversine formula.
    Returns distance in meters.
    """
    # Earth radius in kilometers
    R = 6371.0
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    # Convert to meters
    return distance * 1000

def build_csuf_graph():
    """
    Build a graph representing the CSUF campus with buildings as nodes and
    paths as edges. Edge weights represent the distance between buildings.
    """
    # Load location data from JSON file
    with open('csuf_locations.json', 'r') as f:
        csuf_locations = json.load(f)
    
    # Create a new graph
    G = nx.Graph()
    
    # Add nodes for each building
    for building, coords in csuf_locations.items():
        lat, lon = coords
        G.add_node(building, pos=(lon, lat))
    
    # Connect buildings with edges
    buildings = list(csuf_locations.keys())
    for i in range(len(buildings)):
        for j in range(i+1, len(buildings)):
            building1 = buildings[i]
            building2 = buildings[j]
            lat1, lon1 = csuf_locations[building1]
            lat2, lon2 = csuf_locations[building2]
            
            # Calculate distance between buildings
            distance = calculate_distance(lat1, lon1, lat2, lon2)
            
            # Add edge with distance as weight
            G.add_edge(building1, building2, weight=distance)
    
    return G, csuf_locations

if __name__ == "__main__":
    # Test graph building
    G, locations = build_csuf_graph()
    print(f"Graph created with {len(G.nodes())} nodes and {len(G.edges())} edges")
    
    # Print some example shortest paths
    source = "Titan Student Union"
    targets = ["Computer Science", "McCarthy Hall", "Pollack Library"]
    
    for target in targets:
        try:
            path = nx.shortest_path(G, source=source, target=target, weight='weight')
            distance = nx.shortest_path_length(G, source=source, target=target, weight='weight')
            print(f"Shortest path from {source} to {target}:")
            print(f"  Path: {' -> '.join(path)}")
            print(f"  Distance: {distance:.2f} meters")
        except nx.NetworkXNoPath:
            print(f"No path found from {source} to {target}")