import argparse
import subprocess
import re
import sys
import random
import logging


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--number", dest="number", type=int, default=10)
parser.add_argument("-c", "--commit", dest="commit", default=False, action="store_true")
parser.add_argument("-a", "--asr_path", dest="asr_path", default="/local/tml2115/asr")
options = parser.parse_args()


logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)


default_skeleton = """
#PBS -N %(NAME)s
#PBS -l cput=20:30:00        
#PBS -l walltime=20:30:00        
%(PBS_OPTIONS)s

cd %(PATH)s
%(COMMANDS)s
exit 0
"""


def get_nodes():
    out, err = subprocess.Popen(["qnodes"], stdout=subprocess.PIPE).communicate()
    return [x.strip() for x in out.split("\n") if re.match(r"^\S+.*$", x)]


def submit_job(name, commands, path="", pbs_options=[], skeleton=default_skeleton): #, depends=[]):
    spec = default_skeleton % {"NAME" : name,
                               "PBS_OPTIONS" : "\n".join(["#PBS %s" % x for x in pbs_options]),
                               "PATH" : path,
                               "COMMANDS" : "\n".join(commands),
                           }
    cmd = ["qsub", "-V"]
    if options.commit:
        out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE).communicate(spec)
        try:
            job_id = int(out.strip().split(".")[0])
        except:
            logging.error(out + err)
            sys.exit()
    else:
        logging.debug(spec)
        out, err, job_id = "", "", random.randint(0, 1000)
    return out, err, job_id


nodes = get_nodes()
logging.info("Available nodes: %s", ", ".join(nodes))

# input/dict.test input/vocab buildLM/lm.3gm.arpabo.gz param/dnet.bin.gz

# dlatsi - ctm lat cctm cons
logging.info("launching initial speaker-independent construction jobs, one per node")
construct_ids = []
for node in nodes:
    out, err, job_id = submit_job("dlatsi_construct",
                                  ["%s/VT-2-5-babel/tools/attila/attila construct.py" % options.asr_path, 
                                   "#sleep 30"],
                                  "%s/Tagalog/decode/dlatSI" % options.asr_path,
                                  ["-l nodes=%s" % node],
                                  default_skeleton
                                  )
    construct_ids.append(job_id)


logging.info("launching %d speaker-independent training jobs", options.number)
dlatsi_ids = []
for i in range(options.number):
    out, err, job_id = submit_job("dlatsi",
                                  ["%s/VT-2-5-babel/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.asr_path, options.number, i),
                                   "%s/VT-2-5-babel/tools/attila/attila consensus.py -n %s -j %s" % (options.asr_path, options.number, i)],
                                  "%s/Tagalog/decode/dlatSI" % options.asr_path,
                                  ["-W depend=afterany:%s" % (":".join([str(x) for x in construct_ids]))],
                                  default_skeleton,
                              )
    dlatsi_ids.append(job_id)

# dlatsa - ctm lat cctm cons (refers to dlatsi-cons) (maybe makes cms fmllr)
logging.info("launching %d speaker-adapted training jobs, phase 1", options.number)
dlatsa_ids = []
for i in range(options.number):
    out, err, job_id = submit_job("dlatsa_1",
                                  ["%s/VT-2-5-babel/tools/attila/attila vtln.py -n %s -j %s" % (options.asr_path, options.number, i),
                                   "%s/VT-2-5-babel/tools/attila/attila cat.py -n %s -j %s" % (options.asr_path, options.number, i),
                                   "%s/VT-2-5-babel/tools/attila/attila fmllr.py -n %s -j %s" % (options.asr_path, options.number, i)],
                                  "%s/Tagalog/decode/dlatSA" % options.asr_path,
                                  ["-W depend=afterany:%s" % (":".join([str(x) for x in dlatsi_ids]))],
                                  default_skeleton,
                              )
    dlatsa_ids.append(job_id)


logging.info("launching speaker-adapted construction jobs, one per node")
construct_ids = []
for node in nodes:
    out, err, job_id = submit_job("dlatsa_construct",
                                  ["%s/VT-2-5-babel/tools/attila/attila construct.py" % options.asr_path],
                                  "%s/Tagalog/decode/dlatSA" % options.asr_path,
                                  ["-l nodes=%s" % node,
                                   "-W depend=afterany:%s" % (":".join([str(x) for x in dlatsa_ids]))],
                                  default_skeleton,
                                  )
    construct_ids.append(job_id)


logging.info("launching %d speaker-adapted training jobs, phase 2", options.number)
dlatsa_ids = []
for i in range(options.number):
    out, err, job_id = submit_job("dlatsa_2",
                                  ["%s/VT-2-5-babel/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.asr_path, options.number, i),
                                   "%s/VT-2-5-babel/tools/attila/attila test_cleanup.py -n %s -j %s" % (options.asr_path, options.number, i),
                                   "%s/VT-2-5-babel/tools/attila/attila consensus.py -n %s -j %s" % (options.asr_path, options.number, i)],
                                  "%s/Tagalog/decode/dlatSA" % options.asr_path,
                                  ["-W depend=afterany:%s" % (":".join([str(x) for x in construct_ids]))],
                                  default_skeleton,
                              )
    dlatsa_ids.append(job_id)
