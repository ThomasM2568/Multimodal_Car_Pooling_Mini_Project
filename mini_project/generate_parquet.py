# -*- coding: utf-8 -*-
import osmium
import pandas as pd
import os

input_file = "franche-comte-250929.osm.pbf"
parquet_file = "highways.parquet"

if not os.path.exists(parquet_file):
    print(f"'{parquet_file}' not found. Parsing OSM file...")

    class HighwayHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes_data = []
            self.counter = 0  # Only to provide status

        def way(self, w):
            if 'highway' in w.tags:
                coords = [tuple((n.lat, n.lon)) for n in w.nodes if n.location.valid()]
                if len(coords) >= 2:
                    self.nodes_data.append({'id': w.id, 'highway': w.tags['highway'], 'nodes': coords})
            self.counter += 1
            if self.counter % 10000 == 0:
                print(f"Parsed {self.counter} ways...")

        def close(self):
            print(f"Total 'highways' parsed: {self.counter}")

    handler = HighwayHandler()  # <------ FIXED: no argument here
    handler.apply_file(input_file, locations=True)
    handler.close()

    df = pd.DataFrame(handler.nodes_data)
    df.to_parquet(parquet_file, engine='pyarrow', index=False)
    print(f"Saved highways parquet to: {parquet_file}")
else:
    print(f"Found '{parquet_file}'. No parsing necessary.")
