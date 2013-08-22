import argparse

parser = argparse.ArgumentParser()
#parser.add_argument("-A", "--inputA", dest="inputA")
#parser.add_argument("-B", "--inputB", dest="inputB")
#parser.add_argument("-o", "--output", dest="output")
parser.add_argument("dictionaries", nargs="+")
options = parser.parse_args()

data = {}
for d in options.dictionaries:
    data[d] = set()
    for l in open(d):
        data[d].add(l.split("(")[0])
    print d, len(data[d])
