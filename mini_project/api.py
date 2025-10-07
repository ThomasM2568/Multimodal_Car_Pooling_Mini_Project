#!/usr/bin/python3
'''
Created on 30-09-2025

@author: TM
@version: 1

Python REST API using FLASK for Multimodal Car Pooling Project
'''

#------------------
# Import
#------------------

from flask import Flask, Blueprint, request, jsonify, render_template

import requests
import argparse
import os
import json
import re
import unicodedata
import time
from typing import Dict, Any, List, Optional

#------------------
# Argument parsing
#------------------

is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

if not is_gunicorn:
    parser = argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',action='store_true',help='Enable verbose mode')
    args = parser.parse_args()
    if args.verbose:
        print('***********************')
        print('Verbose mode is enabled')
        print('***********************')
        print()
else:
    class args:
        def __init__(self):
            self.verbose=True
            self.env="prod"
    args = args()

#------------------
# Flask API part
#------------------

app = Flask(__name__)

public_bp = Blueprint("public",__name__)

@public_bp.route("/isalive",methods=["GET"])
def is_alive():
    return "OK",200

app.register_blueprint(public_bp)

private_bp = Blueprint("private", __name__)

# ------------------
# Config & Helpers
#------------------

JSON_PATH = os.environ.get("JSON_PATH", "address.json")
NOMINATIM_USER_AGENT = os.environ.get(
    "NOMINATIM_USER_AGENT",
    "kyllian-address-api/1.0 (kyllian.cuevas@gmail.com)"
)
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"

# cache simple en mémoire
_DATA_CACHE: Dict[str, Any] = {}
_DATA_MTIME: Optional[float] = None

def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _addr_to_text(addr: Dict[str, Any]) -> str:
    parts = [
        addr.get("street"),
        f'{addr.get("postal_code", "")} {addr.get("city", "")}'.strip(),
        addr.get("country"),
    ]
    return ", ".join([p for p in parts if p])

def _load_json() -> Dict[str, Any]:
    global _DATA_CACHE, _DATA_MTIME
    if not os.path.exists(JSON_PATH):
        raise FileNotFoundError(f"JSON introuvable: {JSON_PATH}")
    mtime = os.path.getmtime(JSON_PATH)
    if _DATA_MTIME is None or mtime != _DATA_MTIME:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "places" not in data or "people" not in data:
            raise ValueError("Le JSON doit contenir 'places' et 'people'.")
        _DATA_CACHE = data
        _DATA_MTIME = mtime
    return _DATA_CACHE

def _best_match(query: str, pool: List[str]) -> Optional[str]:
    nq = _normalize(query)
    sub = [p for p in pool if nq in p]
    if sub:
        return sorted(sub, key=len)[0]
    qset = set(nq.split())
    best = None
    best_score = 0.0
    for p in pool:
        pset = set(p.split())
        inter = len(qset & pset)
        union = len(qset | pset)
        score = inter / union if union else 0.0
        if score > best_score:
            best_score = score
            best = p
    return best if best_score >= 0.5 else None

def _search_impl(query: str, category: Optional[str]) -> Optional[Dict[str, Any]]:
    data = _load_json()
    def _index(items):
        return {_normalize(it.get("name", "")): it for it in items}

    places_idx = _index(data["places"])
    people_idx = _index(data["people"])

    cats = ["places", "people"]
    if category == "place":
        cats = ["places"]
    elif category == "person":
        cats = ["people"]

    for cat in cats:
        pool = list((places_idx if cat == "places" else people_idx).keys())
        best = _best_match(query, pool)
        if best:
            item = (places_idx if cat == "places" else people_idx)[best]
            addr = item.get("address", {})
            return {
                "category": "place" if cat == "places" else "person",
                "name": item.get("name", ""),
                "address": addr,
                "address_text": _addr_to_text(addr),
            }
    return None

def _http_get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"User-Agent": NOMINATIM_USER_AGENT, "Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def _geocode(address_text: str) -> Optional[Dict[str, float]]:
    time.sleep(1.0)
    params = {
        "q": address_text,
        "format": "json",
        "addressdetails": 0,
        "limit": 1,
        "countrycodes": "fr",
    }
    data = _http_get(f"{NOMINATIM_BASE}/search", params)
    if not data:
        return None
    return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}

def _reverse(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """(lat, lon) -> adresse structurée complète"""
    time.sleep(1.0)
    params = {"lat": lat, "lon": lon, "format": "json", "zoom": 18, "addressdetails": 1}
    data = _http_get(f"{NOMINATIM_BASE}/reverse", params)
    if not data or "address" not in data:
        return None
    addr = data["address"]
    structured = {
        "house_number": addr.get("house_number"),
        "road": addr.get("road"),
        "suburb": addr.get("suburb"),
        "city": addr.get("city") or addr.get("town") or addr.get("village"),
        "postcode": addr.get("postcode"),
        "county": addr.get("county"),
        "state": addr.get("state"),
        "country": addr.get("country"),
        "country_code": addr.get("country_code"),
        "display_name": data.get("display_name")
    }
    return {k: v for k, v in structured.items() if v is not None}

#------------------
# Routes
#------------------

@private_bp.route('/api', methods=['GET'])
def get_root():
    return jsonify({
        "return_code": "OK",
        "response": "Template API answer",
        "data": {"parameter": "value"}
    }), 200

def _standard_response(func_name: str, data: Any, error: bool=False, code: int=200):
    return jsonify({
        "return_code": "ERROR" if error else "OK",
        "response": func_name,
        "data": data
    }), code

# --- Lookup ---
@private_bp.route('/api/geo/lookup', methods=['GET'])
def geo_lookup():
    query = request.args.get("query", "").strip()
    category = request.args.get("category")
    if not query:
        return _standard_response("geo_lookup", {"error": "query manquant"}, True, 400)
    if category and category not in ("place", "person"):
        return _standard_response("geo_lookup", {"error": "category invalide"}, True, 400)
    res = _search_impl(query, category)
    if not res:
        return _standard_response("geo_lookup", {"error": "Aucune correspondance"}, True, 404)
    return _standard_response("geo_lookup", res)

@private_bp.route('/api/geo/lookup/<path:q>', methods=['GET'])
def geo_lookup_path(q):
    category = request.args.get("category")
    if category and category not in ("place", "person"):
        return _standard_response("geo_lookup_path", {"error": "category invalide"}, True, 400)
    res = _search_impl(q, category)
    if not res:
        return _standard_response("geo_lookup_path", {"error": "Aucune correspondance"}, True, 404)
    return _standard_response("geo_lookup_path", res)

# --- Address ---
@private_bp.route('/api/geo/address', methods=['GET'])
def geo_address():
    query = request.args.get("query", "").strip()
    category = request.args.get("category")
    if not query:
        return _standard_response("geo_address", {"error": "query manquant"}, True, 400)
    if category and category not in ("place", "person"):
        return _standard_response("geo_address", {"error": "category invalide"}, True, 400)
    res = _search_impl(query, category)
    if not res:
        return _standard_response("geo_address", {"error": "Aucune correspondance"}, True, 404)
    return _standard_response("geo_address", res)

@private_bp.route('/api/geo/address/<path:q>', methods=['GET'])
def geo_address_path(q):
    category = request.args.get("category")
    if category and category not in ("place", "person"):
        return _standard_response("geo_address_path", {"error": "category invalide"}, True, 400)
    res = _search_impl(q, category)
    if not res:
        return _standard_response("geo_address_path", {"error": "Aucune correspondance"}, True, 404)
    return _standard_response("geo_address_path", res)

# --- Coords ---
@private_bp.route('/api/geo/coords', methods=['GET'])
def geo_coords():
    query = request.args.get("query", "").strip()
    category = request.args.get("category")
    if not query:
        return _standard_response("geo_coords", {"error": "query manquant"}, True, 400)
    if category and category not in ("place", "person"):
        return _standard_response("geo_coords", {"error": "category invalide"}, True, 400)
    res = _search_impl(query, category)
    if not res:
        return _standard_response("geo_coords", {"error": "Aucune correspondance"}, True, 404)
    coords = _geocode(res["address_text"])
    if not coords:
        return _standard_response("geo_coords", {"error": "Géocodage: aucun résultat"}, True, 502)
    data = {
        "name": res["name"],
        "category": res["category"],
        "address": res["address"],
        "address_text": res["address_text"],
        "coords": coords,
        "provider": "nominatim"
    }
    return _standard_response("geo_coords", data)

@private_bp.route('/api/geo/coords/<path:q>', methods=['GET'])
def geo_coords_path(q):
    category = request.args.get("category")
    if category and category not in ("place", "person"):
        return _standard_response("geo_coords_path", {"error": "category invalide"}, True, 400)
    res = _search_impl(q, category)
    if not res:
        return _standard_response("geo_coords_path", {"error": "Aucune correspondance"}, True, 404)
    coords = _geocode(res["address_text"])
    if not coords:
        return _standard_response("geo_coords_path", {"error": "Géocodage: aucun résultat"}, True, 502)
    data = {
        "name": res["name"],
        "category": res["category"],
        "address": res["address"],
        "address_text": res["address_text"],
        "coords": coords,
        "provider": "nominatim"
    }
    return _standard_response("geo_coords_path", data)

# --- Reverse ---
@private_bp.route('/api/geo/reverse', methods=['GET'])
def geo_reverse():
    try:
        lat = float(request.args.get("lat", ""))
        lon = float(request.args.get("lon", ""))
    except ValueError:
        return _standard_response("geo_reverse", {"error": "lat/lon invalides"}, True, 400)
    addr = _reverse(lat, lon)
    if not addr:
        return _standard_response("geo_reverse", {"error": "Reverse: aucun résultat"}, True, 502)
    return _standard_response("geo_reverse", {"address": addr, "provider": "nominatim"})

@private_bp.route('/api/geo/reverse/<lat>/<lon>', methods=['GET'])
def geo_reverse_path(lat, lon):
    try:
        latf = float(lat)
        lonf = float(lon)
    except ValueError:
        return _standard_response("geo_reverse_path", {"error": "lat/lon invalides"}, True, 400)
    addr = _reverse(latf, lonf)
    if not addr:
        return _standard_response("geo_reverse_path", {"error": "Reverse: aucun résultat"}, True, 502)
    return _standard_response("geo_reverse_path", {"address": addr, "provider": "nominatim"})
    
@private_bp.route('/api/map', methods=['GET'])
def serve_franche_comte_route():
    return render_template("./franche_comte_route.html")
# ------------------
# Register blueprint
#------------------

app.register_blueprint(private_bp)

#------------------
# Main
#------------------

if __name__ == '__main__':
    if not is_gunicorn:
        app.run(debug=True, port=12345, host="0.0.0.0")
