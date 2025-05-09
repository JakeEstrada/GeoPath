import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import math
import heapq
from datetime import datetime as dt
import contextily as ctx
import geopandas as gpd
import pandas as pd
from pyproj import Transformer
import mplcursors

# Set theme colors
BG_COLOR = "#ffffff"
PANEL_BG = "#ffffff"
ACCENT_COLOR = "#4a90e2"
TEXT_COLOR = "#333333"
BUTTON_BG = "#4a90e2"
BUTTON_FG = "#ffffff"
HOVER_COLOR = "#357abd"

# Configure ttk styles
def configure_styles():
    style = ttk.Style()
    style.theme_use('alt')  # Use clam theme as base
    
    # Configure main frame style
    style.configure('Main.TFrame', background=BG_COLOR)
    
    # Configure panel styles
    style.configure('Panel.TLabelframe', background=PANEL_BG)
    style.configure('Panel.TLabelframe.Label', background=PANEL_BG, foreground=TEXT_COLOR, font=('Helvetica', 10, 'bold'))
    
    # Configure button styles
    style.configure('Action.TButton', 
                   background=BUTTON_BG,
                   foreground=BUTTON_FG,
                   font=('Helvetica', 9),
                   padding=5,
                   relief="flat",
                   borderwidth=0)
    style.map('Action.TButton',
              background=[('active', HOVER_COLOR), ('pressed', HOVER_COLOR)],
              foreground=[('active', BUTTON_FG), ('pressed', BUTTON_FG)],
              relief=[('pressed', 'flat'), ('!pressed', 'flat')])
    
    # Configure label styles
    style.configure('Header.TLabel',
                   font=('Helvetica', 10, 'bold'),
                   foreground=TEXT_COLOR,
                   background=PANEL_BG)
    
    # Configure combobox style
    style.configure('TCombobox',
                   background=PANEL_BG,
                   fieldbackground=PANEL_BG,
                   selectbackground=ACCENT_COLOR)

# Load data from JSON files
with open('csuf_locations.json', 'r') as f:
    csuf_locations = json.load(f)

with open('tasks.json', 'r') as f:
    tasks_data = json.load(f)
    tasks_list = tasks_data['tasks']

# Function to calculate distance between two coordinates (using Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
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

# Build graph of CSUF campus
def build_csuf_graph():
    G = nx.Graph()
    
    # Add nodes for each building
    for building, coords in csuf_locations.items():
        lat, lon = coords
        G.add_node(building, pos=(lon, lat))
    
    # Connect buildings with edges (fully connected graph)
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
    
    return G

# Find shortest path between buildings using Dijkstra's algorithm
def find_shortest_path(G, start_building, end_building):
    try:
        path = nx.shortest_path(G, source=start_building, target=end_building, weight='weight')
        return path
    except nx.NetworkXNoPath:
        return None

# Parse time string to datetime object
def parse_time(time_str):
    return dt.strptime(time_str, "%H:%M").time()

# Check if two tasks overlap
def tasks_overlap(task1, task2):
    task1_start = parse_time(task1['time_start'])
    task1_end = parse_time(task1['time_finish'])
    task2_start = parse_time(task2['time_start'])
    task2_end = parse_time(task2['time_finish'])
    
    # Check if task2 starts before task1 ends and task2 ends after task1 starts
    return (task2_start < task1_end) and (task2_end > task1_start)

# Sort tasks by priority and resolve time conflicts
def optimize_schedule(tasks):
    # Define priority values
    priority_values = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    
    # Sort tasks by priority (higher priority first) and then by start time
    sorted_tasks = sorted(
        tasks, 
        key=lambda x: (
            -priority_values.get(x['priority'], 0),  # Negative to sort in descending order
            parse_time(x['time_start'])
        )
    )
    
    optimized_schedule = []
    
    for task in sorted_tasks:
        # Check if current task overlaps with any task in the optimized schedule
        overlaps = False
        for scheduled_task in optimized_schedule:
            if tasks_overlap(task, scheduled_task):
                overlaps = True
                # If there's an overlap, keep the task with higher priority
                if priority_values.get(task['priority'], 0) > priority_values.get(scheduled_task['priority'], 0):
                    optimized_schedule.remove(scheduled_task)
                    optimized_schedule.append(task)
                break
        
        # If no overlap or resolved overlap, add task to schedule
        if not overlaps:
            optimized_schedule.append(task)
    
    # Sort optimized schedule by start time
    optimized_schedule = sorted(optimized_schedule, key=lambda x: parse_time(x['time_start']))
    
    return optimized_schedule

# Find the optimal route between buildings for a given schedule
def find_optimal_route(G, schedule):
    if not schedule:
        return [], 0
    
    route = []
    total_distance = 0
    buildings = [task['building_name'] for task in schedule]
    
    # Start from the first building
    current_building = buildings[0]
    route.append(current_building)
    
    # Find shortest path to each subsequent building
    for next_building in buildings[1:]:
        if current_building != next_building:
            path = find_shortest_path(G, current_building, next_building)
            if path:
                # Calculate distance for this segment
                for i in range(len(path) - 1):
                    total_distance += G[path[i]][path[i+1]]['weight']
                # Add intermediate buildings to route (excluding the starting point which is already in the route)
                route.extend(path[1:])
            else:
                # If no path found, just add the destination
                route.append(next_building)
        
        current_building = next_building
    
    return route, total_distance

# Plot the route on the map
def plot_route(G, route, csuf_locations):
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(12, 10))
    
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
    
    # Plot all buildings
    gdf.plot(ax=ax, color='gray', markersize=5)
    
    # Plot route
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
            ax.plot([x1, x2], [y1, y2], 'r-', linewidth=2)
        
        # Add labels for buildings in the route
        for i, (x, y, label) in enumerate(zip(route_gdf.geometry.x, route_gdf.geometry.y, route_gdf['name'])):
            ax.text(x + 10, y + 10, f"{i+1}. {label}", fontsize=8, weight='bold', color='black')
    
    # Add basemap
    ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
    
    plt.title("CSUF Optimized Route")
    
    # Add lat/lon display
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    def format_coord(x, y):
        lon, lat = transformer.transform(x, y)
        return f"longitude={lon:.5f}, latitude={lat:.5f}"

    ax.format_coord = format_coord
    
    return fig, ax

# Main application class
class CSUFScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSUF Schedule and Route Optimizer")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG_COLOR)
        
        # Configure styles
        configure_styles()
        
        # Build CSUF graph
        self.G = build_csuf_graph()
        
        # Initialize schedule and selected tasks
        self.schedule = []
        self.selected_tasks = []
        
        # Create GUI elements
        self.create_widgets()
    
    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel for task selection
        left_panel = ttk.LabelFrame(main_frame, text="Task Selection", style='Panel.TLabelframe', padding="15")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Create right panel for route display
        right_panel = ttk.LabelFrame(main_frame, text="Route Visualization", style='Panel.TLabelframe', padding="15")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Task selection elements
        ttk.Label(left_panel, text="Select Task:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # Create combobox for task selection
        self.task_combobox = ttk.Combobox(left_panel, width=50)
        self.task_combobox.pack(fill=tk.X, pady=(0, 15))
        
        # Populate combobox with task names
        self.update_task_combobox()
        
        # Buttons for task management
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Add Task", command=self.add_task, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Create New Task", command=self.create_new_task, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Task", command=self.remove_task, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All Tasks", command=self.clear_tasks, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        
        # Selected tasks listbox
        ttk.Label(left_panel, text="Selected Tasks:", style='Header.TLabel').pack(anchor=tk.W, pady=(15, 5))
        
        # Create a frame for the listbox with a border
        listbox_frame = ttk.Frame(left_panel)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.selected_tasks_listbox = tk.Listbox(listbox_frame, 
                                               height=8, 
                                               width=70,
                                               bg=PANEL_BG,
                                               fg=TEXT_COLOR,
                                               selectbackground=ACCENT_COLOR,
                                               selectforeground=BUTTON_FG,
                                               font=('Helvetica', 9))
        self.selected_tasks_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Schedule optimization and route finding
        ttk.Button(left_panel, 
                  text="Optimize Schedule and Find Route",
                  command=self.optimize_and_find_route,
                  style='Action.TButton').pack(fill=tk.X, pady=15)
        
        # Schedule display
        ttk.Label(left_panel, text="Optimized Schedule:", style='Header.TLabel').pack(anchor=tk.W, pady=(15, 5))
        
        # Create a frame for the schedule text with a border
        schedule_frame = ttk.Frame(left_panel)
        schedule_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.schedule_text = tk.Text(schedule_frame,
                                   height=8,
                                   width=70,
                                   bg=PANEL_BG,
                                   fg=TEXT_COLOR,
                                   font=('Helvetica', 9))
        self.schedule_text.pack(fill=tk.BOTH, expand=True)
        
        # Route information display
        ttk.Label(left_panel, text="Route Information:", style='Header.TLabel').pack(anchor=tk.W, pady=(15, 5))
        
        # Create a frame for the route info text with a border
        route_info_frame = ttk.Frame(left_panel)
        route_info_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.route_info_text = tk.Text(route_info_frame,
                                     height=4,
                                     width=70,
                                     bg=PANEL_BG,
                                     fg=TEXT_COLOR,
                                     font=('Helvetica', 9))
        self.route_info_text.pack(fill=tk.X)
        
        # Canvas for map display
        self.canvas_frame = ttk.Frame(right_panel)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Show initial map
        self.show_initial_map()
    
    def show_initial_map(self):
        # Create initial map with all buildings
        fig, ax = plt.subplots(figsize=(6, 6))
        
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
        gdf = gdf.to_crs(epsg=3857)
        
        # Plot all buildings
        gdf.plot(ax=ax, color='red', markersize=6)
        
        # Add building labels for important buildings
        important_buildings = list(csuf_locations.keys())  # Include all buildings
        for x, y, label in zip(gdf.geometry.x, gdf.geometry.y, gdf['name']):
            if label in important_buildings:
                ax.text(x + 10, y + 10, label, fontsize=8, weight='bold', color='black')
        
        # Add basemap
        ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
        
        plt.title("CSUF Campus Map")
        
        # Add coordinate display
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
        
        # Update canvas
        if hasattr(self, 'canvas'):
            self.canvas_widget.destroy()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
    
    def update_task_combobox(self):
        # Sort tasks by name for better display
        sorted_tasks = sorted(tasks_list, key=lambda x: x['task_name'])
        task_names = [f"{t['task_name']} ({t['building_name']}, {t['time_start']}-{t['time_finish']}, {t['priority']})" 
                      for t in sorted_tasks]
        self.task_combobox['values'] = task_names
    
    def add_task(self):
        selected_text = self.task_combobox.get()
        if not selected_text:
            messagebox.showinfo("Information", "Please select a task first")
            return
            
        # Find the task that matches the selected text
        selected_task = None
        for task in tasks_list:
            task_str = f"{task['task_name']} ({task['building_name']}, {task['time_start']}-{task['time_finish']}, {task['priority']})"
            if task_str == selected_text:
                selected_task = task
                break
        
        if selected_task:
            # Check if task is already selected
            task_str = f"{selected_task['task_name']} ({selected_task['building_name']}, {selected_task['time_start']}-{selected_task['time_finish']}, {selected_task['priority']})"
            if task_str not in self.selected_tasks_listbox.get(0, tk.END):
                self.selected_tasks.append(selected_task)
                self.selected_tasks_listbox.insert(tk.END, task_str)
                # Clear the combobox selection
                self.task_combobox.set('')
        else:
            messagebox.showinfo("Information", "Please select a valid task from the dropdown")
    
    def create_new_task(self):
        # Create a new window for task creation
        task_window = tk.Toplevel(self.root)
        task_window.title("Create New Task")
        task_window.geometry("400x350")
        task_window.configure(bg=BG_COLOR)
        
        # Position the window below the main window
        x = self.root.winfo_x()
        y = self.root.winfo_y() + self.root.winfo_height()
        task_window.geometry(f"+{x}+{y}")
        
        # Create main frame with padding
        main_frame = ttk.Frame(task_window, style='Main.TFrame', padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Task name
        ttk.Label(main_frame, text="Task Name:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        task_name_entry = ttk.Entry(main_frame, width=30)
        task_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Building selection
        ttk.Label(main_frame, text="Building:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        building_combobox = ttk.Combobox(main_frame, width=30)
        building_combobox['values'] = sorted(list(csuf_locations.keys()))
        building_combobox.grid(row=1, column=1, padx=5, pady=5)
        
        # Start time
        ttk.Label(main_frame, text="Start Time (HH:MM):", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        start_time_entry = ttk.Entry(main_frame, width=30)
        start_time_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # End time
        ttk.Label(main_frame, text="End Time (HH:MM):", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        end_time_entry = ttk.Entry(main_frame, width=30)
        end_time_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Priority
        ttk.Label(main_frame, text="Priority:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        priority_combobox = ttk.Combobox(main_frame, width=30)
        priority_combobox['values'] = ["HIGH", "MEDIUM", "LOW"]
        priority_combobox.grid(row=4, column=1, padx=5, pady=5)
        
        # Save button
        def save_task():
            # Validate fields
            task_name = task_name_entry.get().strip()
            building = building_combobox.get()
            start_time = start_time_entry.get()
            end_time = end_time_entry.get()
            priority = priority_combobox.get()
            
            if not all([task_name, building, start_time, end_time, priority]):
                messagebox.showerror("Error", "All fields are required")
                return
            
            # Validate time format
            try:
                dt.strptime(start_time, "%H:%M")
                dt.strptime(end_time, "%H:%M")
            except ValueError:
                messagebox.showerror("Error", "Time format should be HH:MM")
                return
            
            # Create new task
            new_task = {
                "task_name": task_name,
                "building_name": building,
                "time_start": start_time,
                "time_finish": end_time,
                "priority": priority
            }
            
            # Add to tasks list
            tasks_list.append(new_task)
            
            # Update the combobox
            self.update_task_combobox()
            
            # Add to selected tasks
            self.selected_tasks.append(new_task)
            task_str = f"{task_name} ({building}, {start_time}-{end_time}, {priority})"
            self.selected_tasks_listbox.insert(tk.END, task_str)
            
            # Save to tasks.json file
            tasks_data['tasks'] = tasks_list
            with open('tasks.json', 'w') as f:
                json.dump(tasks_data, f, indent=2)
            
            # Close window
            task_window.destroy()
        
        ttk.Button(main_frame, 
                  text="Save Task",
                  command=save_task,
                  style='Action.TButton').grid(row=5, column=0, columnspan=2, pady=20)
    
    def remove_task(self):
        selected_index = self.selected_tasks_listbox.curselection()
        if selected_index:
            self.selected_tasks.pop(selected_index[0])
            self.selected_tasks_listbox.delete(selected_index[0])
    
    def clear_tasks(self):
        self.selected_tasks = []
        self.selected_tasks_listbox.delete(0, tk.END)
        self.schedule = []
        self.schedule_text.delete(1.0, tk.END)
    
    def optimize_and_find_route(self):
        if not self.selected_tasks:
            messagebox.showinfo("Information", "No tasks selected")
            return
        
        # Optimize schedule
        self.schedule = optimize_schedule(self.selected_tasks)
        
        # Display optimized schedule
        self.schedule_text.delete(1.0, tk.END)
        self.schedule_text.insert(tk.END, "Optimized Schedule:\n\n")
        
        for i, task in enumerate(self.schedule, 1):
            self.schedule_text.insert(tk.END, f"{i}. {task['task_name']}\n")
            self.schedule_text.insert(tk.END, f"   Location: {task['building_name']}\n")
            self.schedule_text.insert(tk.END, f"   Time: {task['time_start']} - {task['time_finish']}\n")
            self.schedule_text.insert(tk.END, f"   Priority: {task['priority']}\n\n")
        
        # Find optimal route
        route, total_distance = find_optimal_route(self.G, self.schedule)
        
        # Plot route
        fig, ax = plot_route(self.G, route, csuf_locations)
        
        # Update canvas
        if hasattr(self, 'canvas'):
            self.canvas_widget.destroy()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Update route information in the main window
        self.route_info_text.delete(1.0, tk.END)
        self.route_info_text.insert(tk.END, f"Route Information:\n")
        self.route_info_text.insert(tk.END, f"Number of tasks: {len(self.schedule)}\n")
        self.route_info_text.insert(tk.END, f"Number of locations: {len(route)}\n")
        self.route_info_text.insert(tk.END, f"Total distance: {total_distance/1000:.2f} km")

# Main function
if __name__ == "__main__":
    root = tk.Tk()
    app = CSUFScheduleApp(root)
    root.mainloop()