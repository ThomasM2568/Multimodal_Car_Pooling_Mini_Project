import pandas as pd
import os
import networkx as nx
from tqdm import tqdm
import math
import folium
from collections import defaultdict

start_points_coords = [
    (47.639674, 6.863844),
    (47.678125, 6.848332),
    (47.510266, 7.001676),
    (47.512000, 7.002500),
    (47.583328, 6.75),
    (47.633331, 6.16667),
    (47.683331, 6.5),
    (47.51667, 6.8),
    (47.48333, 6.73333),
    (47.466671, 6.76667)
]

potential_end_points_coords = [
    (47.511364, 6.804863),
    (47.584155, 6.890579),
    (47.521808, 6.957887)
]

parquet_file = "highways.parquet"

def haversine_distance(coord1, coord2):
    """
    Calculates the great-circle distance between two points on the Earth 
    (specified in decimal degrees) using the Haversine formula. 
    This will serve as the A* heuristic.
    """
    R = 6371 # Earth radius in kilometers
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- A* Heuristic Function ---
def astar_heuristic(u, v):
    """
    A* heuristic: Haversine distance from node u to node v (the target).
    Assumes node coordinates are u=(lat, lon) and v=(lat, lon).
    """
    return haversine_distance(u, v)

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
    candidates = sorted(G.nodes, key=lambda n: haversine_distance(n, point))[:k]
    best_node = None
    best_dist = float("inf")
    for node in candidates:
        snap_dist = haversine_distance(point, node)
        if snap_dist < best_dist:
            best_node = node
            best_dist = snap_dist
    return best_node

# --- A* Path Function ---
def astar_path(G, source, target):
    """
    Finds the shortest path using the A* algorithm.
    """
    return nx.astar_path(G, source, target, heuristic=astar_heuristic, weight='weight')

if not os.path.exists(parquet_file):
    raise FileNotFoundError(f"Parquet file '{parquet_file}' not found. Run the parser first.")

df = pd.read_parquet(parquet_file)
all_coords = start_points_coords + potential_end_points_coords
min_lat, max_lat, min_lon, max_lon = calculate_bbox(all_coords, buffer=0.1)

tqdm.write("Filtering DataFrame by Bounding Box...")
df_filtered = df[df['nodes'].apply(lambda x: check_row_in_bbox(x, min_lat, max_lat, min_lon, max_lon))]
tqdm.write(f"Filtered from {len(df)} rows to {len(df_filtered)} rows.")
del df

G = nx.DiGraph()
for _, row in tqdm(df_filtered.iterrows(), total=len(df_filtered), desc="Building Graph"):
    nodes = row['nodes']
    for i in range(len(nodes) - 1):
        start = tuple(nodes[i])
        end = tuple(nodes[i + 1])
        dist = haversine_distance(start, end)
        # Ensure we don't overwrite with a longer path if multiple edges exist between nodes
        if not G.has_edge(start, end) or G[start][end]['weight'] > dist:
            G.add_edge(start, end, weight=dist)

start_nodes = [nearest_node_by_road(G, pt) for pt in start_points_coords]

end_point_scores = {}
for end_point in potential_end_points_coords:
    end_node = nearest_node_by_road(G, end_point)
    total_distance = 0
    for start_node in start_nodes:
        try:
            # --- Changed to astar_path_length ---
            total_distance += nx.astar_path_length(G, start_node, end_node, heuristic=astar_heuristic, weight='weight')
        except nx.NetworkXNoPath:
            total_distance += float('inf')
    end_point_scores[end_point] = total_distance

best_end_point = min(end_point_scores, key=end_point_scores.get)
best_end_node = nearest_node_by_road(G, best_end_point)

paths = []
for start_node in start_nodes:
    try:
        # --- Changed to astar_path ---
        paths.append(astar_path(G, start_node, best_end_node))
    except nx.NetworkXNoPath:
        paths.append([])

num_paths = len(paths)
path_edges_list = []
for path in paths:
    edges = []
    for i in range(len(path) - 1):
        edge = (path[i], path[i + 1])
        edges.append(edge)
    path_edges_list.append(edges)

edge_to_paths = defaultdict(set)
for idx, edges in enumerate(path_edges_list):
    for edge in edges:
        edge_to_paths[edge].add(idx)

base_colors = ["blue", "purple", "darkgreen", "cadetblue", "orange", "red", "darkred", "green", "darkblue", "lightred"]
shared_colors_pool = ["darkpurple", "pink", "lightgray", "black", "white"] # Added more colors for more paths
group_color_map = {}
next_shared_color_idx = 0

def get_color_for_group(group_key):
    global next_shared_color_idx
    if group_key not in group_color_map:
        if len(group_key) == 1:
            path_idx = next(iter(group_key))
            color = base_colors[path_idx % len(base_colors)]
        elif next_shared_color_idx < len(shared_colors_pool):
            color = shared_colors_pool[next_shared_color_idx]
            next_shared_color_idx += 1
        else:
            color = "black"
        group_color_map[group_key] = color
    return group_color_map[group_key]

path_segment_colors = [[] for _ in range(num_paths)]
meeting_points = {}

for i in range(num_paths):
    path = paths[i]
    if not path:
        continue
    for j in range(len(path) - 1):
        u, v = path[j], path[j + 1]
        edge = (u, v)
        paths_on_edge = edge_to_paths.get(edge, set())
        if len(paths_on_edge) > 1:
            merged_group_key = frozenset(paths_on_edge)
            if merged_group_key not in meeting_points:
                meeting_points[merged_group_key] = v
            color = get_color_for_group(merged_group_key)
            for path_idx in merged_group_key:
                if len(path_segment_colors[path_idx]) == j:
                    path_segment_colors[path_idx].append(color)
        else:
            color = get_color_for_group(frozenset([i]))
            path_segment_colors[i].append(color)

m = folium.Map(location=best_end_point, zoom_start=10)
for i, pt in enumerate(start_points_coords):
    folium.Marker(pt, popup=f"Start Point {i+1}", icon=folium.Icon(color=base_colors[i % len(base_colors)], icon="play")).add_to(m)

for pt in potential_end_points_coords:
    color = "red" if pt == best_end_point else "gray"
    icon_type = "star" if pt == best_end_point else "question-sign"
    popup_text = "Best Destination" if pt == best_end_point else "Potential Destination"
    folium.Marker(pt, popup=popup_text, icon=folium.Icon(color=color, icon=icon_type)).add_to(m)

for i, path in enumerate(paths):
    if not path:
        continue
    colors = path_segment_colors[i]
    for j in range(len(path) - 1):
        color = colors[j]
        folium.PolyLine([path[j], path[j + 1]], color=color, weight=4, opacity=0.8, tooltip=f"Route from Start {i+1} (Color: {color})").add_to(m)

for group_key, node in meeting_points.items():
    if len(group_key) > 1:
        start_indices = sorted([i + 1 for i in group_key])
        group_color = get_color_for_group(group_key)
        folium.Marker(node, popup=f"Meeting: Starts {start_indices}", icon=folium.Icon(color=group_color, icon="flag")).add_to(m)

print("---")
print(f"Best End Point (Minimum Total Distance): {best_end_point}")
print(f"Total Distances: {end_point_scores}")
print("---")

output_file = "franche_comte_route.html"
m.save(output_file)
