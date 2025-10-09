# -*- coding: utf-8 -*-
import folium
import json
from math import radians, sin, cos, sqrt, atan2
from itertools import permutations
import sys

def haversine(coord1, coord2):
    R = 6371.0
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def load_json(json_path="data.json"):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"? Error loading JSON: {e}")
        sys.exit(1)

def find_most_central_point(points_to_check, reference_points):
    """
    Finds the point in 'points_to_check' that has the minimum total distance 
    to all points in 'reference_points'.
    
    Args:
        points_to_check (list): Coordinates of potential central points (e.g., places).
        reference_points (list): Coordinates of points to measure distance against (e.g., people).
    
    Returns:
        list: The coordinates [lat, lon] of the most central point.
    """
    if not points_to_check or not reference_points:
        if points_to_check:
            return points_to_check[0]
        raise ValueError("Empty list of points.")
        
    min_sum_dist = float("inf")
    central_point = points_to_check[0]
    
    for p_check in points_to_check:
        # Calculate the total distance from the point being checked (p_check) 
        # to ALL reference points (p_ref).
        total_dist = sum(haversine(p_check, p_ref) for p_ref in reference_points)
        
        if total_dist < min_sum_dist:
            min_sum_dist = total_dist
            central_point = p_check
            
    return central_point

def build_coordinates_from_json(json_path="data.json"):
    data = load_json(json_path)

    start_points = []  # [{"name": ..., "coords": {"lat": ..., "lon": ...}}]
    intermediate_points = []
    central_end_points = [] 

    # START (people)
    for person in data.get("people", []):
        coords = person.get("address")
        if coords and "lat" in coords and "lon" in coords:
            start_points.append({"name": person["name"], "coords": coords})

    # INTERMEDIARY (dict)
    for name, coords in data.get("intermediary", {}).items():
        if coords and "lat" in coords and "lon" in coords:
            intermediate_points.append({"name": name, "coords": coords})

    # CENTRAL END POINTS (dict)
    for name, coords in data.get("places", {}).items():
        if coords and "lat" in coords and "lon" in coords:
            central_end_points.append({"name": name, "coords": coords})

    if not central_end_points:
        print("? No central end point found. Exiting.")
        sys.exit(1)
        
    if not start_points:
        print("?? Warning: No start points (people) found. Calculating central point based on places.")
        start_coords_for_centrality = [ [p["coords"]["lat"], p["coords"]["lon"]] for p in central_end_points ]
    else:
        # Get coordinates for start points (the people)
        start_coords_for_centrality = [ 
            [p["coords"]["lat"], p["coords"]["lon"]] for p in start_points 
        ]

    # Get coordinates for potential end points (the places)
    potential_end_coords = [ 
        [p["coords"]["lat"], p["coords"]["lon"]] for p in central_end_points 
    ]

    # Compute the most central end point relative to START POINTS (people)
    central_end_point_coords = find_most_central_point(
        points_to_check=potential_end_coords, 
        reference_points=start_coords_for_centrality
    )

    # Return the list of all central end points as well
    return start_points, intermediate_points, central_end_point_coords, central_end_points

def print_all_places_summary(start_points, intermediate_points, central_end_point, central_end_points):
    """Prints a summary of all places and identifies the most central end point."""
    print("\n" + "="*50)
    print("?? ALL PLACES IN THE MATRICE")
    print("="*50)

    # Find the name of the chosen central end point
    central_end_name = "N/A (Error in lookup)"
    for p in central_end_points: 
        if [p["coords"]["lat"], p["coords"]["lon"]] == central_end_point:
            central_end_name = p["name"]
            break

    print(f"?? **Most Central End Point**: **{central_end_name}**")
    print(f"(This point minimizes the total distance to all **START POINTS/PEOPLE**.)")
    print("-" * 50)
    
    # Start Points
    print("\nSTART POINTS (People):")
    for i, p in enumerate(start_points):
        print(f"  {i+1}. {p['name']}")
    
    # Intermediate Points
    print("\nINTERMEDIARY POINTS (Places to pass through):")
    for i, p in enumerate(intermediate_points):
        print(f"  {i+1}. {p['name']}")

    # Potential Central End Points
    print("\nPOTENTIAL CENTRAL END POINTS (Places):")
    for i, p in enumerate(central_end_points):
        status = "(Chosen Central)" if p['name'] == central_end_name else "(Alternative)"
        print(f"  {i+1}. {p['name']} {status}")
    print("="*50)

# Load data and build coordinate lists
start_points, intermediate_points, central_end_point, central_end_points = build_coordinates_from_json("data.json")
start_points_coords = [
    [p["coords"]["lat"], p["coords"]["lon"]] for p in start_points
]
intermediate_points_coords = [
    [p["coords"]["lat"], p["coords"]["lon"]] for p in intermediate_points
]

# Print the requested summary of all places
print_all_places_summary(start_points, intermediate_points, central_end_point, central_end_points)

# Define 10 distinct colors for the 10 start points
START_COLORS = [
    'red', 'blue', 'green', 'purple', 'darkred', 'orange', 'darkblue', 'gray', 'black'
]

# --------------------------------------------------
## Distance Table: Start $\longleftrightarrow$ Intermediary
# --------------------------------------------------
print("\nDistance Table: Start <-> Intermediary (km)")
# Get names for header and pad/truncate to a maximum of 10 characters
inter_names = [p["name"][:10].ljust(10) for p in intermediate_points]
header = ["Start\\Inter"] + inter_names
print("{:<15}".format(header[0]), end="")
for h in header[1:]:
    print("{}".format(h), end="")
print()

for i, start in enumerate(start_points):
    # Pad/truncate start point name to a maximum of 15 characters
    start_name = start["name"][:15].ljust(15)
    print("{}".format(start_name), end="")
    for inter_coords in intermediate_points_coords:
        dist = haversine([start["coords"]["lat"], start["coords"]["lon"]], inter_coords)
        print("{:>10}".format(round(dist, 2)), end="")
    print()

# --------------------------------------------------
## Distance Table: Intermediary $\longleftrightarrow$ End
# --------------------------------------------------
print("\nDistance Table: Intermediary <-> End (km)")
print("{:<15} {:>10}".format("Intermediary", "Dist_to_End"))
for inter in intermediate_points:
    # Pad/truncate intermediary point name to a maximum of 15 characters
    inter_name = inter["name"][:15].ljust(15)
    inter_coords = [inter["coords"]["lat"], inter["coords"]["lon"]]
    dist = haversine(inter_coords, central_end_point)
    print("{:<15} {:>10}".format(inter_name, round(dist, 2)))

# --------------------------------------------------
## Compute Best Paths
# --------------------------------------------------
results = []

for start in start_points_coords:
    best_distance = float("inf")
    best_path = None

    # Single intermediate
    for inter in intermediate_points_coords:
        total_dist = haversine(start, inter) + haversine(inter, central_end_point)
        if total_dist < best_distance:
            best_distance = total_dist
            best_path = [start, inter, central_end_point]

    # Two intermediates
    for inter1, inter2 in permutations(intermediate_points_coords, 2):
        total_dist = (
            haversine(start, inter1)
            + haversine(inter1, inter2)
            + haversine(inter2, central_end_point)
        )
        if total_dist < best_distance:
            best_distance = total_dist
            best_path = [start, inter1, inter2, central_end_point]

    results.append({
        'Start': start,
        'Path': best_path,
        'Distance_km': round(best_distance, 2)
    })

# --------------------------------------------------
## Plotting ???
# --------------------------------------------------
m = folium.Map(location=central_end_point, zoom_start=10)

# Start Points
for i, start in enumerate(start_points):
    coords = [start["coords"]["lat"], start["coords"]["lon"]]
    folium.Marker(coords, popup=start["name"],
                  icon=folium.Icon(color=START_COLORS[i % len(START_COLORS)])).add_to(m)

# Intermediate Points
for j, inter in enumerate(intermediate_points):
    coords = [inter["coords"]["lat"], inter["coords"]["lon"]]
    folium.Marker(coords, popup=inter["name"],
                  icon=folium.Icon(color="orange", icon="star")).add_to(m)

# ?? MODIFICATION: Plot ALL Central End Points
for end_point in central_end_points:
    coords = [end_point["coords"]["lat"], end_point["coords"]["lon"]]
    
    # Check if this is the chosen central point
    if coords == central_end_point:
        # Chosen Central End Point (Green Flag)
        folium.Marker(coords, popup=f"Chosen End: {end_point['name']}",
                      icon=folium.Icon(color="green", icon="flag")).add_to(m)
    else:
        # Non-Selected Potential End Point (Grey Home)
        folium.Marker(coords, popup=f"Alternative End: {end_point['name']}",
                      icon=folium.Icon(color="gray", icon="home")).add_to(m)


# Draw paths
for i, d in enumerate(results):
    color = START_COLORS[i % len(START_COLORS)]
    folium.PolyLine(d["Path"], color=color, weight=3, opacity=0.7,
                    tooltip=f"{start_points[i]['name']}: {d['Distance_km']} km").add_to(m)

m.save("shortest_routes_map.html")

# --------------------------------------------------
## Best Paths Summary with Names
# --------------------------------------------------
print("\nBest paths:")
# Find the name corresponding to `central_end_point` coordinates
central_end_name = "Central End Point"
for p in central_end_points: 
    if [p["coords"]["lat"], p["coords"]["lon"]] == central_end_point:
        central_end_name = p["name"]
        break

for i, d in enumerate(results):
    start_name = start_points[i]['name']
    path_coords = d['Path']
    
    # Determine the names of the intermediate points used in the path (excluding start/end)
    intermediate_used = path_coords[1:-1]
    inter_names_used = []
    
    # Map coordinates back to names for intermediate points
    for coord in intermediate_used:
        for inter in intermediate_points:
            inter_coords = [inter["coords"]["lat"], inter["coords"]["lon"]]
            if coord == inter_coords: 
                inter_names_used.append(inter["name"])
                break
    
    # Format the path string
    if not inter_names_used:
        path_str = f"Direct to {central_end_name}"
    else:
        path_str = " -> ".join(inter_names_used) + f" -> {central_end_name}"
        
    print(f"**{start_name}**: {path_str} -> **{d['Distance_km']} km**")

print("\n? Map saved as shortest_routes_map.html with color-coded start points and paths.")