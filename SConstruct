import sys
import os.path
import logging
import asr_tools

#
# load variable definitions from custom.py, and define them for SCons (seems like it should logically
# happen in the reverse order, but anyways...)
#
vars = Variables("custom.py")
vars.AddVariables(
    ("OUTPUT_WIDTH", "", 130),
    ("ATILLA_PATH", "", ""),
    ("SEQUITUR_PATH", "", ""),
    ("ATILLA_INTERPRETER", "", "${ATILLA_PATH}/tools/attila/attila"),
    ("BABEL_REPO", "", None),
    ("BABEL_RESOURCES", "", None),
    ("F4DE", "", None),
    ("INDUS_DB", "", None),
    ("JAVA_NORM", "", "${BABEL_REPO}/KWS/examples/babel-dryrun/javabin"),
    ("OVERLAY", "", None),
    ("LIBRARY_OVERLAY", "", "${OVERLAY}/lib:${OVERLAY}/lib64"),
    ("EXPERIMENTS", "", {}),
    ("LOG_LEVEL", "", logging.INFO),
    ("LOG_DESTINATION", "", sys.stdout),
    )

#
# create the actual build environment we'll be using: basically, just import the builders from site_scons/kws_tools.py
#
env = Environment(variables=vars, ENV={}, TARFLAGS="-c -z", TARSUFFIX=".tgz",
                  tools=["default", "textfile"] + [x.TOOLS_ADD for x in [asr_tools]],
                  BUILDERS={"CopyFile" : Builder(action="cp ${SOURCE} ${TARGET}")}
                  )

#
# initialize the Python logging system (though we don't really use it in this build, could be useful later)
#
if isinstance(env["LOG_DESTINATION"], basestring):
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"], filename=env["LOG_DESTINATION"])
else:
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"])

#
# each Builder emits a string describing what it's doing (target, source, etc), but with thousands of
# input files, this can be huge.  If the string is larger than OUTPUT_WIDTH, replace some of its
# characters with an ellipsis.  You can get less-truncated output by running e.g. "scons -Q OUTPUT_WIDTH=300"
#
def print_cmd_line(s, target, source, env):
    if len(s) > int(env["OUTPUT_WIDTH"]):
        print s[:int(env["OUTPUT_WIDTH"]) - 10] + "..." + s[-7:]
    else:
        print s

env['PRINT_CMD_LINE_FUNC'] = print_cmd_line




#
# check whether custom.py has defined all the variables we need
#
# undefined = [x for x in vars.keys() if x not in env]
# if len(undefined) != 0:
#     print ""
# One or more parameters (%s) are undefined.  Please edit custom.py appropriately.
# To get started, 'cp custom.py.example custom.py'
# """ % (",".join(undefined))
#     env.Exit()




#
# run all the experiments in EXPERIMENTS (defined in custom.py)
#
for name, experiment in env["EXPERIMENTS"].iteritems():
    #dev_vocab = env.TranscriptVocabulary("work/dev_vocab.txt", ["buildLM/dev.txt"] + Glob("/mnt/asr/106-Delivery-Tagalog-v0.2g/conversational/dev/transcription/*"))
    #new_vocab = env.MissingVocabulary("work/missing_vocab.txt", ["%s/buildLM/lm.3gm.arpabo.gz" % experiment["IBM_PATH"], "%s/input/dict.train" % experiment["IBM_PATH"]])
    #midline_lm = env.AugmentLanguageModel(["work/new_dict.txt", "work/new_lm.gz"], [new_vocab, "%s/input/dict.test" % experiment["IBM_PATH"], "buildLM/lm.3gm.arpabo.gz"])
    model1_50k_dict, model1_50k_lm, model1_50k_vocab = env.AugmentLanguageModel(["work/model1_50k_dict.txt", "work/model1_50k_lm.gz", "work/model1_50k_vocab.txt"], 
                                                                                ["data/model1_50k.txt", "%s/input/dict.test" % experiment["IBM_PATH"], "buildLM/lm.3gm.arpabo.gz"])
    continue
    baseline = env.CreateASRDirectory(Dir(os.path.join("work", name)), Value({"LANGUAGE_MODEL" : os.path.join(experiment["IBM_PATH"], "buildLM", "lm.3gm.arpabo.gz"),
                                                                              "VOCABULARY" : os.path.join(experiment["IBM_PATH"], "input", "vocab"),
                                                                              "DICTIONARY" : os.path.join(experiment["IBM_PATH"], "input", "dict.test"),
                                                                              "DATABASE" : os.path.join(experiment["IBM_PATH"], "segment", "db", experiment["DATABASE"]),
                                                                              "DATA" : experiment["DATA_PATH"],
                                                                              "IBM_PATH" : experiment["IBM_PATH"],
                                                                              }))
    pass

    #pronunciation_model = env.TrainPronunciationModel("work/pronunciation_model_1.txt", ["input/dict.train", Value(5)])
    #for i in range(2, 6):
    #    pronunciation_model = env.TrainPronunciationModel("work/pronunciation_model_%d.txt" % i, ["input/dict.train", Value(5), pronunciation_model])

    #env.Experiment(env.Dir(os.path.join("work", name)), Value(experiment))
    #print name
    #audio_files = env.Glob(os.path.join(experiment["AUDIO_PATH"], "*"))
    #transcript_files = env.Glob(os.path.join(experiment["TRANSCRIPT_PATH"], "*"))
#    lexicons, locale, skip_roman = [experiment[x] for x in ["LEXICONS", "LOCALE", "SKIP_ROMAN"]]
#    base = os.path.join("work", name)
#    audio_path = experiment["PATH"]
#    env.BaseDictionary([os.path.join(base, x) for x in ["dictionary.txt", "phones.txt", "tags.txt"]], [Value(locale), Value(skip_roman)] + lexicons)
    #for data_type in ["training", "dev"]:
    #    env.CollectRawText(os.path.join(base, "%s_raw_text" % (data_type)), env.Glob(os.path.join(audio_path, "*", data_type, "transcription", "*")))

    #print name, audio_files, transcript_files
