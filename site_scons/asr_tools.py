from SCons.Builder import Builder
from SCons.Action import Action
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

def run_command(cmd, env={}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    Simple convenience wrapper for running commands (not an actual Builder).
    """
    logging.info("Running command: %s", cmd)
    process = subprocess.Popen(shlex.split(cmd), env=env, stdin=stdin, stdout=stdout, stderr=stderr)
    out, err = process.communicate()
    return out, err, process.returncode == 0

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



def TOOLS_ADD(env):
    env.Append(BUILDERS = {"BaseDictionary" : Builder(generator=make_base_dict),
                           "CollectRawText" : Builder(generator=collect_raw_text),
                           })
               
