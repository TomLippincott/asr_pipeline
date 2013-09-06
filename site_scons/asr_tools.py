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


def experiment(target, source, env):
    return None

def experiment_emitter(target, source, env):
    new_targets = [
        os.path.join(target[0].rstr(), "gcfg.py"),
        os.path.join(target[0].rstr(), "dlatSI", "cfg.py"),
        os.path.join(target[0].rstr(), "dlatSA", "cfg.py"),
        ]
    return new_targets, source

#
# PREPARE
#

def make_base_dict(target, source, env, for_signature):
    locale, skip_roman = [x.read() for x in source[0:2]]
    if skip_roman:
        skip_roman = " -r "
    else:
        skip_roman = ""
    lexicons = " ".join(["-i %s" % x.rstr() for x in source[2:]])
    return "${ATILLA_INTERPRETER} bin/makeBaseDict.py -l %s %s %s -d ${TARGETS[0]} -p ${TARGETS[1]} -t ${TARGETS[2]}" % (locale, skip_roman, lexicons)

def collect_raw_text(target, source, env, for_signature):
    return "${ATILLA_INTERPRETER} bin/collectRawText.py -o ${TARGET} ${SOURCES}"

def normalize_text(target, source, env, for_signature):
    return ""

def make_dict(target, source, env, for_signature):
    return ""

def make_phoneset(target, source, env, for_signature):
    return ""

def gen_db(target, source, env, for_signature):
    return ""

def gen_refs(target, source, env, for_signature):
    return ""

#
# Language Model
#

def ibm_train_language_model(target, source, env, for_signature):
    return ""

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
    Input: new words, old dictionary, old language model
    Output: new dictionary, new language model
    """
    (tnew_fid, tnew), (tdict_fid, tdict), (tlm_fid, tlm) = [tempfile.mkstemp() for i in range(3)]
    (tnewdict_fid, tnewdict), (tnewlm_fid, tnewlm) = [tempfile.mkstemp() for i in range(2)]
    bad = "\xc3\xb1"
    updates = {}

    old_dict_words = set([x.split("(")[0] for x in meta_open(source[1].rstr())])

    # replace special characters
    meta_open(tnew, "w").write("\n".join([x for x in meta_open(source[0].rstr()).read().replace(bad, "XQXQ").split("\n") if len(x.split()) > 0 and x.split()[0] not in old_dict_words]))
    meta_open(tdict, "w").write(meta_open(source[1].rstr()).read().replace(bad, "XQXQ"))
    meta_open(tlm, "w").write(meta_open(source[2].rstr()).read().replace(bad, "XQXQ"))
    
    out, err, success = run_command(["java", "-jar", "data/AddWord.jar", "-n", tnew, "-d", tdict, "-a", tlm, 
                                     "-D", tnewdict, "-A", tnewlm, "-p", "-4.844"])
    with meta_open(target[0].rstr(), "w") as newdict_fd, meta_open(target[1].rstr(), "w") as newlm_fd, meta_open(target[2].rstr(), "w") as newvocab_fd:
        newdict_fd.write("\n".join([" ".join([x[0].lower()] + x[1:]) for x in [l.split() for l in meta_open(tnewdict).read().replace("XQXQ", bad).split("\n")] if len(x) > 0]))
        newdict_fd.close()
        newlm_fd.write(meta_open(tnewlm).read().replace("XQXQ", bad))
        newvocab_fd.write("\n".join(["%s(%s) %s" % (w, n, w) for w, n in [re.match(r"^(\S+)\((\d+)\) .*", l).groups() for l in meta_open(target[0].rstr())]]))
        #newvocab_fd.write(meta_open(
    [os.remove(x) for x in [tnew, tdict, tlm, tnewdict, tnewlm]]
    if not success:
        return err
    return None

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

def _augment_language_model(target, source, env):
    """
    Input: Arpabo file, Vocabulary
    Output: Arpabo file
    """
    arpabo_rx = re.compile(r"""
(?P<preamble>.*
BBOARD_BEGIN
(?P<bboard>.*?)
BBOARD_END
\s+
\\data\\
.*
)
(?P<ngrams>
\\1-grams:.*?
)
\\end\\
\s*
""", re.X | re.S | re.M)
    ngram_rx = re.compile(r"""
^\\(\d+)-grams:\n
(.*?)\n
\n
""", re.X | re.S | re.M)
    ngrams = {}
    with meta_open(source[0].rstr()) as arpabo, meta_open(source[1].rstr()) as vocab:
        words = [x.strip() for x in vocab]
        arpabo_match = arpabo_rx.match(arpabo.read())
        for m in ngram_rx.finditer(arpabo_match.group("ngrams")):
            n = int(m.group(1))
            ngrams[n] = {}
            for line in m.group(2).strip().lower().split("\n"):
                toks = line.split()
                seq = tuple(toks[1:n + 1])
                if len(toks) < n + 2:
                    ngrams[n][seq] = (float(toks[0]), None)
                else:
                    ngrams[n][seq] = (float(toks[0]), float(toks[-1]))
        avg_prob = sum([x[0] for x in ngrams[1].values()]) / len(ngrams[1])
        new_words = [x for x in words if (x,) not in ngrams[1] if "_" not in x and re.match(r".*[a-z].*", x)]
        print new_words
        for word in new_words:
            ngrams[1][(word.rstrip("-"),)] = (avg_prob, None)
        with meta_open(target[0].rstr(), "w") as ofd:
            ofd.write(arpabo_match.group("preamble"))
            for n, grams in ngrams.iteritems():
                ofd.write("\\%d-grams:\n" % n)
                for gram, (prob, bow) in grams.iteritems():
                    if bow:
                        ofd.write("%f %s %f\n" % (prob, " ".join(gram), bow))
                    else:
                        ofd.write("%f %s\n" % (prob, " ".join(gram)))
                ofd.write("\n")
            ofd.write("\\end\\\n\n")
    return None

#
# Generic Audio Model
#

#
# Speech/Non-Speech Model
#

#
# Context-Independent Model
#

#
# mixup
#

#
# Context-Dependent Model
#

def create_asr_directory(target, source, env):
    language_model, vocabulary, dictionary, database, gcfg_template, dlatsi_template, dlatsa_template = source[0:7]
    gcfg, dlatsi, dlatsa = target[0:3]
    args = source[-1].read()
    vals = {
        "LANGUAGE_MODEL" : language_model,
        "PCM_DIR" : args["DATA"],
        "ROOT_DIR" : args["IBM_PATH"],
        "VOCABULARY" : vocabulary,
        "DICTIONARY" : dictionary,
        "DATABASE" : database,
        "GCFG_FILE" : gcfg,
        "MAX_ERROR" : 15000,
        "USE_DISPATCHER" : False,
        }
    for ifname, ofname in zip(source[4:], target):
        with open(ifname.rstr()) as ifd, open(ofname.rstr(), "w") as ofd:
            ofd.write(scons_subst(ifd.read(), env=env, lvars=vals))
    for fname in ["consensus.py", "construct.py", "density.py", "test.pj", "test.py", "testserver.py"]:
        pass
        #shutil.copyfile(os.path.join(args["IBM_PATH"], "dlatSI", fname), os.path.join(target[1]))
    for fname in ["cat.py", "consensus.py", "construct.py", "density.py", "fmllr.py", "test_cleanup.py", "test.pj", "test.py", "testserver.py", "vcfg.py", "vtln.py", "warp.lst"]:
        pass
    return None

def create_asr_directory_emitter(target, source, env):
    args = source[0].read()
    base = target[0].rstr()
    new_targets = [
        os.path.join(base, "input", "gcfg.py"),
        os.path.join(base, "dlatSI", "cfg.py"),
        os.path.join(base, "dlatSA", "cfg.py"),
        ] + \
        [os.path.join(base, "dlatSI", x) for x in ["consensus.py", "construct.py", "density.py", "test.pj", "test.py", "testserver.py"]] + \
        [os.path.join(base, "dlatSA", x) for x in ["cat.py", "consensus.py", "construct.py", "density.py", "fmllr.py", "test_cleanup.py", "test.pj", 
                                                   "test.py", "testserver.py", "vcfg.py", "vtln.py", "warp.lst"]]
    new_sources = [
        args["LANGUAGE_MODEL"],
        args["VOCABULARY"],
        args["DICTIONARY"],
        args["DATABASE"],
        os.path.join("data", "gcfg.py.template"),
        os.path.join("data", "dlatsi.cfg.py.template"),
        os.path.join("data", "dlatsa.cfg.py.template"),
        source[0],
        ]
    return new_targets, new_sources

def TOOLS_ADD(env):
    env.Append(BUILDERS = {"IBMTrainLanguageModel" : Builder(generator=ibm_train_language_model),
                           "BaseDictionary" : Builder(generator=make_base_dict),
                           "CollectRawText" : Builder(generator=collect_raw_text),
                           "Experiment" : Builder(action=experiment, emitter=experiment_emitter),
                           "MissingVocabulary" : Builder(action=missing_vocabulary),
                           "AugmentLanguageModel" : Builder(action=augment_language_model),
                           "AugmentLanguageModelFromBabel" : Builder(action=augment_language_model_from_babel),
                           "TranscriptVocabulary" : Builder(action=transcript_vocabulary),
                           "TrainPronunciationModel" : Builder(action=train_pronunciation_model),
                           "CreateASRDirectory" : Builder(action=create_asr_directory, emitter=create_asr_directory_emitter),
                           })
               
