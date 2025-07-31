import os
import json
import requests
import time

def get_catalogue_record_paths(cache_filename="catalogue_record_paths_cache.json", cache_ttl=24*3600):
    """Get catalogue record information from the moles API. Grabs all records from the catalogue and stores then in a cache JSON file."""
    
    # too detailed - crashes server
    # url = 'http://api.catalogue.ceda.ac.uk/api/v2/observations.json?limit=200'  
   
    # needs doing in one lump. pagination does not work.
    url = 'https://api.catalogue.ceda.ac.uk/api/v2/observations/?fields=uuid,result_field,title,publicationState&limit=1000'  
    
    if os.path.exists(cache_filename) and os.path.getmtime(cache_filename) > time.time() - cache_ttl:
        return json.load(open(cache_filename))
    
    paths = {}
    i = 0 
    while url is not None:
        r = requests.get(url=url)
        print(r)
        record_list = r.json()
        print(len(record_list["results"]))
        for record in record_list["results"]:
            i += 1
            # print(record)
            result_field = record["result_field"]
            if record["uuid"] == "bdade57677db14829c6cdaa1f3e937c9":
                print("****** FOUND bdade57677db14829c6cdaa1f3e937c9")
            # print(result_field)
            if result_field is None: 
                print(f"'{record['title']}' result_field is None")
                continue
            elif result_field["storageLocation"] != "internal": 
                print(f"'{record['title']}' result_field.storageLocation is {result_field['storageLocation']}")
                continue
            elif result_field["dataPath"] is None: 
                print(f"'{record['title']}' result_field.dataPath is None")
                continue

            path = result_field["dataPath"].rstrip("/")
            if path in paths:
                print(f"DUPLICATE ----- {path}")
            paths[path] = record["publicationState"]

           
        url = record_list["next"]
        print(len(paths), path, url, i) 

    json.dump(paths, open(cache_filename, "w"), indent=4)
    return paths

if __name__ == "__main__":
    x = get_catalogue_record_paths(cache_ttl=0)
    print(len(x))

