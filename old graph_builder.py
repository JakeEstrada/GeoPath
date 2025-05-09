import networkx as nx
import json

def build_csuf_graph():
    with open("csuf_locations.json", "r") as f:
        csuf_locations = json.load(f)

    G = nx.Graph()
    for name, (lat, lon) in csuf_locations.items():
        G.add_node(name, pos=(lon, lat))
    
    return G, csuf_locations
