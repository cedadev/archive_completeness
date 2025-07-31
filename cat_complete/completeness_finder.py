
from email.policy import default
import os
from typing import DefaultDict
from collections import OrderedDict
import click
import re
import json
from fbi_core import fbi_listdir
from tabulate import tabulate
from .get_fbi_sizes import get_size
from .get_catalogue_records import get_catalogue_record_paths
# report by number, vol, collections

ok_annotations = ["ignore", "ignore_pattern", "citable", "published", "removed", "old"]

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

    def __init__(self, output_dir) -> None:
        self.output_dir = output_dir
        self.ignore_patterns = []
        self.top_vol, self.top_number, self.total_vol, self.total_number = 0, 0, 0, 0
        self.ad = {}
        self.read_ignore_patterns_file()

    # self.read_path_list(missing_file, "missing")  

    def annotate_catalogue_paths(self):
        """fill annotations from catalogue"""
        cat_file = os.path.join(self.output_dir, "completeness_catalogue_record_paths_cache.json")
        for path, annotation in get_catalogue_record_paths(cat_file).items():
            self.ad[path] = AnnotatedDir(path, annotation)

    def annotate_ignore_paths(self):
        """fill annotations from ignore file"""
        ignore_file = os.path.join(self.output_dir, "completeness_ignore_paths.txt")
        if os.path.exists(ignore_file):
            with open(ignore_file) as fh:
                for line in fh.readlines():
                    ignore_dir = line.strip().rstrip('/')
                    self.ad[ignore_dir] = AnnotatedDir(ignore_dir, "ignore")
        else: 
            print(f"Add paths to {ignore_file} to ignore them")

    def read_ignore_patterns_file(self):
        ignore_pats_file = os.path.join(self.output_dir, "completeness_ignore_patterns.txt")
        if os.path.exists(ignore_pats_file):
            with open(ignore_pats_file) as fh:
                for line in fh.readlines():
                    pattern = line.strip()
                    if pattern == "": 
                        continue
                    self.ignore_patterns.append(re.compile(pattern))
        else:
            print (f"Add regex patterns to {ignore_pats_file} to ignore paths that match.")

    def has_subdirs(self, path):
        for ad_path in self.ad:
            if ad_path.startswith(path + "/"): 
                return True
        return False

    def is_readme_only(self, path):
        """Is probably just readmes and links"""
        vol, num = get_size(path)
        if num < 4 and vol < 10000: 
            return True
        return False

    def printsubdirs(self, path):
        for ad_path in self.ad:
            if ad_path.startswith(path + "/"): 
                print(ad_path, self.ad[ad_path].annotation)
        return False

    def in_ignore_patterns(self, path):
        for pattern in self.ignore_patterns:
            if pattern.search(path):
                return True
        return False

    def find_annotation(self, path):
        """Find the annotation that belongs to the path"""
        if path in self.ad:
            return self.ad[path].annotation     # path already in annotations
        elif self.in_ignore_patterns(path):
            self.ad[path] = AnnotatedDir(path, "ignore_pattern")
            return "ignore_pattern"             # path in ignore list
        elif self.has_subdirs(path):
            return None                         # there are annnotated paths below this, keep going...
        elif self.is_readme_only(path):
            self.ad[path] = AnnotatedDir(path, "readme_only")
            return "readme_only" 
        else:
            self.ad[path] = AnnotatedDir(path, "missing")
            return "missing"                    # otherwise it's missing

    def walk_the_tree(self, directory: str):
        subdir_records = fbi_listdir(directory, dirs_only=True)
        for subdir_record in subdir_records:
            subdir = subdir_record["path"]
            annotation = self.find_annotation(subdir)
            if annotation is None:   
                self.walk_the_tree(subdir)  
            else:
                print(subdir, annotation)

    def save_output(self):
        """Save the outputs fromm analyses"""
        with open(os.path.join(self.output_dir, "completeness_missing.txt"), "w") as fh:
            for annotateddir  in self.ad:
                if self.ad[annotateddir].annotation == "missing":
                    fh.write(f"{annotateddir}\n")
        with open(os.path.join(self.output_dir, "completeness_ignore_patterns_output.txt"), "w") as fh:
            for annotateddir  in self.ad:
                if self.ad[annotateddir].annotation == "ignore_pattern":
                    fh.write(f"{annotateddir}\n")
        with open(os.path.join(self.output_dir, "completeness_annotations.txt"), "w") as fh:
            for annotateddir  in self.ad:
                fh.write(f"{annotateddir} {self.ad[annotateddir].collection} {self.ad[annotateddir].annotation}\n")

    def load_annotations(self):
        with open(os.path.join(self.output_dir, "completeness_annotations.txt")) as fh:
            for line in fh.readlines():
                line = line.strip()
                if line == "":
                    continue
                bits = line.split(" ")
                directory = bits[0]
                collection = bits[1]
                annotation = " ".join(bits[2:])
                self.ad[directory] = AnnotatedDir(directory, annotation)

    def find_missing(self):
        """Analyses the fbi to find where there are no catalogue records"""
        self.annotate_catalogue_paths()
        self.annotate_ignore_paths()
        self.walk_the_tree("/")
        self.save_output()

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

    def summary3(self):
        vol_dict = DefaultDict(int)
        number_dict = DefaultDict(int)

        header = ["Annotation", "Number", "Number %", "Volume (TB)", "Volume %"]

        for directory in self.ad:
            annotateddir = self.ad[directory]
            annotation = annotateddir.annotation
            number_dict[annotation] += annotateddir.number
            vol_dict[annotation] += annotateddir.vol
            
        table = []  
        ok_number, ok_vol, not_ok_number, not_ok_vol = 0, 0, 0, 0
        for annotation in number_dict:
            if annotation in ok_annotations:
                ok_number += number_dict[annotation]
                ok_vol += vol_dict[annotation]
            else:
                not_ok_number += number_dict[annotation]
                not_ok_vol += vol_dict[annotation]
        not_ok_number += self.top_number
        not_ok_vol += self.top_vol

        table.append(["OK states", ok_number, 100*ok_number/self.total_number, ok_vol* 1e-12, 100*ok_vol/self.total_vol])
        table.append(["Not OK states", not_ok_number, 100*not_ok_number/self.total_number, not_ok_vol* 1e-12, 100*not_ok_vol/self.total_vol])
        print(tabulate(table, headers=header))
        print()

        table = []    
        for annotation in number_dict:
            number = number_dict[annotation]
            vol = vol_dict[annotation]
            table.append([annotation, number, 100*number/self.total_number, vol* 1e-12, 100*vol/self.total_vol])
        table.append(["TOP", self.top_number, 100*self.top_number/self.total_number, 
                      self.top_vol* 1e-12, 100*self.top_vol/self.total_vol])

        print(tabulate(table, headers=header))

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
                self.printsubdirs(directory)
                print(f" ****** {annotateddir.directory} has sub dirs ? ******")
            self.top_vol -= annotateddir.vol
            self.top_number -= annotateddir.number

    def __str__(self):
        return f"{self.top_vol} {self.top_number}\n" + str(self.ad)

                    

def printtable(primary, primary_label, primary_total, secondary, secondary_label, secondary_total):
    table = []
    print()
    print("sorted by number")
    cum_percent_prim, cum_percent_seco = 0, 0
    for annotation, collection in primary:
        if annotation in ok_annotations:
            continue
        prim_value = primary[(annotation, collection)]
        seco_value = secondary[(annotation, collection)]
        percent_prim = 100 * prim_value/primary_total
        percent_seco = 100 * seco_value/secondary_total
        cum_percent_prim += percent_prim
        cum_percent_seco += percent_seco
        if percent_prim < 0.03:
            continue
        table.append([annotation, collection, percent_prim, cum_percent_prim, percent_seco, cum_percent_seco])
    print(tabulate(table[0:400], headers=["Annotation", "Collection", f"percent by {primary_label}", 
        f"Cum. percent by {primary_label}",  f"percent by {secondary_label}", f"Cum. percent by {secondary_label}"]))


@click.command("catalogue_coverage", context_settings={'show_default': True})
@click.option("-d", "--working-dir", type=click.Path(), 
              help="Path to directory where files are output.", 
              default=".")
def catalogue_coverage(working_dir):
    """Use the missing, ignored and catalogue records to report on coverage."""
    ad = AnnotatedDirs(working_dir) 
    ad.load_annotations()
    ad.maketop()
    
    vols, numbers, number_list, header = ad.summary2()

    printtable(numbers, "Number", ad.total_number, vols, "Volume", ad.total_vol)
    printtable(vols, "Volume", ad.total_vol, numbers, "Number", ad.total_number)

    #print()
    #print(tabulate(number_list, headers=header))
    print()
    ad.summary3()


@click.command("find_missing", context_settings={'show_default': True})
@click.option("-d", "--working-dir", type=click.Path(), 
              help="Path to directory where files are output.", 
              default=".")
def find_missing(working_dir):
    """Find the missing directories that need a catalogue record."""
    ad = AnnotatedDirs(working_dir)
    ad.find_missing() 


 
