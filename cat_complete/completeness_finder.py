
from email.policy import default
import os
from typing import DefaultDict
from collections import OrderedDict
import click
from fbi_core import fbi_listdir
from tabulate import tabulate
from .get_fbi_sizes import get_size
from .get_catalogue_records import get_catalogue_record_paths
# report by number, vol, collections

class AnnotatedDir:
    def __init__(self, directory, annotation) -> None:
        self.directory = directory
        self.annotation = annotation
        collection_bits = directory.split("/")
        self.collection = "/".join(collection_bits[0:3])
    
    @property
    def vol(self):
        return get_size(self.directory)[0]

    @property
    def number(self):
        return get_size(self.directory)[1]        

    def __lt__(self, other):
        return self.directory < other.directory
    
    def __eq__(self, other):
        return self.directory == other.directory

    def is_child_path(self, other):
        if isinstance(other, AnnotatedDir):
            other = other.directory 
        return self.directory.startswith(other + "/") 

    def __str__(self):
        return f"{self.directory}|{self.annotation}"    

    __repr__ = __str__


class AnnotatedDirs:

    def __init__(self, cat_file, ignore_file, missing_file=None) -> None:
        self.ignore_file = ignore_file
        self.cat_file = cat_file
        self.missing_file = missing_file
        self.top_vol, self.top_number, self.total_vol, self.total_number = 0, 0, 0, 0
        self.ad = {}
      
        if missing_file is not None:
            self.read_path_list(missing_file, "missing")
        self.read_path_list(ignore_file, "ignore")

        for path, annotation in get_catalogue_record_paths(cat_file).items():
            self.ad[path] = AnnotatedDir(path, annotation)

    def read_path_list(self, filename, annotation):
        with open(filename) as fh:
            for line in fh.readlines():
                ignore_dir = line.strip().rstrip('/')
                self.ad[ignore_dir] = AnnotatedDir(ignore_dir, annotation)

    def has_subdirs(self, path):
        for ad_path in self.ad:
            if ad_path.startswith(path + "/"): 
                return True
        return False

    def find_annotation(self, path):
        if path in self.ad:
            return self.ad[path].annotation
        elif self.has_subdirs(path):
            return None
        else:
            return "MISSING"

    def save_missing(self, filename):
        with open(filename, "w") as fh:
            for annotateddir  in self.ad:
                if self.ad[annotateddir].annotation == "missing":
                    fh.write(f"{annotateddir}\n")

    def summary(self):
        vol_dict = DefaultDict(int)
        number_dict = DefaultDict(int)
        for directory in self.ad:
            annotateddir = self.ad[directory]
            vol_dict[annotateddir.annotation] += annotateddir.vol
            number_dict[annotateddir.annotation] += annotateddir.number
        vol_dict = OrderedDict(sorted(vol_dict.items(), key=lambda x: x[1], reverse=True))
        number_dict = OrderedDict(sorted(number_dict.items(), key=lambda x: x[1], reverse=True))
        return vol_dict, number_dict

    def summary2(self):
        vol_dict = DefaultDict(int)
        number_dict = DefaultDict(int)
        annotations = set()
        collections = set()
        for directory in self.ad:
            annotateddir = self.ad[directory]
            collection = annotateddir.collection
            annotation = annotateddir.annotation
            annotations.add(annotation)
            collections.add(collection)
            vol_dict[(annotation, collection)] += annotateddir.vol
            number_dict[(annotation, collection)] += annotateddir.number
        vol_dict[("missing", "TOP")] = self.top_vol
        number_dict[("missing", "TOP")] = self.top_number
        collections.add("TOP")

        collections = list(collections)
        collections.sort()
        
        header = ["Collection"]
        for annotation in annotations:
            header.append(annotation)

        number_list = []
        for collection in  collections:
            row = [collection]
            number_list.append(row)
            for annotation in annotations:
                if (annotation, collection) in number_dict:
                    row.append(number_dict[(annotation, collection)])
                else:
                    row.append(0)
        
        vol_dict = OrderedDict(sorted(vol_dict.items(), key=lambda x: x[1], reverse=True))
        number_dict = OrderedDict(sorted(number_dict.items(), key=lambda x: x[1], reverse=True))
        return vol_dict, number_dict, number_list, header

    def maketop(self):
        self.total_vol, self.total_number = get_size("/")
        self.top_vol, self.top_number = self.total_vol, self.total_number
        #self.top_vol, self.top_number = 0, 0
        for directory in self.ad:
            annotateddir = self.ad[directory]
            if self.has_subdirs(annotateddir.directory):
                print(f" ****** {annotateddir.directory} has sub dirs ? ******")
            self.top_vol -= annotateddir.vol
            self.top_number -= annotateddir.number

    def __str__(self):
        return f"{self.top_vol} {self.top_number}\n" + str(self.ad)

    def walk_the_tree(self, directory: str):
        subdir_records = fbi_listdir(directory, dirs_only=True)
        for subdir_record in subdir_records:
            subdir = subdir_record["path"]
            annotation = self.find_annotation(subdir)
            if annotation is None:   
                self.walk_the_tree(subdir)  
            else:
                print(subdir, annotation)
                if annotation == "MISSING":
                    self.ad[subdir] = AnnotatedDir(subdir, "missing")
                    

def printtable(primary, primary_label, primary_total, secondary, secondary_label, secondary_total):
    table = []
    print()
    print("sorted by number")
    cum_percent_prim, cum_percent_seco = 0, 0
    for annotation, collection in primary:
        if annotation in ("published", "removed", "citable", "old", "ignore"):
            continue
        prim_value = primary[(annotation, collection)]
        seco_value = secondary[(annotation, collection)]
        percent_prim = 100 * prim_value/primary_total
        percent_seco = 100 * seco_value/secondary_total
        cum_percent_prim += percent_prim
        cum_percent_seco += percent_seco
        if percent_prim < 0.00001:
            continue
        table.append([annotation, collection, percent_prim, cum_percent_prim, percent_seco, cum_percent_seco])
    print(tabulate(table[0:400], headers=["Annotation", "Collection", f"percent by {primary_label}", 
        f"Cum. percent by {primary_label}",  f"percent by {secondary_label}", f"Cum. percent by {secondary_label}"]))


@click.command("catalogue_coverage", context_settings={'show_default': True})
@click.option("--cat", type=click.Path(), 
              help="File with a json encoded dict of paths and record publication state.", 
              default="catalogue_record_paths_cache.json")
@click.option("--ignore", type=click.Path(), 
              help="File containing list of paths to ignore.", 
              default="ignore.txt")
@click.option("--missing", type=click.Path(), 
              help="Output file for missing paths.", 
              default="missing.txt")
def catalogue_coverage(cat, ignore, missing):
    ad = AnnotatedDirs(cat, ignore, missing_file=missing) 
    ad.maketop()
    
    vols, numbers, number_list, header = ad.summary2()

    printtable(numbers, "Number", ad.total_number, vols, "Volume", ad.total_vol)
    printtable(vols, "Volume", ad.total_vol, numbers, "Number", ad.total_number)

    table = []
    print()
    print("Missing  by Vol")
    for annotation in vols:
        number = numbers[annotation]
        vol = vols[annotation]
        table.append([annotation, number, 100*number/ad.total_number, vol, 100*vol/ad.total_vol])
    print(tabulate(table[0:100], headers=["Annotation", "number", "percent by number", "volume", "percent by Volume"]))

    vol = ad.top_vol
    number = ad.top_number
    print( number, 100*number/ad.total_number, vol, 100*vol/ad.total_vol)

    print()
    print(tabulate(number_list, headers=header))


@click.command("find_missing", context_settings={'show_default': True})
@click.option("--cat", type=click.Path(), 
              help="File with a json encoded dict of paths and record publication state.", 
              default="catalogue_record_paths_cache.json")
@click.option("--ignore", type=click.Path(), 
              help="File containing list of paths to ignore.", 
              default="ignore.txt")
@click.option("--missing", type=click.Path(), 
              help="Output file for missing paths.", 
              default="missing.txt")
def find_missing(cat, ignore, missing):
    ad = AnnotatedDirs(cat, ignore) 
    ad.walk_the_tree("/")
    ad.save_missing(missing)

 