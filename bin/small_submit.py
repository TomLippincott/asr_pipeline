import argparse
import subprocess
import re
import sys
import random
import logging
import os.path
import os

class PathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        apath = os.path.abspath(values)
        try:
            os.makedirs(apath)
        except:
            pass
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
parser.add_argument("-D", "--debug", dest="debug", default=False, action="store_true")
parser.add_argument("-a", "--acoustic_weight", dest="acw", default=0.13, type=float)
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


logging.info("launching speaker-adapted construction jobs, one per node")
dlatsa_construct_jobs = []
for node in nodes:
    dlatsa_construct_job = Job(name="dlatsa_construct_%s" % node,
                               resources={"nodes" : node},
                               commands=["%s/tools/attila/attila construct.py" % options.attila_path],
                               path=options.config_path,
                               stdout_path=options.stdout,
                               stderr_path=options.stderr)
    dlatsa_construct_job.submit(options.commit)
    dlatsa_construct_jobs.append(dlatsa_construct_job)


logging.info("launching %d speaker-adapted training jobs", options.number)
dlatsa_jobs = []
for i in range(options.number):
    dlatsa_job = Job(name="dlatsa_j%d_n%d" % (i, options.number),
                     dependencies=dlatsa_construct_jobs,
                     resources={},
                     commands=["%s/tools/attila/attila test.py -w %f -n %s -j %s -l 1" % (options.attila_path, options.acw, options.number, i)],
                     #"%s/tools/attila/attila consensus.py -n %s -j %s" % (options.attila_path, options.number, i)],
                     path=options.config_path,
                     stdout_path=options.stdout,
                     stderr_path=options.stderr)
    dlatsa_job.submit(options.commit)
    dlatsa_jobs.append(dlatsa_job)


logging.info("rsyncing results of dlatsa")
for node in nodes:
    dlatsa_rsync_job = Job(name="post_dlatsa_rsync_%s" % node,
                            dependencies=dlatsa_jobs,
                            resources={"nodes" : node},
                            commands=["rsync -avz -e ssh %s:%s/* %s" % (n, options.output_path, options.output_path) for n in nodes],
                            path=options.config_path,
                            stdout_path=options.stdout,
                            stderr_path=options.stderr)
    dlatsa_rsync_job.submit(options.commit)
