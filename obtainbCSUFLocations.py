import osmnx as ox
import json
import pandas as pd

# Step 1: Define the place
place_name = "California State University, Fullerton, California, USA"

# Step 2: Download all building footprints
print("Downloading building data from OpenStreetMap...")
gdf = ox.features_from_place(place_name, tags={"building": True})

# Step 3: Build csuf_locations dictionary
csuf_locations = {}

for idx, row in gdf.iterrows():
    if pd.notnull(row.get('name')):  # Only if the building has a name
        centroid = row['geometry'].centroid
        csuf_locations[row['name']] = (centroid.y, centroid.x)  # lat, lon

print(f"Found {len(csuf_locations)} named buildings.")

# Step 4: Save to a JSON file
with open("csuf_locations.json", "w") as f:
    json.dump(csuf_locations, f, indent=4)

print("Saved building locations to csuf_locations.json!")

# Optional: Show a preview
for name, coords in list(csuf_locations.items())[:10]:
    print(f"{name}: {coords}")
