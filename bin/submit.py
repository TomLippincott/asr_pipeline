import argparse
import subprocess
import re
import sys
import random
import logging


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--number", dest="number", type=int, default=10)
parser.add_argument("-c", "--commit", dest="commit", default=False, action="store_true")
parser.add_argument("-a", "--attila_path", dest="attila_path", default="/local/tml2115/asr/VT-2-5-babel")
parser.add_argument("-l", "--language_path", dest="language_path", default="/local/tml2115/asr/Tagalog")
parser.add_argument("-H", "--hold", dest="hold", default=False, action="store_true")
parser.add_argument("-S", "--start", choices=["dlatsi", "dlatsa1", "dlatsa2"], default="dlatsi")
parser.add_argument("-E", "--end", choices=["dlatsi", "dlatsa1", "dlatsa2"], default="dlatsi")
parser.add_argument("-e", "--stderr", dest="error", default=None)
parser.add_argument("-o", "--stdout", dest="output", default=None)
options = parser.parse_args()


logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)


default_skeleton = """
#PBS -N %(NAME)s
#PBS -l cput=20:30:00        
#PBS -l walltime=20:30:00        
%(PBS_OPTIONS)s

cd %(PATH)s
%(COMMANDS)s
exit 0
"""

class Job():
    def __init__(self, name="UNNAMED", resources={}, dependencies=[], commands=[], path="", array=0, output_path=None, error_path=None):
        self.name = name
        self.resources = resources
        self.dependencies = dependencies
        self.commands = commands
        self.path = path
        self.array = array
        self.resources["cput"] = "20:30:00"
        self.resources["walltime"] = "20:30:00"
        self.commands.append("exit 0")
        self.output_path = output_path
        self.error_path = error_path

    def __str__(self):
        lines = ["#PBS -N %s" % self.name] + ["#PBS -l %s=%s" % (k, v) for k, v in self.resources.iteritems()]
        if self.output_path:
            lines.append("#PBS -o %s" % self.output_path)
        if self.error_path:
            lines.append("#PBS -e %s" % self.error_path)
        if self.dependencies:
            arrays = [x.job_id for x in self.dependencies if x.array > 0]
            nonarrays = [x.job_id for x in self.dependencies if x.array == 0]
            if len(arrays) > 0 and len(nonarrays) > 0:
                depline = "%s,%s" % ("afterany:%s" % (":".join([str(x) for x in nonarrays])), "afteranyarray:%s" % (":".join(["%d[]" % (x) for x in arrays])))
            elif len(arrays) == 0 and len(nonarrays) > 0:
                depline = "afterany:%s" % (":".join([str(x) for x in nonarrays]))
            else:
                depline = "afteranyarray:%s" % (":".join(["%d[]" % (x) for x in arrays]))
            lines.append("#PBS -W depend=%s" % depline)
        if self.array > 0:
            lines.append("#PBS -t 0-%d" % (self.array - 1))
        if self.path:
            lines.append("cd %s" % self.path)
        lines += [c for c in self.commands]
        return "\n".join(lines) + "\n"

    def submit(self, commit=False, propagate=True):
        cmd = ["qsub"]
        if propagate:
            cmd.append("-V")
        if options.hold:
            cmd.append("-h")
        if commit:
            logging.debug("Submitting the following job specification via \"%s\":\n%s" % (" ".join(cmd), self))
            out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE).communicate(str(self))
            try:
                logging.info("Got job id: %s" % out)
                job_id = int(out.strip().split(".")[0])
                self.job_id = job_id
            except:
                print out, err
                sys.exit()
        else:
            logging.debug("Would submit the following job specification via \"%s\":\n%s" % (" ".join(cmd), self))
            self.job_id = random.randint(1, 10000)
            
def get_nodes():
    out, err = subprocess.Popen(["qnodes"], stdout=subprocess.PIPE).communicate()
    return [x.strip() for x in out.split("\n") if re.match(r"^\S+.*$", x)]


nodes = get_nodes()
logging.info("Available nodes: %s", ", ".join(nodes))


# input/dict.test input/vocab buildLM/lm.3gm.arpabo.gz
#
# clean -> [constructSI -> dlatSI -> rsync] -> [dlatSA1 -> rsync] -> [constructSA -> dlatSA2 -> rsync]
#
# dlatsa - ctm lat cctm cons (refers to dlatsi-cons) (maybe makes cms fmllr)
dlatsi_locs = ["lat", "ctm", "cctm", "cons"]
dlatsa_locs = ["lat", "ctm", "cctm", "cons"]


if options.start == "dlatsi":

    logging.info("launching initial clean-up and speaker-independent construction jobs, one per node")
    dlatsi_construct_jobs = []
    for node in nodes:
        cleanup_job = Job(name="cleanup",
                          resources={"nodes" : node},
                          dependencies=[],
                          commands=["rm -rf %s" % (" ".join(["%s/decode/dlatSI/%s" % (options.language_path, x) for x in ["lat", "ctm", "cctm", "cons", "param"]])),
                                    "rm -rf %s" % (" ".join(["%s/decode/dlatSA/%s" % (options.language_path, x) for x in ["lat", "ctm", "cctm", "cons", "param"]])),
                                    "mkdir %s" % (" ".join(["%s/decode/dlatSI/%s" % (options.language_path, x) for x in ["lat", "ctm", "cctm", "cons", "param"]])),
                                    "mkdir %s" % (" ".join(["%s/decode/dlatSA/%s" % (options.language_path, x) for x in ["lat", "ctm", "cctm", "cons", "param"]]))],
                          path="%s/decode/dlatSI" % options.language_path)
        cleanup_job.submit(options.commit)

        dlatsi_construct_job = Job(name="dlatsi_construct",
                                   resources={"nodes" : node},
                                   dependencies=[cleanup_job],
                                   commands=["%s/tools/attila/attila construct.py" % options.attila_path],
                                   path="%s/decode/dlatSI" % options.language_path)
        dlatsi_construct_job.submit(options.commit)
        dlatsi_construct_jobs.append(dlatsi_construct_job)


    logging.info("launching %d speaker-independent training jobs (dlatsi)", options.number)
    dlatsi_jobs = []
    for i in range(options.number):
        dlatsi_job = Job(name="dlatsi",
                         dependencies=dlatsi_construct_jobs,
                         resources={},
                         commands=["%s/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.attila_path, options.number, i),
                                   "%s/tools/attila/attila consensus.py -n %s -j %s" % (options.attila_path, options.number, i)],
                         path="%s/decode/dlatSI" % options.language_path,
                         )
        dlatsi_job.submit(options.commit)
        dlatsi_jobs.append(dlatsi_job)


    logging.info("rsyncing results of dlatsi")
    dlatsi_rsync_jobs = []
    for node in nodes:
        dlatsi_rsync_job = Job(name="post_dlatsi_rsync",
                               dependencies=dlatsi_jobs,
                               resources={"nodes" : node},
                               commands=["rsync -avz -e ssh %s:%s/decode/dlatSI/%s %s/decode/dlatSI/" % (n, options.language_path, d, options.language_path) for n in nodes for d in dlatsi_locs],
                               path="%s/decode/dlatSI" % options.language_path,
                               )
        dlatsi_rsync_job.submit(options.commit)
        dlatsi_rsync_jobs.append(dlatsi_rsync_job)

if options.start == "dlatsa1":
    dlatsi_rsync_jobs = []

if options.start in ["dlatsi", "dlatsa1"] and options.end != "dlatsi":

    logging.info("launching %d speaker-adapted training jobs (dlatsa1)", options.number)
    dlatsa1_jobs = []
    for i in range(options.number):
        dlatsa1_job = Job(name="dlatsa1",
                          dependencies=dlatsi_rsync_jobs,
                          resources={},
                          commands=["%s/tools/attila/attila vtln.py -n %s -j %s" % (options.attila_path, options.number, i),
                                    "%s/tools/attila/attila cat.py -n %s -j %s" % (options.attila_path, options.number, i),
                                    "%s/tools/attila/attila fmllr.py -n %s -j %s" % (options.attila_path, options.number, i)],
                          path="%s/decode/dlatSA" % options.language_path,
                          )
        dlatsa1_job.submit(options.commit)
        dlatsa1_jobs.append(dlatsa1_job)


    logging.info("rsyncing results of dlatsa1")
    dlatsa1_rsync_jobs = []
    for node in nodes:
        dlatsa1_rsync_job = Job(name="post_dlatsa1_rsync",
                               dependencies=dlatsa1_jobs,
                               resources={"nodes" : node},
                               commands=["rsync -avz -e ssh %s:%s/decode/dlatSA/%s %s/decode/dlatSA/" % (n, options.language_path, d, options.language_path) for n in nodes for d in dlatsa_locs],
                               path="%s/decode/dlatSA" % options.language_path,
                               )
        dlatsa1_rsync_job.submit(options.commit)
        dlatsa1_rsync_jobs.append(dlatsa1_rsync_job)


if options.start == "dlatsa2":
    dlatsa1_rsync_jobs = []

if options.start in ["dlatsi", "dlatsa1", "dlatsa2"] and options.end not in ["dlatsi", "dlatsa1"]:

    logging.info("launching speaker-adapted construction jobs, one per node")
    dlatsa_construct_jobs = []
    for node in nodes:
        dlatsa_construct_job = Job(name="dlatsa_construct",
                                   resources={"nodes" : node},
                                   dependencies=dlatsa1_rsync_jobs,
                                   commands=["%s/tools/attila/attila construct.py" % options.attila_path],
                                   path="%s/decode/dlatSA" % options.language_path)
        dlatsa_construct_job.submit(options.commit)
        dlatsa_construct_jobs.append(dlatsa_construct_job)


    logging.info("launching %d speaker-adapted training jobs (dlatsa2)", options.number)
    dlatsa2_jobs = []
    for i in range(options.number):
        dlatsa2_job = Job(name="dlatsa2",
                          dependencies=dlatsa1_rsync_jobs,
                          resources={},
                          commands=["%s/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.attila_path, options.number, i),
                                    #"%s/VT-2-5-babel/tools/attila/attila test_cleanup.py -n %s -j %s" % (options.asr_path, options.number, i),
                                    "%s/tools/attila/attila consensus.py -n %s -j %s" % (options.attila_path, options.number, i)],
                          path="%s/decode/dlatSA" % options.language_path,
                          )
        dlatsa2_job.submit(options.commit)
        dlatsa2_jobs.append(dlatsa2_job)


    logging.info("rsyncing results of dlatsa2")
    dlatsa2_rsync_jobs = []
    for node in nodes:
        dlatsa2_rsync_job = Job(name="post_dlatsa2_rsync",
                               dependencies=dlatsa2_jobs,
                               resources={"nodes" : node},
                               commands=["rsync -avz -e ssh %s:%s/decode/dlatSA/%s %s/decode/dlatSA/" % (n, options.language_path, d, options.language_path) for n in nodes for d in dlatsa_locs],
                               path="%s/decode/dlatSA" % options.language_path,
                               )
        dlatsa2_rsync_job.submit(options.commit)
        dlatsa2_rsync_jobs.append(dlatsa1_rsync_job)
