# -*- coding: utf-8 -*-
import folium
import json
from math import radians, sin, cos, sqrt, atan2
from itertools import permutations
import sys
import os
import base64, mimetypes

json_path = "data(1).json"

# --------------------------------------------------
# Distance calculation (Haversine)
# --------------------------------------------------
def haversine(coord1, coord2):
    R = 6371.0
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# --------------------------------------------------
# JSON Loading
# --------------------------------------------------
def load_json(json_path=json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        sys.exit(1)

# --------------------------------------------------
# Find the most central point
# --------------------------------------------------
def find_most_central_point(points_to_check, reference_points):
    if not points_to_check or not reference_points:
        if points_to_check:
            return points_to_check[0]
        raise ValueError("Empty list of points.")
        
    min_sum_dist = float("inf")
    central_point = points_to_check[0]
    
    for p_check in points_to_check:
        total_dist = sum(haversine(p_check, p_ref) for p_ref in reference_points)
        if total_dist < min_sum_dist:
            min_sum_dist = total_dist
            central_point = p_check
            
    return central_point

# --------------------------------------------------
# Image Handling
# --------------------------------------------------
def img_to_data_uri(filepath: str) -> str:
    """Encode image as data:URI base64 (for <img src=...>)."""
    if not os.path.exists(filepath):
        return None
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "image/png"
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def make_image_popup(title, img_data_uri=None, instruction="", width=560, height=480):
    """Popup Folium with optional image and instruction."""
    if img_data_uri:
        img_html = f'<img src="{img_data_uri}" alt="Plan" style="width:100%;height:auto;display:block;border-radius:6px;box-shadow:0 0 8px #aaa;"/>'
    else:
        img_html = '<div style="width:100%;height:200px;display:flex;align-items:center;justify-content:center;background:#f0f0f0;color:#555;border-radius:6px;box-shadow:0 0 8px #aaa;">No image available</div>'
    
    html = f"""
    <div style="width:{width-20}px;padding:8px 10px">
      <h4 style="margin:0 0 6px">{title}</h4>
      {img_html}
      <p style="margin-top:8px;font-size:0.9em;color:#555;">{instruction}</p>
    </div>"""
    
    return folium.Popup(folium.IFrame(html=html, width=width, height=height), max_width=width + 20)

# --------------------------------------------------
# Build coordinates from JSON
# --------------------------------------------------
def build_coordinates_from_json(json_path=json_path):
    data = load_json(json_path)

    start_points = []
    intermediate_points = []
    central_end_points = []

    # START POINTS (people)
    for person in data.get("people", []):
        coords = person.get("address")
        if coords and "lat" in coords and "lon" in coords:
            start_points.append({
                "name": person["name"],
                "coords": coords,
                "img_path": person.get("img_path", None)
            })

    # INTERMEDIARY POINTS
    for name, info in data.get("intermediary", {}).items():
        if info and "lat" in info and "lon" in info:
            intermediate_points.append({
                "name": info["name"],
                "coords": {"lat": info["lat"], "lon": info["lon"]},
                "img_path": info.get("img_path", None),
                "instruction": info.get("instruction", "")
            })

    # CENTRAL END POINTS
    for name, info in data.get("places", {}).items():
        if info and "lat" in info and "lon" in info:
            central_end_points.append({
                "name": info["name"],
                "coords": {"lat": info["lat"], "lon": info["lon"]},
                "img_path": info.get("img_path", None),
                "instruction": info.get("instruction", "")
            })

    if not central_end_points:
        print("❌ No central end point found. Exiting.")
        sys.exit(1)
        
    if not start_points:
        print("⚠️ Warning: No start points found. Calculating central point based on places.")
        start_coords_for_centrality = [
            [p["coords"]["lat"], p["coords"]["lon"]] for p in central_end_points
        ]
    else:
        start_coords_for_centrality = [
            [p["coords"]["lat"], p["coords"]["lon"]] for p in start_points
        ]

    potential_end_coords = [
        [p["coords"]["lat"], p["coords"]["lon"]] for p in central_end_points
    ]

    central_end_point_coords = find_most_central_point(
        points_to_check=potential_end_coords,
        reference_points=start_coords_for_centrality
    )

    return start_points, intermediate_points, central_end_point_coords, central_end_points

# --------------------------------------------------
# Print summary
# --------------------------------------------------
def print_all_places_summary(start_points, intermediate_points, central_end_point, central_end_points):
    print("\n" + "="*50)
    print("📍 ALL PLACES IN THE MATRIX")
    print("="*50)

    central_end_name = "N/A"
    for p in central_end_points:
        if [p["coords"]["lat"], p["coords"]["lon"]] == central_end_point:
            central_end_name = p["name"]
            break

    print(f"🏁 Most Central End Point: **{central_end_name}**")
    print("-"*50)
    
    print("\nSTART POINTS (People):")
    for i, p in enumerate(start_points):
        print(f"  {i+1}. {p['name']}")

    print("\nINTERMEDIARY POINTS:")
    for i, p in enumerate(intermediate_points):
        print(f"  {i+1}. {p['name']} - Instruction: {p.get('instruction', '')}")

    print("\nPOTENTIAL CENTRAL END POINTS:")
    for i, p in enumerate(central_end_points):
        status = "(Chosen)" if p['name'] == central_end_name else "(Alternative)"
        print(f"  {i+1}. {p['name']} - Instruction: {p.get('instruction', '')} {status}")
    print("="*50)

# --------------------------------------------------
# Main Execution
# --------------------------------------------------
start_points, intermediate_points, central_end_point, central_end_points = build_coordinates_from_json(json_path)

start_points_coords = [[p["coords"]["lat"], p["coords"]["lon"]] for p in start_points]
intermediate_points_coords = [[p["coords"]["lat"], p["coords"]["lon"]] for p in intermediate_points]

print_all_places_summary(start_points, intermediate_points, central_end_point, central_end_points)

START_COLORS = ['red', 'blue', 'green', 'purple', 'darkred', 'orange', 'darkblue', 'gray', 'black']

# --------------------------------------------------
# Compute best paths
# --------------------------------------------------
results = []
for start in start_points_coords:
    best_distance = float("inf")
    best_path = None
    for inter in intermediate_points_coords:
        total_dist = haversine(start, inter) + haversine(inter, central_end_point)
        if total_dist < best_distance:
            best_distance = total_dist
            best_path = [start, inter, central_end_point]
    for inter1, inter2 in permutations(intermediate_points_coords, 2):
        total_dist = (haversine(start, inter1)
                      + haversine(inter1, inter2)
                      + haversine(inter2, central_end_point))
        if total_dist < best_distance:
            best_distance = total_dist
            best_path = [start, inter1, inter2, central_end_point]
    results.append({'Start': start, 'Path': best_path, 'Distance_km': round(best_distance, 2)})

# --------------------------------------------------
# Map plotting
# --------------------------------------------------
m = folium.Map(location=central_end_point, zoom_start=10)

# Start Points
for i, start in enumerate(start_points):
    coords = [start["coords"]["lat"], start["coords"]["lon"]]
    img_file = start.get("img_path")
    img_data_uri = img_to_data_uri(img_file)
    popup = make_image_popup(f"Départ {i+1} – {start['name']}", img_data_uri)
    folium.Marker(coords, popup=popup,
                  icon=folium.Icon(color=START_COLORS[i % len(START_COLORS)])).add_to(m)

# Intermediate Points
for inter in intermediate_points:
    coords = [inter["coords"]["lat"], inter["coords"]["lon"]]
    img_file = inter.get("img_path")
    img_data_uri = img_to_data_uri(img_file)
    instruction = inter.get("instruction", "")
    popup = make_image_popup(f"Intermédiaire – {inter['name']}", img_data_uri, instruction=instruction)
    folium.Marker(coords, popup=popup,
                  icon=folium.Icon(color="orange", icon="star")).add_to(m)

# Central End Points
for end_point in central_end_points:
    coords = [end_point["coords"]["lat"], end_point["coords"]["lon"]]
    img_file = end_point.get("img_path")
    img_data_uri = img_to_data_uri(img_file)
    instruction = end_point.get("instruction", "")
    popup = make_image_popup(f"Arrivée – {end_point['name']}", img_data_uri, instruction=instruction)
    if coords == central_end_point:
        folium.Marker(coords, popup=popup,
                      icon=folium.Icon(color="green", icon="flag")).add_to(m)
    else:
        folium.Marker(coords, popup=popup,
                      icon=folium.Icon(color="gray", icon="home")).add_to(m)

# Draw Paths
for i, d in enumerate(results):
    color = START_COLORS[i % len(START_COLORS)]
    folium.PolyLine(d["Path"], color=color, weight=3, opacity=0.7,
                    tooltip=f"{start_points[i]['name']}: {d['Distance_km']} km").add_to(m)

m.save("shortest_routes_map.html")

# --------------------------------------------------
# Summary of best paths
# --------------------------------------------------
print("\nBest paths:")
central_end_name = next((p["name"] for p in central_end_points
                         if [p["coords"]["lat"], p["coords"]["lon"]] == central_end_point),
                        "Central End Point")

for i, d in enumerate(results):
    start_name = start_points[i]['name']
    path_coords = d['Path']
    inter_used = path_coords[1:-1]
    inter_names_used = []
    for coord in inter_used:
        for inter in intermediate_points:
            if coord == [inter["coords"]["lat"], inter["coords"]["lon"]]:
                inter_names_used.append(inter["name"])
                break
    if not inter_names_used:
        path_str = f"Direct to {central_end_name}"
    else:
        path_str = " -> ".join(inter_names_used) + f" -> {central_end_name}"
    print(f"**{start_name}**: {path_str} -> **{d['Distance_km']} km**")

print("\n✅ Map saved as shortest_routes_map.html with instructions and placeholder for missing images.")

