import re
import sys
from functools import partial

pattern = re.compile("/(ba|neo)dc/(?P<collection>[\w\d_-]+)/.*\|missing\|")

with open(sys.argv[1]) as fh:
    lines = fh.readlines()

for line in lines:
    line  =line.strip()
    m = pattern.match(line)
    
    if m:
        collection = m.group(2)
        print(line.replace('|missing|', f"|missing_{collection}|"))
    else:
        print(line)