import argparse
import subprocess
import re
import sys
import random
import logging
import os.path

class PathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        apath = os.path.abspath(values)
        if not os.path.exists(apath):            
            raise Exception("%s does not exist!" % apath)
        setattr(namespace, self.dest, apath)

parser = argparse.ArgumentParser()
parser.add_argument("-A", "--attila_path", dest="attila_path", action=PathAction, required=True)
parser.add_argument("-C", "--config_path", dest="config_path", action=PathAction, required=True)
parser.add_argument("-O", "--output_path", dest="output_path", action=PathAction, required=True)
parser.add_argument("-e", "--stderr", dest="stderr", action=PathAction, required=True)
parser.add_argument("-o", "--stdout", dest="stdout", action=PathAction, required=True)
parser.add_argument("-n", "--number", dest="number", type=int, default=10)
parser.add_argument("-c", "--commit", dest="commit", default=False, action="store_true")
parser.add_argument("-H", "--hold", dest="hold", default=False, action="store_true")
parser.add_argument("-S", "--start", choices=["dlatsi", "dlatsa1", "dlatsa2"], default="dlatsi")
parser.add_argument("-E", "--end", choices=["dlatsi", "dlatsa1", "dlatsa2"], default="dlatsa2")
parser.add_argument("-D", "--debug", dest="debug", default=False, action="store_true")
options = parser.parse_args()

if options.debug:    
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
else:
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
    def __init__(self, name="UNNAMED", resources={}, dependencies=[], commands=[], path="", array=0, stdout_path=None, stderr_path=None):
        self.name = name
        self.resources = resources
        self.dependencies = dependencies
        self.commands = commands
        self.path = path
        self.array = array
        self.resources["cput"] = "20:30:00"
        self.resources["walltime"] = "20:30:00"
        self.commands.append("exit 0")
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path

    def __str__(self):
        lines = ["#PBS -N %s" % self.name] + ["#PBS -l %s=%s" % (k, v) for k, v in self.resources.iteritems()]
        if self.stdout_path:
            lines.append("#PBS -o %s" % os.path.join(self.stdout_path, "%s.out" % (self.name)))
        if self.stderr_path:
            lines.append("#PBS -e %s" % os.path.join(self.stderr_path, "%s.err" % (self.name)))
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
            
def get_nodes(commit):
    if options.commit:
        out, err = subprocess.Popen(["qnodes"], stdout=subprocess.PIPE).communicate()
        return [x.strip() for x in out.split("\n") if re.match(r"^\S+.*$", x)]
    else:
        return ["dummy%d" % x for x in range(1, 5)]

nodes = get_nodes(options.commit)
logging.info("Available nodes: %s", ", ".join(nodes))

if options.start == "dlatsi":
    logging.info("launching initial clean-up and speaker-independent construction jobs, one per node")
    dlatsi_construct_jobs = []
    for node in nodes:
        cleanup_job = Job(name="cleanup_%s" % node,
                          resources={"nodes" : node},
                          dependencies=[],
                          commands=["rm -rf %s/*" % options.output_path],
                          stdout_path=options.stdout,
                          stderr_path=options.stderr)

                
        cleanup_job.submit(options.commit)

        dlatsi_construct_job = Job(name="dlatsi_construct_%s" % node,
                                   resources={"nodes" : node},
                                   dependencies=[cleanup_job],
                                   commands=["%s/tools/attila/attila construct.py" % options.attila_path],
                                   path="%s/dlatSI" % options.config_path,
                                   stdout_path=options.stdout,
                                   stderr_path=options.stderr)

        dlatsi_construct_job.submit(options.commit)
        dlatsi_construct_jobs.append(dlatsi_construct_job)


    logging.info("launching %d speaker-independent training jobs (dlatsi)", options.number)
    dlatsi_jobs = []
    for i in range(options.number):
        dlatsi_job = Job(name="dlatsi_j%d_n%d" % (i, options.number),
                         dependencies=dlatsi_construct_jobs,
                         resources={},
                         commands=["%s/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.attila_path, options.number, i),
                                   "%s/tools/attila/attila consensus.py -n %s -j %s" % (options.attila_path, options.number, i)],
                         path="%s/dlatSI" % options.config_path,
                         stdout_path=options.stdout,
                         stderr_path=options.stderr)
        dlatsi_job.submit(options.commit)
        dlatsi_jobs.append(dlatsi_job)


    logging.info("rsyncing results of dlatsi")
    dlatsi_rsync_jobs = []
    for node in nodes:
        dlatsi_rsync_job = Job(name="post_dlatsi_rsync_%s" % node,
                               dependencies=dlatsi_jobs,
                               resources={"nodes" : node},
                               commands=["rsync -avz -e ssh %s:%s/* %s" % (n, options.output_path, options.output_path) for n in nodes],
                               stdout_path=options.stdout,
                               stderr_path=options.stderr)
        dlatsi_rsync_job.submit(options.commit)
        dlatsi_rsync_jobs.append(dlatsi_rsync_job)

if options.start == "dlatsa1":
    dlatsi_rsync_jobs = []

if options.start in ["dlatsi", "dlatsa1"] and options.end != "dlatsi":

    logging.info("launching %d speaker-adapted training jobs (dlatsa1)", options.number)
    dlatsa1_jobs = []
    for i in range(options.number):
        dlatsa1_job = Job(name="dlatsa1_j%d_n%d" % (i, options.number),
                          dependencies=dlatsi_rsync_jobs,
                          resources={},
                          commands=["%s/tools/attila/attila vtln.py -n %s -j %s" % (options.attila_path, options.number, i),
                                    "%s/tools/attila/attila fmllr.py -n %s -j %s" % (options.attila_path, options.number, i)],
                          path="%s/dlatSA" % options.config_path,
                          stdout_path=options.stdout,
                          stderr_path=options.stderr)
        dlatsa1_job.submit(options.commit)
        dlatsa1_jobs.append(dlatsa1_job)


    logging.info("rsyncing results of dlatsa1")
    dlatsa1_rsync_jobs = []
    for node in nodes:
        dlatsa1_rsync_job = Job(name="post_dlatsa1_rsync_%s" % node,
                                dependencies=dlatsa1_jobs,
                                resources={"nodes" : node},
                                commands=["rsync -avz -e ssh %s:%s/* %s" % (n, options.output_path, options.output_path) for n in nodes] + \
                                    ["%s/tools/attila/attila cat.py" % options.attila_path],
                                path="%s/dlatSA" % options.config_path,
                                stdout_path=options.stdout,
                                stderr_path=options.stderr)
        dlatsa1_rsync_job.submit(options.commit)
        dlatsa1_rsync_jobs.append(dlatsa1_rsync_job)


if options.start == "dlatsa2":
    dlatsa1_rsync_jobs = []

if options.start in ["dlatsi", "dlatsa1", "dlatsa2"] and options.end not in ["dlatsi", "dlatsa1"]:

    logging.info("launching speaker-adapted construction jobs, one per node")
    dlatsa_construct_jobs = []
    for node in nodes:
        dlatsa_construct_job = Job(name="dlatsa_construct_%s" % node,
                                   resources={"nodes" : node},
                                   dependencies=dlatsa1_rsync_jobs,
                                   commands=["%s/tools/attila/attila construct.py" % options.attila_path],
                                   path="%s/dlatSA" % options.config_path,
                                   stdout_path=options.stdout,
                                   stderr_path=options.stderr)
        dlatsa_construct_job.submit(options.commit)
        dlatsa_construct_jobs.append(dlatsa_construct_job)


    logging.info("launching %d speaker-adapted training jobs (dlatsa2)", options.number)
    dlatsa2_jobs = []
    for i in range(options.number):
        dlatsa2_job = Job(name="dlatsa2_j%d_n%d" % (i, options.number),
                          dependencies=dlatsa1_rsync_jobs,
                          resources={},
                          commands=["%s/tools/attila/attila test.py -w 0.060 -n %s -j %s" % (options.attila_path, options.number, i),
                                    "%s/tools/attila/attila consensus.py -n %s -j %s" % (options.attila_path, options.number, i)],
                          path="%s/dlatSA" % options.config_path,
                          stdout_path=options.stdout,
                          stderr_path=options.stderr)
        dlatsa2_job.submit(options.commit)
        dlatsa2_jobs.append(dlatsa2_job)


    logging.info("rsyncing results of dlatsa2")
    dlatsa2_rsync_jobs = []
    for node in nodes:
        dlatsa2_rsync_job = Job(name="post_dlatsa2_rsync_%s" % node,
                                dependencies=dlatsa2_jobs,
                                resources={"nodes" : node},
                                commands=["rsync -avz -e ssh %s:%s/* %s" % (n, options.output_path, options.output_path) for n in nodes],
                                path="%s/dlatSA" % options.config_path,
                                stdout_path=options.stdout,
                                stderr_path=options.stderr)
        dlatsa2_rsync_job.submit(options.commit)
        dlatsa2_rsync_jobs.append(dlatsa1_rsync_job)
