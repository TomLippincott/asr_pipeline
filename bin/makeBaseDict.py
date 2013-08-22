import codecs
import locale
import os
import os.path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--locale", dest="locale")
parser.add_argument("-r", "--skip_roman", dest="skip_roman", default=False, action="store_true")
parser.add_argument("-i", "--input_lexicons", dest="input_lexicons", default=[], action="append")

parser.add_argument("-d", "--dictionary", dest="dictionary")
parser.add_argument("-p", "--phone_symbols", dest="phone_symbols")
parser.add_argument("-t", "--tags", dest="tags")
options = parser.parse_args()



# set the locale for sorting and getting consistent case
locale.setlocale(locale.LC_ALL, options.locale)

# create the output directory
#try:
#    os.makedirs('../input')
#except:
#    if not os.path.isdir('../input'):
#        raise

# convert BABEL SAMPA pronunciations to attila format
#
# In this version the primary stress ("), secondary stress (%),
# syllable boundary (.), and word boundary within compound (#) marks
# are simply stripped out.  We may want to try including this
# information in the form of tags in some variants.
#
def attilapron(u, pnsp):
    skipD = frozenset(['"', '%', '.', '#'])
    phoneL = []
    for c in u.encode('utf-8').split():
        if c in skipD:
            continue
        pnsp.add(c)
        phoneL.append(c)
    phoneL.append('[ wb ]')
    if len(phoneL) > 2:
        phoneL.insert(1, '[ wb ]')
    return ' '.join(phoneL)

# Pronunciations for the BABEL standard tags, silence, and the start
# and end tokens
nonlex = [ ['<UNINTELLIGIBLE>', set(['REJ [ wb ]'])],
           ['<FOREIGN>',   set(['REJ [ wb ]'])],
           ['<LAUGH>',     set(['VN [ wb ]'])],
           ['<COUGH>',     set(['VN [ wb ]'])],
           ['<BREATH>',    set(['NS [ wb ]', 'VN [ wb ]'])],
           ['<LIPSMACK>',  set(['NS [ wb ]'])],
           ['<CLICK>',     set(['NS [ wb ]'])],
           ['<RING>',      set(['NS [ wb ]'])],
           ['<DTMF>',      set(['NS [ wb ]'])],
           ['<INT>',       set(['NS [ wb ]'])],
           ['<NO-SPEECH>', set(['SIL [ wb ]'])],
           ['~SIL',        set(['SIL [ wb ]'])], 
           ['<s>',         set(['SIL [ wb ]'])],
           ['</s>',        set(['SIL [ wb ]'])], ]

# read in the dictionaries, normalizing the case of the word tokens to
# all lowercase.  Normalize <hes> to <HES> so the LM tools don't think
# it is an XML tag.
voc = {}
pnsp = set()
for name in options.input_lexicons:
#[ 'conversational/reference_materials/lexicon.txt',
#              'scripted/reference_materials/lexicon.txt' ]:
    with codecs.open(name,'rb',encoding='utf-8') as f:
        for line in f:
            pronL = line.strip().split(u'\t')
            token = pronL.pop(0).lower()
            if options.skip_roman:
                pronL.pop(0)
            if token == '<hes>':
                token = '<HES>'
            prons = voc.setdefault(token, set())
            prons.update([attilapron(p,pnsp) for p in pronL])

# need a collation function as a workaround for a Unicode bug in
# locale.xtrxfrm (bug is fixed in Python 3.0)
def collate(s):
    return locale.strxfrm(s.encode('utf-8'))

# write the dictionary, and collect the phone set
with open(options.dictionary, 'w') as f:
    for token in sorted(voc.iterkeys(),key=collate):
        for pronX, pron in enumerate(voc[token]):
            print >> f, '%s(%02d) %s' % (token.encode('utf-8'), 1+pronX,
                                         pron)

    for elt in nonlex:
        token = elt[0]
        for pronX, pron in enumerate(elt[1]):
            print >> f, '%s(%02d) %s' % (token, 1+pronX, pron)
    
# generate and write a list of phone symbols (pnsp)
with open(options.phone_symbols,'w') as f:
    for pn in sorted(pnsp):
        print >> f, pn
    print >> f, 'SIL'
    print >> f, 'NS'
    print >> f, 'VN'
    print >> f, 'REJ'
    print >> f, '|'
    print >> f, '-1'

# generate and write a list of tags
with open(options.tags, 'w') as f:
    print >> f, 'wb'
