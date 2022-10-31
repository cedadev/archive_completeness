import os
import json
import requests
import time

def get_catalogue_record_paths():
    url = 'http://api.catalogue.ceda.ac.uk/api/v1/observations.json'
    cache_filename = "catalogue_record_paths_cache.json"
    if os.path.exists(cache_filename) and os.path.getmtime(cache_filename) > time.time() - 24*3600:
        return json.load(open(cache_filename))

    print("f")
    paths = {}
    while url is not None:
        r = requests.get(url=url)
        record_list = r.json()
        for record in record_list["results"]:
            result_field = record["result_field"]
            if result_field is None: 
                print(f"'{record['title']}' result_field is None")
                continue
            if result_field["storageLocation"] != "internal": 
                print(f"'{record['title']}' result_field.storageLocation is {result_field['storageLocation']}")
                continue
            if result_field["dataPath"] is None: 
                print(f"'{record['title']}' result_field.dataPath is None")
                continue

            path = result_field["dataPath"].rstrip("/")
            paths[path] = record["publicationState"]

        print(len(paths), path)    
        url = record_list["next"]

    json.dump(paths, open(cache_filename, "w"), indent=4)
    return paths

if __name__ == "__main__":
    print("fff")
    x = get_catalogue_record_paths()

