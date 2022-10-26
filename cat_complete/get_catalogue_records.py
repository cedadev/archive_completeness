import os
import json
import requests
import time

def get_catalogue_record_paths():
    url = 'http://api.catalogue.ceda.ac.uk/api/v1/observations.json'
    cache_filename = "catalogue_record_paths_cache.json"
    if os.path.exists(cache_filename) and os.path.getmtime(cache_filename) > time.time() - 24*3600:
        return json.load(open(cache_filename))

    paths = []
    while url is not None:
        r = requests.get(url=url)
        record_list = r.json()
        for record in record_list["results"]:
            result_field = record["result_field"]
            if result_field is None: continue
            if result_field["storageLocation"] != "internal": continue
            if result_field["dataPath"] is None: continue
            paths.append(result_field["dataPath"].rstrip("/"))

        print(len(paths), paths[-1])    
        url = record_list["next"]

    paths.sort()
    print(paths)
    json.dump(paths, open(cache_filename, "w"))
    return paths

if __name__ == "__main__":
    x = get_catalogue_record_paths()
    print(x)
