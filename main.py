from graph_builder import build_csuf_graph
from visualizer import plot_graph

G, csuf_locations = build_csuf_graph()
plot_graph(G, csuf_locations)
