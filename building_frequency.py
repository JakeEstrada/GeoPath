import json
import matplotlib.pyplot as plt
from collections import Counter

# Load data from files
with open("csuf_locations.json", "r") as f:
    csuf_locations = json.load(f)

with open("tasks.json", "r") as f:
    tasks_data = json.load(f)

# Count how often each building is used in tasks.json
task_buildings = [task["building_name"] for task in tasks_data["tasks"]]
building_counts = Counter(task_buildings)

# Ensure all csuf_locations buildings are represented, even if unused
for building in csuf_locations:
    if building not in building_counts:
        building_counts[building] = 0

# Sort buildings alphabetically (or use sorted by frequency with .most_common())
sorted_buildings = dict(sorted(building_counts.items()))

# Plot the data
plt.figure(figsize=(14, 7))
plt.bar(sorted_buildings.keys(), sorted_buildings.values(), color="skyblue")
plt.xticks(rotation=90)
plt.xlabel("Building")
plt.ylabel("Task Frequency")
plt.title("Frequency of Tasks per Building (CSUF)")
plt.tight_layout()
plt.show()
