import requests
import time
import json

# Données JSON initiales
data = {
    "places": [
        {"name": "UFR STGI", "address": {"street": "4 Place Tharradin", "postal_code": "25200", "city": "Montbéliard", "country": "France"}},
        {"name": "Université de Belfort Louis NEEL", "address": {"street": "2 rue Chantereine", "postal_code": "90000", "city": "Belfort", "country": "France"}},
        {"name": "Pub O'Brian", "address": {"street": "13 Place du Général de Gaulle", "postal_code": "25200", "city": "Montbéliard", "country": "France"}},
        {"name": "Le Moulin Rouge", "address": {"street": "1 rue de la Croisée", "postal_code": "25400", "city": "Taillecourt", "country": "France"}}
    ],
    "intermediary": [
        {"name": "Grand Frais", "address": {"street": "3 Rue au Fol", "postal_code": "25420", "city": "Voujeaucourt", "country": "France"}},
        {"name": "Musée de L'Aventure Peugeot", "address": {"street": "Carr de l'Europe", "postal_code": "25600", "city": "Sochaux", "country": "France"}},
        {"name": "Stade Auguste-Bonal", "address": {"street": "2 Imp. de la Forge", "postal_code": "25200", "city": "Montbéliard", "country": "France"}},
        {"name": "au konbini", "address": {"street": "1 Rue du Stratégique C.C AUCHAN", "postal_code": "90160", "city": "Bessoncourt", "country": "France"}}
    ]
}

def format_address(addr):
    """Combine les champs d'adresse non vides en texte pour Nominatim"""
    return ", ".join(str(v) for v in [addr.get("street"), addr.get("postal_code"), addr.get("city"), addr.get("country")] if v)

def get_coords(address_text):
    """Récupère les coordonnées GPS via Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address_text,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
        "countrycodes": "fr"
    }
    headers = {"User-Agent": "my-app/1.0 (email@example.com)"}
    #time.sleep(1)  # éviter de spammer l'API
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    if data:
        return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    return None

# Génération d'un nouveau JSON avec coords
output_data = {}

for category in ["places", "intermediary"]:
    output_data[category] = []
    for item in data.get(category, []):
        name = item["name"]
        addr_text = format_address(item["address"])
        coords = get_coords(addr_text)
        output_data[category].append({
            "name": name,
            "address": coords  # remplace l'adresse par les coordonnées
        })
        print(f"{name}: {coords}")

# Sauvegarde en fichier JSON si besoin
with open("coords_output.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print("\nToutes les coordonnées ont été récupérées et sauvegardées dans coords_output.json")

