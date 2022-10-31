import os
import json
import requests
import time

def get_catalogue_record_paths(cache_filename="catalogue_record_paths_cache.json"):
    url = 'http://api.catalogue.ceda.ac.uk/api/v2/observations/?ordering=uuid'
    # url = 'http://api.catalogue.ceda.ac.uk/api/v1/observations.json'
    if os.path.exists(cache_filename) and os.path.getmtime(cache_filename) > time.time() - 24*3600:
        return json.load(open(cache_filename))

    paths = {}
    while url is not None:
        r = requests.get(url=url)
        record_list = r.json()
        for record in record_list["results"]:
            result_field = record["result_field"]
            if result_field is None: 
                path = f"'{record['title']}' result_field is None"
            if result_field["storageLocation"] != "internal": 
                print(f"'{record['title']}' result_field.storageLocation is {result_field['storageLocation']}")
                continue
            if result_field["dataPath"] is None: 
                print(f"'{record['title']}' result_field.dataPath is None")
                continue

            path = result_field["dataPath"].rstrip("/")
            paths[path] = record["publicationState"]

           
        url = record_list["next"]
        print(len(paths), path, url) 

    json.dump(paths, open(cache_filename, "w"), indent=4)
    return paths

if __name__ == "__main__":
    x = get_catalogue_record_paths()

