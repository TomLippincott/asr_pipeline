import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--tt", dest="train_transcript")
parser.add_argument("--td", dest="train_dictionary")
parser.add_argument("--tv", dest="train_vocab")
parser.add_argument("--dt", dest="dev_transcript")
parser.add_argument("--dd", dest="dev_dictionary")
parser.add_argument("--dv", dest="dev_vocab")

parser.add_argument("--ibm", dest="ibm")
options = parser.parse_args()

train_dict = set([l.strip() for l in open(options.train_dictionary)])
dev_dict = set([l.strip() for l in open(options.dev_dictionary)])


#for t in train_dict:
#    dev_dict.add(t)



not_in_train = set([t for t in dev_dict if t not in train_dict])

ibm_dict = set()
for l in open(options.ibm):
    ibm_dict.add(l.strip().split("(")[0])

print len(train_dict), len(dev_dict), len(ibm_dict), len(not_in_train)

print len(not_in_train.intersection(ibm_dict))

#print not_in_train
#data = {}
#for d in options.dictionaries:
#    data[d] = set()
#    for l in open(d):
#        data[d].add(l.split("(")[0])
#    print d, len(data[d])
