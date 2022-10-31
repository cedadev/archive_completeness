# Archive completeness

Scripts to work out how complete the discovery records are by comparing them to the FBI.

This works by having the following input
 - The list of catalogue records and their publication state.
 - A list of directories that can be safely ignored. e.g. /badc/cira/metadata

These two list should be mutually exclusive and not contain sub paths. 
This means /badc/cira/data and /badc/cira/data/netcdf should not be in the lists.

The algorithum for finding missing directories is to do a top down seach ot the FBI direcroies annotation them with the publication state, ignore or missing. Any directorry which have and  entry in the catalogue or ignore list is marked with the annotation. If there is no directory in the list, but entries do exist futher down the directory hiracrhy then the subdirectories are recursed into. And finally, if there is no directory in the list and no entries exist futher down the directory hiracrhy then the dirrectory is marked as missing. The net result is a list of missing directories at the higest point in the hireacrhy that can be descrided as missing.
 
Using the two input lists and the output missing list it is now possible to summerise the problem areas in terms of volume, number and collection. These summaries are then useed to prioritise actions to increase catalogue coverage.

