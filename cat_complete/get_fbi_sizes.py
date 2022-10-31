import os
import json
import time
from fbi_core import archive_summary

cache_filename="fbi_size_cache.json"
size_cache = {}
if os.path.exists(cache_filename):
    if os.path.getmtime(cache_filename) > time.time() - 24*3600:
        size_cache = json.load(open(cache_filename))
    else:
        os.remove(cache_filename)


def save_size_cache():
    json.dump(size_cache, open(cache_filename, "w"))  

def get_size(path):
    """Get size and number for a path"""
    if path in size_cache:
        return size_cache[path]

    print(f"Getting size and number from FBI: {path} ... ", end="")
    summary = archive_summary(path, item_type="file")
    vol = summary["size_stats"]["sum"]
    types = dict(summary["types"])
    if "file" in types:
        number = types["file"]
    else:
        number = 0
    print(f"{vol}, {number}")
    size_cache[path] = (vol, number)
    save_size_cache()
    return vol, number
