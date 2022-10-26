
import os
from typing import DefaultDict
from collections import OrderedDict
import click
from fbi_core import fbi_listdir
from tabulate import tabulate
from .get_fbi_sizes import get_size
from .get_catalogue_records import get_catalogue_record_paths
import json
# report by number, vol, collections

class AnnotatedDir:
    def __init__(self, directory, annotation) -> None:
        self.directory = directory
        self.annotation = annotation
        collection_bits = directory.split("/")
        print(collection_bits)
        if len(collection_bits) > 2:  
            self.collection = collection_bits[2]
        else:
            self.collection = collection_bits[1]
    
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
        return f"{self.directory}|{self.annotation}|{self.vol}|{self.number}"    

    __repr__ = __str__

class AnnotatedDirs:

    def __init__(self, ignore_file) -> None:
        self.ignore_file = ignore_file
        self.top_vol, self.top_number, self.total_vol, self.total_number = 0, 0, 0, 0
        self.ad = {}
        for path in get_catalogue_record_paths():
            self.ad[path] = AnnotatedDir(path, "catalogue")

        with open(self.ignore_file) as fh:
            for line in fh.readlines():
                bits = line.split("|")
                vol, number = None, None
                if len(bits) == 2: 
                    directory = bits[0].strip()
                    annotation = bits[1].strip()
                    annotateddir = AnnotatedDir(directory, annotation)
                if len(bits) == 4: 
                    directory = bits[0].strip()
                    annotation = bits[1].strip()
                    vol, number = int(float(bits[2].strip())), int(bits[3].strip()) 
                    annotateddir = AnnotatedDir(directory, annotation, vol=vol, number=number)
                self.add(annotateddir)
        
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

    def add(self, annotateddir_to_add):
        print("In add")
        i = 0 
        for i, annotateddir in enumerate(self.ad):
            if annotateddir.directory == annotateddir_to_add.directory:
                print("skip", i, annotateddir.directory, annotateddir_to_add.directory)
                return 
            if annotateddir.directory > annotateddir_to_add.directory:
                break
        print("add", i, annotateddir_to_add.directory)    
        self.ad.insert(i, annotateddir_to_add)

    def save(self, filename):
        with open(filename, "w") as fh:
            for annotateddir  in self.ad:
                fh.write(f"{annotateddir}\n")

    def summary(self):
        vol_dict = DefaultDict(int)
        number_dict = DefaultDict(int)
        for annotateddir  in self.ad:
            vol_dict[annotateddir.annotation] += annotateddir.vol
            number_dict[annotateddir.annotation] += annotateddir.number
        vol_dict = OrderedDict(sorted(vol_dict.items(), key=lambda x: x[1], reverse=True))
        number_dict = OrderedDict(sorted(number_dict.items(), key=lambda x: x[1], reverse=True))
        return vol_dict, number_dict

    def maketop(self):
        self.total_vol, self.total_number = get_size("/")
        self.top_vol, self.top_number = self.total_vol, self.total_number
        #self.top_vol, self.top_number = 0, 0
        for annotateddir in self.ad:
            annotateddir.update_size()
            self.top_vol -= annotateddir.vol
            self.top_number -= annotateddir.number

    def __str__(self):
        return f"{self.top_vol} {self.top_number}\n" + str(self.ad)

    def find_annotation(self, path):
        for annotateddir  in self.ad:
            if path == annotateddir.directory:
                return annotateddir.annotation
            if annotateddir.is_child_path(path):
                return None
        return "MISSING"

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
                    self.add(AnnotatedDir(subdir, "missing"))
 

@click.command()
@click.argument("filename", nargs=1)
@click.option("--path", "-P", type=click.Path(), default="/")
def main(filename, path):
    ad = AnnotatedDirs(filename) 
    print(ad)
    # ad.walk_the_tree(path)
    ad.maketop()
    print(ad)
    vols, numbers = ad.summary()
    ad.save(filename + ".out")

    table = []
    print()
    print("Missing  by number")
    for annotation in numbers:
        number = numbers[annotation]
        vol = vols[annotation]
        table.append([annotation, number, 100*number/ad.total_number, vol, 100*vol/ad.total_vol])
    print(tabulate(table[0:20], headers=["Annotation", "number", "percent by number", "volume", "percent by Volume"]))

    table = []
    print()
    print("Missing  by Vol")
    for annotation in vols:
        number = numbers[annotation]
        vol = vols[annotation]
        table.append([annotation, number, 100*number/ad.total_number, vol, 100*vol/ad.total_vol])
    print(tabulate(table[0:20], headers=["Annotation", "number", "percent by number", "volume", "percent by Volume"]))

    vol = ad.top_vol
    number = ad.top_number
    print( number, 100*number/ad.total_number, vol, 100*vol/ad.total_vol)