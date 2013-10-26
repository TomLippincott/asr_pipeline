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
import torque


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


def submit_job(target, source, env):
    args = source[-1].read()
    stdout = args.get("stdout", os.path.join(args["path"], "stdout"))
    stderr = args.get("stderr", os.path.join(args["path"], "stderr"))
    interval = args.get("interval", 10)
    job = torque.Job(args.get("name", "scons"),
                     commands=[env.subst(x) for x in args["commands"]],
                     path=args["path"],
                     stdout_path=stdout,
                     stderr_path=stderr)
    j = job.submit()
    print job.job_id
    
    return None



def TOOLS_ADD(env):
    env.Append(BUILDERS = {"SubmitJob" : Builder(action=submit_job),
                           })
# "IBMTrainLanguageModel" : Builder(generator=ibm_train_language_model),
#                            "BaseDictionary" : Builder(generator=make_base_dict),
#                            "CollectRawText" : Builder(generator=collect_raw_text),
#                            "Experiment" : Builder(action=experiment, emitter=experiment_emitter),
#                            "MissingVocabulary" : Builder(action=missing_vocabulary),
#                            "AugmentLanguageModel" : Builder(action=augment_language_model),
#                            "AugmentLanguageModelFromBabel" : Builder(action=augment_language_model_from_babel),
#                            "TranscriptVocabulary" : Builder(action=transcript_vocabulary),
#                            "TrainPronunciationModel" : Builder(action=train_pronunciation_model),
#                            "CreateASRDirectory" : Builder(action=create_asr_directory, emitter=create_asr_directory_emitter),
#                            })
