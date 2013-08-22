#!/localtemp/ab3744/babel/Python-2.7.3/bin/python2.7


import codecs
from glob import glob
from os.path import basename, isdir
from os import makedirs
#import cfg
import argparse

parser = argparse.ArgumentParser()
#parser.add_argument("-i", "--input", dest="input", default=[], action="append")
parser.add_argument("-o", "--output", dest="output")
parser.add_argument(dest="input", nargs="+")
options = parser.parse_args()


odirL = ['../txt.raw/train/', '../txt.raw/dev/']
typeL = ['training', 'dev']

for odir, type_ in zip(odirL, typeL):
    try:
        makedirs(odir)
    except:
        if not isdir(odir):
            raise

    for dir_ in [ 'conversational/%s/transcription/' % (type_),
                  'scripted/%s/transcription/' % (type_) ]:
        for in_ in glob(cfg.langPackRoot+dir_+'*.txt'):
	#for in_ in glob(cfg.langPackRoot+dir_+'*.txt.gz'):

            out = odir + basename(in_)
            with codecs.open(in_,'rb',encoding='utf-8') as inF, \
                    codecs.open(out,'wb',encoding='utf-8') as outF:
                uttX = 1
                state = 'TIME'
                for lineX, line in enumerate(inF):
                    if line.startswith('['):
                        if state == 'TXT':
                            print 'WARNING: Format error in %s at ' \
                                'line %d, assuming <no-speech>' % \
                                (in_, lineX+1)
                            print >> outF, '%04d <no-speech>' % (uttX)
                            uttX += 1
                            continue
                        state = 'TXT'
                        continue
                    if state != 'TXT':
                        msg = 'Format error in %s at line %d' % \
                            (in_, lineX+1)
                        raise ValueError, msg
                    state = 'TIME'
                    print >> outF, '%04d %s' % (uttX, line.strip())
                    uttX += 1
