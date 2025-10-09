import pandas as pd
import os
import networkx as nx
from tqdm import tqdm
import math
import folium
from collections import defaultdict
import base64, mimetypes

# --- Configuration ---
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

# >>> Chemins FICHIERS (là où sont tes PNG sur la machine qui exécute ce script)
IMG_DEPART_FILE  = "/var/www/html/img/rdc_salon_depart.png"
IMG_ARRIVEE_FILE = "/var/www/html/img/rdc_cuisine_arrivee.png"

parquet_file = "highways.parquet"

# --- Helpers ---

def img_to_data_uri(filepath: str) -> str:
    """Encode un fichier image en data:URI base64 (pour <img src=...>)."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Image not found: {filepath}")
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "image/png"
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def make_image_popup(title, img_data_uri, width=560, height=480):
    """Popup Folium avec l’image intégrée."""
    html = f"""
    <div style="width:{width-20}px;padding:8px 10px">
      <h4 style="margin:0 0 6px">{title}</h4>
      <img src="{img_data_uri}" alt="Plan" style="width:100%;height:auto;display:block;border-radius:6px;box-shadow:0 0 8px #aaa;"/>
    </div>"""
    return folium.Popup(folium.IFrame(html=html, width=width, height=height), max_width=width + 20)

def haversine_distance(coord1, coord2):
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlon = lon2 - lon1
    dlat = lon2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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
    best_node, best_dist = None, float("inf")
    for node in candidates:
        snap_dist = haversine_distance(point, node)
        if snap_dist < best_dist:
            best_node, best_dist = node, snap_dist
    return best_node

def dijkstra_path(G, source, target):
    return nx.dijkstra_path(G, source, target, weight='weight')

# --- Data loading ---
if not os.path.exists(parquet_file):
    raise FileNotFoundError(f"Parquet file '{parquet_file}' not found. Run the parser first.")

df = pd.read_parquet(parquet_file)

# Bounding box + filter
all_coords = start_points_coords + potential_end_points_coords
min_lat, max_lat, min_lon, max_lon = calculate_bbox(all_coords, buffer=0.1)

tqdm.write("Filtering DataFrame by Bounding Box...")
df_filtered = df[df['nodes'].apply(lambda x: check_row_in_bbox(x, min_lat, max_lat, min_lon, max_lon))]
tqdm.write(f"Filtered from {len(df)} rows to {len(df_filtered)} rows.")
del df

# Build graph
G = nx.Graph()
for _, row in tqdm(df_filtered.iterrows(), total=len(df_filtered), desc="Building Graph"):
    nodes = row['nodes']
    for i in range(len(nodes) - 1):
        a = tuple(nodes[i]); b = tuple(nodes[i+1])
        G.add_edge(a, b, weight=haversine_distance(a, b))

# Routing
start_nodes = [nearest_node_by_road(G, pt) for pt in start_points_coords]

end_point_scores = {}
for end_point in potential_end_points_coords:
    end_node = nearest_node_by_road(G, end_point)
    total_distance = 0
    for start_node in start_nodes:
        try:
            total_distance += nx.dijkstra_path_length(G, start_node, end_node, weight='weight')
        except nx.NetworkXNoPath:
            total_distance += float('inf')
    end_point_scores[end_point] = total_distance

best_end_point = min(end_point_scores, key=end_point_scores.get)
best_end_node  = nearest_node_by_road(G, best_end_point)

paths = []
for s in start_nodes:
    try:
        paths.append(dijkstra_path(G, s, best_end_node))
    except nx.NetworkXNoPath:
        paths.append([])

# --- Colors / meeting points (inchangé et simple) ---
base_colors = ["blue", "purple", "darkgreen", "cadetblue"]
m = folium.Map(location=best_end_point, zoom_start=10)

# Encode les images en data:URI (une fois pour toutes)
IMG_DEPART_DATA  = img_to_data_uri(IMG_DEPART_FILE)
IMG_ARRIVEE_DATA = img_to_data_uri(IMG_ARRIVEE_FILE)

# Start markers (image dans popup)
for i, pt in enumerate(start_points_coords):
    icon = folium.Icon(color=base_colors[i % len(base_colors)], icon="play")
    popup = make_image_popup(f"Départ {i+1} – Plan RDC (Salon)", IMG_DEPART_DATA)
    folium.Marker(pt, popup=popup, icon=icon).add_to(m)

# End markers (image seulement sur le meilleur)
for pt in potential_end_points_coords:
    is_best = (pt == best_end_point)
    color = "red" if is_best else "gray"
    icon   = folium.Icon(color=color, icon=("star" if is_best else "question-sign"))
    if is_best:
        popup = make_image_popup("Arrivée – Plan RDC (Cuisine)", IMG_ARRIVEE_DATA)
        folium.Marker(pt, popup=popup, icon=icon).add_to(m)
    else:
        folium.Marker(pt, popup="Destination potentielle", icon=icon).add_to(m)

# Draw paths
for i, path in enumerate(paths):
    if not path: 
        continue
    for j in range(len(path) - 1):
        folium.PolyLine([path[j], path[j+1]],
                        color=base_colors[i % len(base_colors)],
                        weight=4, opacity=0.8,
                        tooltip=f"Route from Start {i+1}").add_to(m)

print("---")
print(f"Best End Point: {best_end_point}")
print(f"Total Distances: {end_point_scores}")
print("---")

output_file = "templates/franche_comte_route.html"
m.save(output_file)
