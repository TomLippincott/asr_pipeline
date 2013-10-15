from SCons.Builder import Builder
from SCons.Action import Action
from SCons.Subst import scons_subst
import re
from glob import glob
from functools import partial
import logging
import os.path
import os
import cPickle as pickle
import math
import xml.etree.ElementTree as et
import gzip
import subprocess
import shlex
import time
import shutil
import tempfile
import arpabo
import codecs
import locale




def meta_open(file_name, mode="r"):
    """
    Convenience function for opening a file with gzip if it ends in "gz", uncompressed otherwise.
    """
    if os.path.splitext(file_name)[1] == ".gz":
        return gzip.open(file_name, mode)
    else:
        return open(file_name, mode)

def run_command(cmd, env={}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, data=None):
    """
    Simple convenience wrapper for running commands (not an actual Builder).
    """
    if isinstance(cmd, basestring):
        cmd = shlex.split(cmd)
    logging.info("Running command: %s", " ".join(cmd))
    process = subprocess.Popen(cmd, env=env, stdin=stdin, stdout=stdout, stderr=stderr)
    if data:
        out, err = process.communicate(data)
    else:
        out, err = process.communicate()
    return out, err, process.returncode == 0


def dictionary_to_vocabulary(target, source, env):
    with meta_open(source[0].rstr()) as ifd:
        d = arpabo.Dictionary(ifd)
    with meta_open(target[0].rstr(), "w") as ofd:
        ofd.write(d.format_vocabulary())
    return None

def appen_to_attila(target, source, env):
    # set the locale for sorting and getting consistent case
    locale.setlocale(locale.LC_ALL, source[-1].read())

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
            #c = cfg.p2p.get(c,c) TODO
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

    # Get the right dictionaries
    dictL = [x.rstr() for x in source[:-1]]

    # read in the dictionaries, normalizing the case of the word tokens to
    # all lowercase.  Normalize <hes> to <HES> so the LM tools don't think
    # it is an XML tag.
    voc = {}
    pnsp = set()
    for name in dictL:
        with codecs.open(name,'rb',encoding='utf-8') as f:
            for line in f:
                pronL = line.strip().split(u'\t')
                token = pronL.pop(0).lower()
                #if cfg.skipRoman:
                #    pronL.pop(0)
                if token == '<hes>':
                    token = '<HES>'
                prons = voc.setdefault(token, set())
                prons.update([attilapron(p,pnsp) for p in pronL])

    # need a collation function as a workaround for a Unicode bug in
    # locale.xtrxfrm (bug is fixed in Python 3.0)
    def collate(s):
        return locale.strxfrm(s.encode('utf-8'))

    odict, opnsp, otags = [x.rstr() for x in target]

    # write the dictionary, and collect the phone set
    with open(odict, 'w') as f:
        for token in sorted(voc.iterkeys(),key=collate):
            for pronX, pron in enumerate(voc[token]):
                f.write("%s(%02d) %s\n" % (token.encode('utf-8'), 1+pronX, pron))

        for elt in nonlex:
            token = elt[0]
            for pronX, pron in enumerate(elt[1]):
                f.write("%s(%02d) %s\n" % (token, 1+pronX, pron))

    # generate and write a list of phone symbols (pnsp)
    with open(opnsp, 'w') as f:
        for pn in sorted(pnsp):
            f.write("%s\n" % pn)
        f.write("\n".join(["SIL", "NS", "VN", "REJ", "|", "-1"]) + "\n")

    # generate and write a list of tags
    with open(otags,'w') as f:
        f.write("wb\n")
    return None

#
# Language Model
#

def ibm_train_language_model(target, source, env):
    text_file = source[0].rstr()
    vocab_file = source[1].rstr()
    n = source[2].read()

    # first create count files
    temp_dir = tempfile.mkdtemp()
    prefix = os.path.join(temp_dir, "temp")
    cmd = "${ATTILA_PATH}/tools/lm_64/CountNGram -n %d %s %s %s" % (n, text_file, vocab_file, prefix)
    out, err, success = run_command(env.subst(cmd))

    # build LM
    lm = ".".join(target[0].rstr().split(".")[0:-2])
    cmd = "${ATTILA_PATH}/tools/lm_64/BuildNGram.sh -n %d -arpabo %s %s" % (n, prefix, lm)
    out, err, success = run_command(env.subst(cmd), env={"SFCLMTOOLS" : env.subst("${ATTILA_PATH}/tools/lm_64")})

    # clean up
    for i in range(1, n + 1):
        os.remove("%s.count.%d" % (prefix, i))
    os.remove("%s.count.check" % (prefix))
    os.rmdir(temp_dir)
    return None

def train_pronunciation_model(target, source, env):
    """
    g2p.py --train - --devel 5% --model test.model2 --ramp-up --write-model test.model3
    """
    train_fname = source[0].rstr()
    dev_percent = source[1].read()
    if len(source) == 3:
        previous = source[2].rstr()
        cmd = "${SEQUITUR_PATH}/bin/g2p.py --train - --devel %d%% --write-model %s --ramp-up --model %s" % (dev_percent, target[0].rstr(), previous)        
    else:
        cmd = "${SEQUITUR_PATH}/bin/g2p.py --train - --devel %d%% --write-model %s" % (dev_percent, target[0].rstr())
    with open(train_fname) as ifd:
        data = "\n".join([re.sub(r"^(\S+)\(\d+\) (\S+) \[ wb \] (.*) \[ wb \]$", r"\1 \2 \3", line.strip()) for line in ifd if "REJ" not in line and line[0] != "<" and "SIL" not in line])
        #print data
        out, err, success = run_command(env.subst(cmd), env={"PYTHONPATH" : env.subst("${SEQUITUR_PATH}/lib/python2.7/site-packages")}, data=data)
        if not success:
            return err
        else:
            return None

def transcript_vocabulary(target, source, env):
    """
    Input: list of transcript files
    Output: sorted vocabulary file
    """
    words = set()
    for f in source:
        with meta_open(f.rstr()) as ifd:
            words = words.union(set(sum([[word.strip().lower() for word in line.split() if not word[0] == "<"] for line in ifd if not re.match(r"^\[\d+\.\d+\]$", line)], [])))
    with meta_open(target[0].rstr(), "w") as ofd:
        ofd.write("\n".join(sorted(words)))
    return None

def missing_vocabulary(target, source, env):
    with meta_open(source[0].rstr()) as lm_fd, meta_open(source[1].rstr()) as dict_fd, meta_open(target[0].rstr(), "w") as new_dict:
        dict_words = {}
        for l in dict_fd:
            if "REJ" not in l:
                m = re.match(r"^(.*)\(\d+\) (.*)$", l)
                word, pron = m.groups()
                dict_words[word] = dict_words.get(pron, []) + [pron.replace("[ wb ]", "")]
        lm_words = set([m.group(1) for m in re.finditer(r"^\-\d+\.\d+ (\S+) \-\d+\.\d+$", lm_fd.read(), re.M)])
        for word, prons in dict_words.iteritems():
            if word not in lm_words:
                for pron in prons:
                    new_dict.write("%s %s\n" % (word, pron))
    return None


def augment_language_model(target, source, env):
    """
    Input: old language model, old dictionary, new pronunciations
    Output: new language model, new vocab, new dictionary
    """
    from arpabo import Arpabo, Dictionary
    old_lm = Arpabo(meta_open(source[0].rstr()))
    old_dict = Dictionary(meta_open(source[1].rstr()))
    new_prons = Dictionary(meta_open(source[2].rstr()))
    wt = source[3].read()

    logging.info("Old LM: %s", old_lm)
    logging.info("Old Dictionary: %s", old_dict)
    logging.info("Words to add: %s", new_prons)

    old_dict.add_entries(new_prons)
    old_lm.add_unigrams(new_prons.get_words(), wt)

    logging.info("New LM: %s", old_lm)
    logging.info("New Dictionary: %s", old_dict)

    with meta_open(target[0].rstr(), "w") as new_lm, meta_open(target[1].rstr(), "w") as new_vocab, meta_open(target[2].rstr(), "w") as new_dict:
        new_lm.write(old_lm.format())
        new_vocab.write(old_dict.format_vocabulary() + "\n")
        new_dict.write(old_dict.format_dictionary() + "\n")

    return None

def augment_language_model_emitter(target, source, env):
    """
    Input: either a single dictionary, or something else
    Output: given a dictionary, set up the appropriate dependencies, otherwise pass through
    """
    # if there's more than one source, or it isn't a Python value, don't modify anything
    if len(source) != 1:
        return target, source
    else:
        try:
            config = source[0].read()
        except:
            return target, source
        base_path = env.get("BASE", "work")
        new_targets = [os.path.join(base_path, x % (config["NAME"])) for x in ["%s_lm.arpabo.gz", "%s_vocab.txt", "%s_dict.txt"]]
        new_sources = [config[x] for x in ["OLD_LANGUAGE_MODEL_FILE", "OLD_DICTIONARY_FILE", "NEW_DICTIONARY_FILE"]] + [env.Value(config["PROBABILITY_MASS"])]
        return new_targets, new_sources


def augment_language_model_from_babel(target, source, env):
    """
    """
    (tnew_fid, tnew), (tdict_fid, tdict), (tlm_fid, tlm) = [tempfile.mkstemp() for i in range(3)]
    (tnewdict_fid, tnewdict), (tnewlm_fid, tnewlm) = [tempfile.mkstemp() for i in range(2)]
    bad = "\xc3\xb1"
    words = {}
    for m in re.finditer(r"^(.*)\(\d+\) (\S+) \[ wb \] (.*) \[ wb \]$", meta_open(source[0].rstr()).read().replace(bad, "XQXQ"), re.M):
        word, a, b = m.groups()
        words[word] = words.get(word, []) + ["%s %s" % (a, b)]
    swords = sorted(words.iteritems())
    meta_open(tnew, "w").write("\n".join([x[0] for x in swords]))
    meta_open(tdict, "w").write("\n".join(["\n".join(["%s %s" % (k, vv) for vv in v]) for k, v in swords]))
    meta_open(tlm, "w").write(meta_open(source[1].rstr()).read().replace(bad, "XQXQ"))
    out, err, success = run_command(["java", "-jar", "data/AddWord.jar", "-n", tnew, "-d", tdict, "-a", tlm, 
                                     "-D", tnewdict, "-A", tnewlm, "-p", "-4.844"])
    with meta_open(target[0].rstr(), "w") as newdict_fd, meta_open(target[1].rstr(), "w") as newlm_fd:
        newdict_fd.write(meta_open(tnewdict).read().replace("XQXQ", bad))
        newlm_fd.write(meta_open(tnewlm).read().replace("XQXQ", bad))
    [os.remove(x) for x in [tnew, tdict, tlm, tnewdict, tnewlm]]
    if not success:
        return err
    return None

def collect_text(target, source, env):
    words = set()
    with meta_open(target[0].rstr(), "w") as ofd:
        for dname in source:
            for fname in glob(os.path.join(dname.rstr(), "*.txt")):
                with meta_open(fname) as ifd:
                    for line in ifd:
                        if not line.startswith("["):
                            toks = []
                            for x in line.lower().split():
                                if x == "<hes>":
                                    toks.append("<HES>")
                                elif not x.startswith("<"):
                                    toks.append(x)
                            for t in toks:
                                words.add(t)
                            if len(toks) > 0:
                                ofd.write("%s </s>\n" % (" ".join(toks)))
    with meta_open(target[1].rstr(), "w") as ofd:
        ofd.write("# BOS: <s>\n# EOS: </s>\n# UNK: <UNK>\n<s>\n</s>\n<UNK>\n")
        ofd.write("\n".join(sorted(words)) + "\n")                                      
    return None


def create_asr_directory(target, source, env):

    # the first three sources are the original configuration dictionaries
    files, directories, parameters = [x.read() for x in source[:3]]
    files = {k : env.File(v) for k, v in files.iteritems()}
    directories = {k : env.Dir(v) for k, v in directories.iteritems()}

    # the remainder are template files
    templates = source[3:]

    # create one big configuration dictionary
    config = {k : v for k, v in sum([list(y) for y in [files.iteritems(), directories.iteritems(), parameters.iteritems()]], [])}
    config["GRAPH_OFILE"] = env.File(os.path.join(config["OUTPUT_PATH"].rstr(), "dnet.bin.gz"))
    config["CTM_OPATH"] = env.Dir(os.path.join(config["OUTPUT_PATH"].rstr(), "ctm"))
    config["LAT_OPATH"] = env.Dir(os.path.join(config["OUTPUT_PATH"].rstr(), "lat"))

    # print dictionary for debugging
    logging.info("%s", "\n".join(["%s = %s" % (k, v) for k, v in config.iteritems()]))

    # perform substitution on each template file, write to appropriate location
    for template, final in zip(templates, target):
        with open(template.rstr()) as ifd, open(final.rstr(), "w") as ofd:
            ofd.write(scons_subst(ifd.read(), env=env, lvars=config))

    # write a PBS submission script for the entire experiment

    return None


def create_asr_directory_emitter(target, source, env):

    # start with three configuration dictionaries
    files, directories, parameters = [x.read() for x in source]

    # create a dependency on each file passed in
    for name, path in files.iteritems():
        env.Depends(target, path)

    # all templates (except for gcfg.py)
    input = ["gcfg.py"]
    dlatsi = ["cfg.py", "construct.py", "test.py", "consensus.py"]
    dlatsa = ["cfg.py", "construct.py", "vtln.py", "fmllr.py", "test.py", "test_cleanup.py", "consensus.py", "vcfg.py", "cat.py"]

    # new list of targets
    new_targets = [os.path.join(directories["CONFIGURATION_PATH"], "input/gcfg.py")] + \
        [os.path.join(directories["CONFIGURATION_PATH"], "dlatSI", x) for x in dlatsi] + \
        [os.path.join(directories["CONFIGURATION_PATH"], "dlatSA", x) for x in dlatsa]
 
    # new list of sources
    new_sources = [env.Value(files), env.Value(directories), env.Value(parameters)] + \
        [os.path.join("data", "gcfg.py.input")] + \
        [os.path.join("data", "%s.dlatSI" % x) for x in dlatsi] + \
        [os.path.join("data", "%s.dlatSA" % x) for x in dlatsa]

    return new_targets, new_sources


def create_small_asr_directory(target, source, env):

    # the first three sources are the original configuration dictionaries
    files, directories, parameters = [x.read() for x in source[:3]]
    files = {k : env.File(v) for k, v in files.iteritems()}
    directories = {k : env.Dir(v) for k, v in directories.iteritems()}

    # the remainder are template files
    templates = source[3:]

    # create one big configuration dictionary
    config = {k : v for k, v in sum([list(y) for y in [files.iteritems(), directories.iteritems(), parameters.iteritems()]], [])}
    config["GRAPH_OFILE"] = env.File(os.path.join(config["OUTPUT_PATH"].rstr(), "dnet.bin.gz"))
    config["CTM_OPATH"] = env.Dir(os.path.join(config["OUTPUT_PATH"].rstr(), "ctm"))
    config["LAT_OPATH"] = env.Dir(os.path.join(config["OUTPUT_PATH"].rstr(), "lat"))

    # print dictionary for debugging
    logging.debug("%s", "\n".join(["%s = %s" % (k, v) for k, v in config.iteritems()]))

    # perform substitution on each template file, write to appropriate location
    for template, final in zip(templates, target):
        with open(template.rstr()) as ifd, open(final.rstr(), "w") as ofd:
            ofd.write(scons_subst(ifd.read(), env=env, lvars=config))

    return None

def create_small_asr_directory_emitter(target, source, env):

    # start with three configuration dictionaries
    files, directories, parameters = [x.read() for x in source]

    # create a dependency on each file passed in
    for name, path in files.iteritems():
        env.Depends(target, path)

    # all templates
    dlatsa = ["cfg.py", "construct.py", "test.py"]

    # new list of targets
    new_targets = [os.path.join(directories["CONFIGURATION_PATH"], x) for x in dlatsa]
 
    # new list of sources
    new_sources = [env.Value(files), env.Value(directories), env.Value(parameters)] + \
        [os.path.join("data", "%s.dlatSA" % x) for x in dlatsa]

    return new_targets, new_sources

def TOOLS_ADD(env):
    env.Append(BUILDERS = {"AppenToAttila" : Builder(action=appen_to_attila),
                           "DictionaryToVocabulary" : Builder(action=dictionary_to_vocabulary),
                           "IBMTrainLanguageModel" : Builder(action=ibm_train_language_model),
                           "MissingVocabulary" : Builder(action=missing_vocabulary),
                           "AugmentLanguageModel" : Builder(action=augment_language_model, emitter=augment_language_model_emitter),
                           "AugmentLanguageModelFromBabel" : Builder(action=augment_language_model_from_babel),
                           "TranscriptVocabulary" : Builder(action=transcript_vocabulary),
                           "TrainPronunciationModel" : Builder(action=train_pronunciation_model),
                           "CreateASRDirectory" : Builder(action=create_asr_directory, emitter=create_asr_directory_emitter),
                           "CreateSmallASRDirectory" : Builder(action=create_small_asr_directory, emitter=create_small_asr_directory_emitter),
                           "CollectText" : Builder(action=collect_text),
                           })
               
