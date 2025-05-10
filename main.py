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
from kmp import kmp_search, search_tasks_by_building

# Set theme colors
BG_COLOR = "#ffffff"
PANEL_BG = "#ffffff"
ACCENT_COLOR = "#4a90e2"
TEXT_COLOR = "#333333"
BUTTON_BG = "#4a90e2"
BUTTON_FG = "#ffffff"
HOVER_COLOR = "#357abd"

def configure_styles():
    style = ttk.Style()
    style.theme_use('alt')
    
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

# Load weekly schedule
with open('weekly_tasks.json', 'r') as f:
    weekly_data = json.load(f)
    weekly_schedule = weekly_data['weekly_schedule']

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

# Calculate travel time between buildings (in minutes)
def calculate_travel_time(G, building1, building2):
    try:
        path = nx.shortest_path(G, source=building1, target=building2, weight='weight')
        distance = sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
        # Assuming average walking speed of 1.4 m/s (5 km/h)
        travel_time_minutes = (distance / 1.4) / 60
        return travel_time_minutes
    except nx.NetworkXNoPath:
        return float('inf')

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
        self.selected_building = None  # Track validated building
        self.task_controls = []  # Track buttons and widgets related to tasks
        self.selected_day = tk.StringVar(value="Monday")  # Default to Monday

        # Create GUI elements
        self.create_widgets()
    
    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create left panel for task selection
        left_panel = ttk.LabelFrame(main_frame, text="Task Selection", style='Panel.TLabelframe', padding="15")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Add day selection
        day_frame = ttk.Frame(left_panel, style='Main.TFrame')
        day_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(day_frame, text="Select Day:", style='Header.TLabel').pack(side=tk.LEFT, padx=5)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_combo = ttk.Combobox(day_frame, textvariable=self.selected_day, values=days, state="readonly", width=15)
        day_combo.pack(side=tk.LEFT, padx=5)
        day_combo.bind('<<ComboboxSelected>>', self.load_day_tasks)
        
        # Task selection combobox
        ttk.Label(left_panel, text="Select Task:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.task_combobox = ttk.Combobox(left_panel, width=50)
        self.task_combobox.pack(fill=tk.X, pady=(0, 15))
        self.update_task_combobox()
        self.task_controls.append(self.task_combobox)
        
        # Enable task combobox by default
        self.task_combobox.configure(state='normal')
        
        # Populate combobox with task names
        self.update_task_combobox()
        
        # Buttons for task management
        button_frame = ttk.Frame(left_panel, style='Main.TFrame')
        button_frame.pack(fill=tk.X, pady=10)
        
        add_button = ttk.Button(button_frame, text="Add Task", command=self.add_task, style='Action.TButton')
        add_button.pack(side=tk.LEFT, padx=6)
        self.task_controls.append(add_button)
        create_button = ttk.Button(button_frame, text="Create New Task", command=self.create_new_task, style='Action.TButton')
        create_button.pack(side=tk.LEFT, padx=6)
        self.task_controls.append(create_button)
        remove_button = ttk.Button(button_frame, text="Remove Task", command=self.remove_task, style='Action.TButton')
        remove_button.pack(side=tk.LEFT, padx=6)
        self.task_controls.append(remove_button)
        clear_button = ttk.Button(button_frame, text="Clear All Tasks", command=self.clear_tasks, style='Action.TButton')
        clear_button.pack(side=tk.LEFT, padx=6)
        self.task_controls.append(clear_button)

        # Search bar for buildings
        ttk.Label(left_panel, text="Search Building:", style='Header.TLabel').pack(anchor=tk.W, pady=(10, 5))

        search_frame = ttk.Frame(left_panel, style='Main.TFrame')
        search_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        search_button = ttk.Button(search_frame, text="Search", command=self.perform_search, style='Action.TButton')
        search_button.pack(side=tk.LEFT, padx=6)

        # Selected tasks listbox
        ttk.Label(left_panel, text="Selected Tasks:", style='Header.TLabel').pack(anchor=tk.W, pady=(15, 5))
        
        # Create a frame for the listbox with a border
        listbox_frame = ttk.Frame(left_panel, style='Main.TFrame')
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
        optimize_button = ttk.Button(left_panel, 
                  text="Optimize Schedule and Find Route",
                  command=self.optimize_and_find_route,
                  style='Action.TButton').pack(fill=tk.X, pady=15)
        self.task_controls.append(optimize_button)
        
        # Schedule display
        ttk.Label(left_panel, text="Optimized Schedule:", style='Header.TLabel').pack(anchor=tk.W, pady=(15, 5))
        
        # Create a frame for the schedule text with a border
        schedule_frame = ttk.Frame(left_panel, style='Main.TFrame')
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
        route_info_frame = ttk.Frame(left_panel, style='Main.TFrame')
        route_info_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.route_info_text = tk.Text(route_info_frame,
                                     height=4,
                                     width=70,
                                     bg=PANEL_BG,
                                     fg=TEXT_COLOR,
                                     font=('Helvetica', 9))
        self.route_info_text.pack(fill=tk.X)
        
        # Canvas for map display
        self.canvas_frame = ttk.Frame(main_frame, style='Main.TFrame')
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Show initial map
        self.show_initial_map()

    def disable_task_controls(self):
        for widget in self.task_controls:
            widget.configure(state='disabled')

    def enable_task_controls(self):
        for widget in self.task_controls:
            if isinstance(widget, (tk.Button, tk.Entry, tk.Text, tk.Checkbutton, tk.Radiobutton, ttk.Button, ttk.Entry, ttk.Checkbutton, ttk.Radiobutton)):
                widget.configure(state='normal')

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
    
    def show_initial_map(self):
        # Create initial map with all buildings
        fig, ax = plt.subplots(figsize=(12, 10))  # Consistent size with plot_route
        
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
        important_buildings = list()  # Include all buildings
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
    
    def create_new_task(self):
        # Create a new window for task creation
        task_window = tk.Toplevel(self.root)
        task_window.title("Create A New Task")
        task_window.geometry("400x350")
        task_window.configure(bg=BG_COLOR)
    
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
            
            # Validate building exists
            if building not in csuf_locations:
                messagebox.showerror("Error", f"Building '{building}' not found in campus locations")
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
        
        # Step 1: Group tasks by time slot and priority
        task_groups = {}
        for task in self.selected_tasks:
            key = (task['priority'], task['time_start'], task['time_finish'])
            if key not in task_groups:
                task_groups[key] = []
            task_groups[key].append(task)
        
        # Early pruning optimization:
        # If there are many groups, process them in chronological order
        # and prune combinations that are already worse than the best found
        
        # Sort groups by time for early pruning
        sorted_keys = sorted(task_groups.keys(), key=lambda k: parse_time(k[1]))
        sorted_groups = [task_groups[k] for k in sorted_keys]
        
        # For very large problems, limit the search space
        MAX_COMBINATIONS = 1000  # Set a reasonable limit based on performance testing
        total_combinations = 1
        for group in sorted_groups:
            total_combinations *= len(group)
        
        if total_combinations > MAX_COMBINATIONS:
            # Apply heuristics for large problems
            # For example, for each time slot, keep only the N closest buildings to previous location
            # This is just a placeholder for the concept - implementation would depend on specific needs
            print(f"Warning: Large search space ({total_combinations} combinations). Applying heuristics.")
            return self.greedy_optimize_route()
        
        # For reasonable sized problems, use optimized branch and bound
        return self.branch_and_bound_optimize(sorted_groups)

    def branch_and_bound_optimize(self, sorted_groups):
        """Optimized branch and bound approach for finding best schedule"""
        min_distance = float('inf')
        best_schedule = None
        best_route = None
        
        # Helper function for recursive branching
        def branch(current_index, current_schedule, current_location, accumulated_distance):
            nonlocal min_distance, best_schedule, best_route
            
            # Base case: all groups processed
            if current_index == len(sorted_groups):
                # Calculate final route and distance
                route, total_distance = find_optimal_route(self.G, current_schedule)
                if total_distance < min_distance:
                    min_distance = total_distance
                    best_schedule = current_schedule.copy()
                    best_route = route
                return
            
            # Process current group
            current_group = sorted_groups[current_index]
            
            # Sort tasks in this group by distance from current_location if available
            if current_location and current_index > 0:
                tasks_with_distance = []
                for task in current_group:
                    task_location = task['building_name']
                    distance = calculate_travel_time(self.G, current_location, task_location)
                    tasks_with_distance.append((task, distance))
                
                # Sort by distance (best candidates first for branch pruning)
                sorted_tasks = [t[0] for t in sorted(tasks_with_distance, key=lambda x: x[1])]
            else:
                sorted_tasks = current_group
            
            # Try each task in the sorted group
            for task in sorted_tasks:
                # Calculate estimated distance increase
                new_distance = accumulated_distance
                if current_location:
                    estimated_distance = calculate_travel_time(self.G, current_location, task['building_name'])
                    new_distance += estimated_distance
                    
                    # Early pruning: skip this branch if already worse than best
                    if new_distance >= min_distance:
                        continue
                
                # Add task to current schedule
                new_schedule = current_schedule + [task]
                
                # Recurse to next group
                branch(current_index + 1, new_schedule, task['building_name'], new_distance)
        
        # Start branching from the first group with empty schedule
        branch(0, [], None, 0)
        
        # Update UI with the best found solution
        if best_schedule:
            self.update_ui_with_solution(best_schedule, best_route, min_distance)
            return best_schedule, best_route, min_distance
        return [], [], 0

    def greedy_optimize_route(self):
        """Greedy approach for very large problems"""
        # Sort all tasks by priority (high to low)
        priority_values = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        sorted_tasks = sorted(self.selected_tasks, 
                             key=lambda x: (-priority_values.get(x['priority'], 0), 
                                           parse_time(x['time_start'])))
        
        schedule = []
        current_location = None
        
        # Process tasks in time order
        for time_slot in sorted(set([(t['time_start'], t['time_finish']) for t in sorted_tasks]), 
                               key=lambda x: parse_time(x[0])):
            
            # Get all tasks in this time slot
            slot_tasks = [t for t in sorted_tasks if (t['time_start'], t['time_finish']) == time_slot]
            
            # If no current location, pick highest priority task
            if not current_location:
                task = slot_tasks[0]  # Already sorted by priority
            else:
                # Find closest task from current location
                min_distance = float('inf')
                task = None
                
                # Group by priority
                priority_groups = {}
                for t in slot_tasks:
                    p = t['priority']
                    if p not in priority_groups:
                        priority_groups[p] = []
                    priority_groups[p].append(t)
                
                # Start with highest priority
                for priority in sorted(priority_groups.keys(), 
                                     key=lambda p: -priority_values.get(p, 0)):
                    
                    # Find closest task in this priority group
                    for t in priority_groups[priority]:
                        distance = calculate_travel_time(self.G, current_location, t['building_name'])
                        if distance < min_distance:
                            min_distance = distance
                            task = t
                    
                    # If we found a task in this priority group, don't check lower priorities
                    if task:
                        break
            
            # Add selected task to schedule
            if task:
                schedule.append(task)
                current_location = task['building_name']
        
        # Apply schedule optimization to handle any remaining time conflicts
        optimized_schedule = optimize_schedule(schedule)
        
        # Calculate route and distance
        route, total_distance = find_optimal_route(self.G, optimized_schedule)
        
        # Update UI
        self.update_ui_with_solution(optimized_schedule, route, total_distance)
        
        return optimized_schedule, route, total_distance

    def update_ui_with_solution(self, schedule, route, total_distance):
        """Update UI with the computed solution"""
        self.schedule = schedule
        
        # Clear and update selected tasks listbox
        self.selected_tasks_listbox.delete(0, tk.END)
        self.selected_tasks = sorted(list({task['task_name']: task for task in schedule}.values()), 
                                  key=lambda x: parse_time(x['time_start']))
        
        for task in self.selected_tasks:
            task_str = f"{task['task_name']} ({task['building_name']}, {task['time_start']}-{task['time_finish']}, {task['priority']})"
            self.selected_tasks_listbox.insert(tk.END, task_str)
        
        # Display optimized schedule
        self.schedule_text.delete(1.0, tk.END)
        self.schedule_text.insert(tk.END, "Optimized Schedule:\n\n")
        
        for i, task in enumerate(schedule, 1):
            self.schedule_text.insert(tk.END, f"{i}. {task['task_name']}\n")
            self.schedule_text.insert(tk.END, f"   Location: {task['building_name']}\n")
            self.schedule_text.insert(tk.END, f"   Time: {task['time_start']} - {task['time_finish']}\n")
            self.schedule_text.insert(tk.END, f"   Priority: {task['priority']}\n\n")
        
        # Plot route
        fig, ax = plot_route(self.G, route, csuf_locations)
        
        # Update canvas
        if hasattr(self, 'canvas'):
            self.canvas_widget.destroy()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Update route information
        self.route_info_text.delete(1.0, tk.END)
        self.route_info_text.insert(tk.END, f"Route Information:\n")
        self.route_info_text.insert(tk.END, f"Number of tasks: {len(schedule)}\n")
        self.route_info_text.insert(tk.END, f"Number of locations: {len(route)}\n")
        self.route_info_text.insert(tk.END, f"Total distance: {total_distance/1000:.2f} km")

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showinfo("Info", "Please enter a building name to search.")
            return

        # Search through buildings in csuf_locations
        matches = []
        for building_name in csuf_locations.keys():
            if kmp_search(building_name, query):
                matches.append(building_name)

        if not matches:
            messagebox.showinfo("No Matches", f"Building '{query}' is not found. Please enter an existing building!")
            self.selected_building = None
            return

        # If found, pick the first match (or you can show choices)
        matched_building = matches[0]
        messagebox.showinfo("Found", f"Building '{matched_building}' is found!")
        self.selected_building = matched_building

        # Enable task-related buttons after valid building search
        self.enable_task_controls()

    def load_day_tasks(self, event=None):
        # Clear current tasks
        self.selected_tasks = []
        self.selected_tasks_listbox.delete(0, tk.END)
        self.schedule = []
        self.schedule_text.delete(1.0, tk.END)
        self.route_info_text.delete(1.0, tk.END)
        
        # Get tasks for selected day
        selected_day = self.selected_day.get()
        if selected_day in weekly_schedule:
            day_tasks = weekly_schedule[selected_day]
            
            # Add each task to the selected tasks list
            for task in day_tasks:
                # Verify the building exists in csuf_locations
                if task['building_name'] in csuf_locations:
                    self.selected_tasks.append(task)
                    task_str = f"{task['task_name']} ({task['building_name']}, {task['time_start']}-{task['time_finish']}, {task['priority']})"
                    self.selected_tasks_listbox.insert(tk.END, task_str)
                else:
                    messagebox.showwarning("Warning", f"Building '{task['building_name']}' not found in campus locations. Task '{task['task_name']}' will be skipped.")
            
            # Enable task controls after loading tasks
            self.enable_task_controls()
            
            # Show initial map
            self.show_initial_map()

# Main function
if __name__ == "__main__":
    root = tk.Tk()
    app = CSUFScheduleApp(root)
    root.mainloop()