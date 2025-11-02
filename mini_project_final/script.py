#CUEVAS, MEYER, MIRBEY
import folium
import json
from math import radians, sin, cos, sqrt, atan2
import sys
import os
import base64, mimetypes
import networkx as nx
import pandas as pd
from tqdm import tqdm
import time

json_path = "data(1).json"
parquet_file = "highways.parquet"

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

def haversine(coord1, coord2):
    R = 6371.0
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def load_json(json_path=json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        sys.exit(1)

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

def img_to_data_uri(filepath: str) -> str:
    if not os.path.exists(filepath):
        return None
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "image/png"
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def make_image_popup(title, img_data_uri=None, instruction="", width=560, height=480):
    if img_data_uri:
        img_html = f'<img src="{img_data_uri}" alt="Plan" style="width:100%;height:auto;border-radius:6px;box-shadow:0 0 8px #aaa;"/>'
    else:
        img_html = '<div style="width:100%;height:200px;display:flex;align-items:center;justify-content:center;background:#f0f0f0;color:#555;">No image available</div>'
    html = f"""
    <div style="width:{width-20}px;padding:8px 10px">
        <h4>{title}</h4>
        {img_html}
        <p style="margin-top:8px;font-size:0.9em;color:#555;">{instruction}</p>
    </div>"""
    return folium.Popup(folium.IFrame(html=html, width=width, height=height), max_width=width + 20)

def build_coordinates_from_json(json_path=json_path):
    data = load_json(json_path)
    start_points, intermediate_points, central_end_points = [], [], []
    for person in data.get("people", []):
        coords = person.get("address")
        if coords and "lat" in coords and "lon" in coords:
            start_points.append(dict(name=person["name"], coords=[coords["lat"], coords["lon"]], img_path=person.get("img_path")))
    for name, info in data.get("intermediary", {}).items():
        if info and "lat" in info and "lon" in info:
            intermediate_points.append(dict(
                name=info["name"], coords=[info["lat"], info["lon"]],
                img_path=info.get("img_path"), instruction=info.get("instruction", "")
            ))
    for name, info in data.get("places", {}).items():
        if info and "lat" in info and "lon" in info:
            central_end_points.append(dict(
                name=info["name"], coords=[info["lat"], info["lon"]],
                img_path=info.get("img_path"), instruction=info.get("instruction", "")
            ))
    if not central_end_points:
        sys.exit("❌ No central end point.")
    start_coords = [p["coords"] for p in (start_points)]
    potential_end_coords = [p["coords"] for p in central_end_points]
    central_end = find_most_central_point(potential_end_coords, start_coords)
    return start_points, intermediate_points, central_end, central_end_points

def print_all_places_summary(start_points, inter_points, end_point, end_points):
    print("\n" + "="*50)
    print("📍 ALL PLACES IN THE MATRIX")
    print("="*50)
    central_name = next((p["name"] for p in end_points if p["coords"] == end_point), "Unknown")
    print(f"🏁 Most Central End Point: {central_name}")
    print("-"*50)
    print("\nSTARTS:")
    for p in start_points: print(f"  - {p['name']}")
    print("\nINTERMEDIARIES:")
    for p in inter_points: print(f"  - {p['name']}: {p.get('instruction','')}")
    print("\nDESTINATIONS:")
    for p in end_points:
        tag = "(Chosen)" if p["coords"] == end_point else "(Alt)"
        print(f"  - {p['name']} {tag}")
    print("="*50)

def calculate_bbox(coords, buffer=0.1):
    if not coords:
        return 0, 0, 0, 0
    min_lat = min(c[0] for c in coords) - buffer
    max_lat = max(c[0] for c in coords) + buffer
    min_lon = min(c[1] for c in coords) - buffer
    max_lon = max(c[1] for c in coords) + buffer
    return min_lat, max_lat, min_lon, max_lon

def check_row_in_bbox(nodes, min_lat, max_lat, min_lon, max_lon):
    for lat, lon in nodes:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    return False

def nearest_node_by_road(G, point, k=5):
    if not G.nodes:
        return point
    candidates = sorted(G.nodes, key=lambda n: haversine(n, point))[:k]
    best_node = None
    best_dist = float("inf")
    for node in candidates:
        snap_dist = haversine(point, node)
        if snap_dist < best_dist:
            best_node = node
            best_dist = snap_dist
    return best_node

def build_road_graph(all_coords):
    if not os.path.exists(parquet_file):
        raise FileNotFoundError(f"Parquet file '{parquet_file}' not found. Run the parser first.")
    df = pd.read_parquet(parquet_file)
    min_lat, max_lat, min_lon, max_lon = calculate_bbox(all_coords, buffer=0.1)
    tqdm.write("Filtering DataFrame by Bounding Box...")
    df_filtered = df[df['nodes'].apply(lambda x: check_row_in_bbox(x, min_lat, max_lat, min_lon, max_lon))]
    tqdm.write(f"Filtered from {len(df)} rows to {len(df_filtered)} rows.")
    del df
    G = nx.DiGraph()
    for _, row in tqdm(df_filtered.iterrows(), total=len(df_filtered), desc="Building Road Graph"):
        nodes = row['nodes']
        for i in range(len(nodes) - 1):
            start = tuple(nodes[i])
            end = tuple(nodes[i + 1])
            dist = haversine(start, end)
            G.add_edge(start, end, weight=dist)
    return G

def astar_road_path(G, source_node, target_node):
    try:
        return nx.astar_path(G, source_node, target_node, heuristic=lambda a, b: haversine(a, b), weight='weight')
    except nx.NetworkXNoPath:
        return []

start_time_total = time.time()
start_time_data = time.time()
start_points, inter_points, central_end_point, end_points = build_coordinates_from_json(json_path)
start_coords = [tuple(p["coords"]) for p in start_points]
inter_coords = [tuple(p["coords"]) for p in inter_points]
central_end_point_tuple = tuple(central_end_point)

print_all_places_summary(start_points, inter_points, central_end_point, end_points)

all_coords = start_coords + inter_coords + [central_end_point_tuple]
time_data = time.time() - start_time_data
print(f"\n⏱️ Time to load and process data: {time_data:.4f} seconds")

start_time_graph = time.time()
G = build_road_graph(all_coords)
time_graph = time.time() - start_time_graph
print(f"⏱️ Time to build road graph: {time_graph:.4f} seconds")

start_names = [p['name'] for p in start_points]
inter_names = [p['name'] for p in inter_points]
end_names = [p['name'] for p in end_points]

mobility_matrix_start_inter = pd.DataFrame(
    [[round(haversine(start_coord, inter_coord), 2) for inter_coord in inter_coords] for start_coord in start_coords],
    index=start_names,
    columns=inter_names
)

mobility_matrix_inter_end = pd.DataFrame(
    [[round(haversine(inter_coord, central_end_point_tuple), 2) for _ in end_names] for inter_coord in inter_coords],
    index=inter_names,
    columns=end_names
)

print("\n" + "="*50)
print("🗺️ MOBILITY MATRIX: ALL START POINTS TO ALL INTERMEDIARY POINTS (Straight-Line km)")
print("="*50)
print(mobility_matrix_start_inter)

print("\n" + "="*50)
print("🗺️ MOBILITY MATRIX: ALL INTERMEDIARY POINTS TO CENTRAL END POINT (Straight-Line km)")
print("="*50)
print(mobility_matrix_inter_end)
print("="*50)

START_COLORS = ['red','blue','green','purple','darkred','orange','darkblue','black']
results = []
start_time_road_calc = time.time()
for i, start_coord in enumerate(start_coords):
    start_time_path = time.time()

    closest_inter = None
    closest_dist = float('inf')
    for inter_coord in inter_coords:
        dist = haversine(start_coord, inter_coord)
        if dist < closest_dist:
            closest_inter = inter_coord
            closest_dist = dist

    near_start = nearest_node_by_road(G, start_coord)
    near_inter = nearest_node_by_road(G, closest_inter)
    near_end = nearest_node_by_road(G, central_end_point_tuple)

    path_start_to_inter = astar_road_path(G, near_start, near_inter)
    path_inter_to_end = astar_road_path(G, near_inter, near_end)

    time_path = time.time() - start_time_path
    print(f"\n⏱️ Path calculation for {start_points[i]['name']}: {time_path:.4f} seconds")

    if not path_start_to_inter or not path_inter_to_end:
        full_astar_path = []
        total_astar_dist = float('inf')
        print(f"⚠️ No A* path found for start to intermediary or intermediary to end for {start_points[i]['name']}")
    else:
        full_astar_path = path_start_to_inter + path_inter_to_end[1:]
        total_astar_dist = sum(G[u][v]['weight'] for u, v in zip(full_astar_path[:-1], full_astar_path[1:]))

    straight_dist = closest_dist + haversine(closest_inter, central_end_point_tuple)
    straight_path = [start_coord, closest_inter, central_end_point_tuple]

    start_name = start_points[i]['name']
    inter_name = next((ip['name'] for ip in inter_points if tuple(ip["coords"]) == closest_inter), "Unknown")
    end_name = next((ep['name'] for ep in end_points if tuple(ep["coords"]) == central_end_point_tuple), "Unknown")

    print(f"Path matrix for {start_name}: {start_name} (a) -> {inter_name} (b) -> {end_name} (c)")
    print(f" - Straight line distances: a->b={round(closest_dist,2)} km, b->c={round(haversine(closest_inter, central_end_point_tuple),2)} km")
    print(f" - A* road distances: a->b={round(sum(G[u][v]['weight'] for u,v in zip(path_start_to_inter[:-1], path_start_to_inter[1:])),2) if path_start_to_inter else 'N/A'} km, b->c={round(sum(G[u][v]['weight'] for u,v in zip(path_inter_to_end[:-1], path_inter_to_end[1:])),2) if path_inter_to_end else 'N/A'} km")

    results.append({
        'Start_name': start_name,
        'Intermediary_name': inter_name,
        'End_name': end_name,
        'Straight_Path_Coords': straight_path,
        'AStar_Path': full_astar_path,
        'Straight_Distance_km': round(straight_dist, 2),
        'AStar_Distance_km': round(total_astar_dist, 2)
    })

time_road_calc = time.time() - start_time_road_calc
print(f"\n⏱️ Total time for A* road path calculations: {time_road_calc:.4f} seconds")

start_time_map = time.time()
m = folium.Map(location=central_end_point, zoom_start=10)

for i, start in enumerate(start_points):
    popup = make_image_popup(f"Start {i+1} – {start['name']}", img_to_data_uri(start.get("img_path")))
    folium.Marker(start["coords"],
                  popup=popup,
                  icon=folium.Icon(color=START_COLORS[i % len(START_COLORS)], icon="play")).add_to(m)
for inter in inter_points:
    popup = make_image_popup(f"Intermédiaire – {inter['name']}",
                             img_to_data_uri(inter.get("img_path")),
                             inter.get("instruction",""))
    folium.Marker(inter["coords"],
                  icon=folium.Icon(color="orange", icon="star"), popup=popup).add_to(m)
for end in end_points:
    popup = make_image_popup(f"Arrivée – {end['name']}",
                             img_to_data_uri(end.get("img_path")),
                             end.get("instruction",""))
    color = "green" if end["coords"] == central_end_point else "gray"
    icon = "flag" if color == "green" else "home"
    folium.Marker(end["coords"],
                  icon=folium.Icon(color=color, icon=icon), popup=popup).add_to(m)

base_group = folium.FeatureGroup(name="1. Straight-Line Routes (Simple Graph)",show=True)
for i, d in enumerate(results):
    color = START_COLORS[i % len(START_COLORS)]
    tooltip_text = f"{d['Start_name']} – {d['Straight_Distance_km']} km (Straight)"
    folium.PolyLine(d["Straight_Path_Coords"], color=color, weight=3, opacity=0.6,
                    tooltip=tooltip_text, dash_array='5, 5').add_to(base_group)
base_group.add_to(m)

astar_group = folium.FeatureGroup(name="2. A* Road Network Routes (Realistic)",show=False)
for i, d in enumerate(results):
    path = d["AStar_Path"]
    if path:
        color = START_COLORS[i % len(START_COLORS)]
        tooltip_text = f"A* route for {d['Start_name']} ({d['AStar_Distance_km']} km)"
        folium.PolyLine(path, color=color, weight=5, opacity=0.8,
                        tooltip=tooltip_text).add_to(astar_group)
        print(f"✅ Route A* {d['Start_name']} calculée: {d['AStar_Distance_km']} km.")
    else:
        print(f"❌ Route A* {d['Start_name']} non trouvée. Straight distance was {d['Straight_Distance_km']} km.")
astar_group.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

m.save("map.html")
time_map = time.time() - start_time_map
print(f"⏱️ Time to generate and save map: {time_map:.4f} seconds")

time_total = time.time() - start_time_total
print(f"\n🎉 Total script execution time: {time_total:.4f} seconds")
print("\n✅ Map saved as map.html with two comparison layers: Straight-Line and A* Road Network.")

