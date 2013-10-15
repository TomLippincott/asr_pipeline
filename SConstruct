import sys
import os.path
import logging
import asr_tools
from glob import glob

#
# load variable definitions from custom.py, and define them for SCons (seems like it should logically
# happen in the reverse order, but anyways...)
#
vars = Variables("custom.py")
vars.AddVariables(
    ("OUTPUT_WIDTH", "", 130),
    ("OUTPUT_PATH", "", ""),
    ("LANGUAGES", "", {}),
    ("ATTILA_PATH", "", ""),
    ("SEQUITUR_PATH", "", ""),
    ("ATTILA_INTERPRETER", "", "${ATTILA_PATH}/tools/attila/attila"),
    ("OUTPUT_PATH", "", ""),
    ("ADD_WORDS", "", "/usr/bin/add_words"),
    ("BABEL_REPO", "", None),
    ("BABEL_RESOURCES", "", None),
    ("F4DE", "", None),
    ("INDUS_DB", "", None),
    ("JAVA_NORM", "", "${BABEL_REPO}/KWS/examples/babel-dryrun/javabin"),
    ("OVERLAY", "", None),
    ("LIBRARY_OVERLAY", "", "${OVERLAY}/lib:${OVERLAY}/lib64"),
    ("EXPERIMENTS", "", {}),
    ("LANGUAGE_MODELS", "", {}),
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

for language, packs in env["LANGUAGES"].iteritems():
    for pack, locations in packs.iteritems():
        data = locations["data"]
        models = locations["models"]
        locale = locations["locale"]
        base_path = os.path.join("work", language, pack)
        output_path = os.path.join(env["OUTPUT_PATH"], language, pack)
        for x in ["baseline", "triple_oracle"]:
            try:
                os.makedirs(os.path.join(output_path, x))
            except:
                pass

        baseline_dictionary = env.File(os.path.join(models, "models", "dict.test"))
        baseline_vocab = env.File(os.path.join(models, "models", "vocab"))
        baseline_lm = env.File(os.path.join(models, "models", "lm.3gm.arpabo.gz"))


        # baseline experiment
        baseline = env.CreateSmallASRDirectory(Dir(os.path.join(base_path, "baseline")),
                                               [env.Value({"LANGUAGE_MODEL_FILE" : os.path.join(models, "models", "lm.3gm.arpabo.gz"),
                                                           "DICTIONARY_FILE" : os.path.join(models, "models", "dict.test"),
                                                           "VOCABULARY_FILE" : os.path.join(models, "models", "vocab"),
                                                           "DATABASE_FILE" : os.path.join(models, "segment", "babel106.dev.LimitedLP.seg.v1.db"),
                                                           "MEL_FILE" : os.path.join(models, "models", "mel"),
                                                           "PHONE_FILE" : os.path.join(models, "models", "pnsp"),
                                                           "PHONE_SET_FILE" : os.path.join(models, "models", "phonesset"),
                                                           "TAGS_FILE" : os.path.join(models, "models", "tags"),
                                                           "PRIORS_FILE" : os.path.join(models, "models", "priors"),
                                                           "TREE_FILE" : os.path.join(models, "models", "tree"),
                                                           "TOPO_FILE" : os.path.join(models, "models", "topo.tied"),
                                                           "TOPO_TREE_FILE" : os.path.join(models, "models", "topotree"),
                                                           "WARP_FILE" : os.path.join(models, "adapt", "warp.lst"),
                                                           "LDA_FILE" : os.path.join(models, "models", "30.mat"),
                                                           }),
                                                env.Value({"PCM_PATH" : data,
                                                           "OUTPUT_PATH" : os.path.join(output_path, "baseline"),
                                                           "CONFIGURATION_PATH" : os.path.join(base_path, "baseline"),
                                                           "CMS_PATH" : os.path.join(models, "adapt", "cms"),
                                                           "FMLLR_PATH" : os.path.join(models, "adapt", "fmllr"),
                                                           "MODEL_PATH" : os.path.join(models, "models"),
                                                           }),
                                                env.Value({"SAMPLING_RATE" : 8000,                    
                                                           "FEATURE_TYPE" : "plp",
                                                           "AC_WEIGHT" : 0.053,
                                                           "MAX_ERROR" : 15000,
                                                           "USE_DISPATCHER" : False,
                                                           })
                                                ])

        # triple oracle experiment
        oracle_dictionary, oracle_pnsp, oracle_tags = env.AppenToAttila([os.path.join(base_path, x) for x in ["oracle_dictionary.txt", "oracle_pnsp.txt", "oracle_tags.txt"]],
                                                                        [os.path.join(data, "conversational", "reference_materials", "lexicon.txt"),
                                                                         os.path.join(data, "scripted", "reference_materials", "lexicon.txt"),
                                                                         env.Value(locale)])
        oracle_text, oracle_text_words = env.CollectText([os.path.join(base_path, x) for x in ["oracle_text.txt", "oracle_text_words.txt"]], 
                                                         [env.Dir(x) for x in glob(os.path.join(data, "*/*/transcription"))])
        oracle_vocabulary = env.DictionaryToVocabulary(os.path.join(base_path, "oracle_vocabulary.txt"), oracle_dictionary)
        oracle_lm = env.IBMTrainLanguageModel(os.path.join(base_path, "oracle_lm.3gm.arpabo.gz"), [oracle_text, oracle_text_words, env.Value(3)])
        triple_oracle = env.CreateSmallASRDirectory(Dir(os.path.join(base_path, "triple_oracle")),
                                               [env.Value({"LANGUAGE_MODEL_FILE" : oracle_lm[0], #os.path.join(models, "models", "lm.3gm.arpabo.gz"),
                                                           "DICTIONARY_FILE" : oracle_dictionary, #os.path.join(models, "models", "dict.test"),
                                                           "VOCABULARY_FILE" : oracle_vocabulary[0], #os.path.join(models, "models", "vocab"),
                                                           "DATABASE_FILE" : os.path.join(models, "segment", "babel106.dev.LimitedLP.seg.v1.db"),
                                                           "MEL_FILE" : os.path.join(models, "models", "mel"),
                                                           "PHONE_FILE" : os.path.join(models, "models", "pnsp"),
                                                           "PHONE_SET_FILE" : os.path.join(models, "models", "phonesset"),
                                                           "TAGS_FILE" : os.path.join(models, "models", "tags"),
                                                           "PRIORS_FILE" : os.path.join(models, "models", "priors"),
                                                           "TREE_FILE" : os.path.join(models, "models", "tree"),
                                                           "TOPO_FILE" : os.path.join(models, "models", "topo.tied"),
                                                           "TOPO_TREE_FILE" : os.path.join(models, "models", "topotree"),
                                                           "WARP_FILE" : os.path.join(models, "adapt", "warp.lst"),
                                                           "LDA_FILE" : os.path.join(models, "models", "30.mat"),
                                                           }),
                                                env.Value({"PCM_PATH" : data,
                                                           "OUTPUT_PATH" : os.path.join(output_path, "triple_oracle"),
                                                           "CONFIGURATION_PATH" : os.path.join(base_path, "triple_oracle"),
                                                           "CMS_PATH" : os.path.join(models, "adapt", "cms"),
                                                           "FMLLR_PATH" : os.path.join(models, "adapt", "fmllr"),
                                                           "MODEL_PATH" : os.path.join(models, "models"),
                                                           }),
                                                env.Value({"SAMPLING_RATE" : 8000,                    
                                                           "FEATURE_TYPE" : "plp",
                                                           "AC_WEIGHT" : 0.053,
                                                           "MAX_ERROR" : 15000,
                                                           "USE_DISPATCHER" : False,
                                                           })
                                                ])
        

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
# build all language models
#
#language_models = {}
#for name, config in env["LANGUAGE_MODELS"].iteritems():
#    full_config = {"NAME" : name}
#    full_config.update(config)
#    language_models[name] = env.AugmentLanguageModel([], env.Value(full_config))

    #env.AugmentLanguageModel(["work/model1_50k_lm.arpabo.gz", "work/model1_50k_vocab.txt", "work/model1_50k_dict.txt"],
    #                                                                            [experiment["FILES"]["LANGUAGE_MODEL_FILE"],
    #                                                                             experiment["FILES"]["DICTIONARY_FILE"],
    #                                                                             "data/model1_50k.txt",
    #                                                                             Value(.1),
    #                                                                             ])
    #
    #model1_50k_lm, model1_50k_vocab, model1_50k_dict = 
    #env.AugmentLanguageModel(["work/model1_50k_lm.arpabo.gz", "work/model1_50k_vocab.txt", "work/model1_50k_dict.txt"],
    #                                                                            [experiment["FILES"]["LANGUAGE_MODEL_FILE"],
    #                                                                             experiment["FILES"]["DICTIONARY_FILE"],
    #                                                                             "data/model1_50k.txt",
    #                                                                             Value(.1),
    #                                                                             ])


#
# run all the experiments in EXPERIMENTS (defined in custom.py)
#
#for name, experiment in env["EXPERIMENTS"].iteritems():
#    base_path = experiment["DIRECTORIES"]["CONFIGURATION_PATH"]

    #topline_text = env.CollectText(os.path.join(base_path, "all_transcripts.txt"), [env.Dir(x) for x in glob(os.path.join(experiment["DIRECTORIES"]["PCM_PATH"], "*/*/transcription"))])
    #all_vocab = env.TranscriptVocabulary(os.path.join(base_path, "all_vocab.txt"), topline_text)

    #database_file, data_path, output_path, language_model_file, dictionary_file = [experiment[x] for x in ["DATABASE_FILE", "DATA_PATH", "OUTPUT_PATH", "LANGUAGE_MODEL_FILE", "DICTIONARY_FILE"]]
    # "DICTIONARY_FILE", "LANGUAGE_MODEL_FILE", "VOCABULARY_FILE"
#    baseline = env.CreateSmallASRDirectory(Dir(os.path.join(base_path, "baseline")),
#                                           [env.Value(experiment["FILES"]),
#                                            env.Value(experiment["DIRECTORIES"]),
#                                            env.Value(experiment["PARAMETERS"]),
#                                            ])

    #model1_50k_experiment = experiment
    #model1_50k_experiment["FILES"]["LANGUAGE_MODEL_FILE"] = model1_50k_lm.rstr()
    #model1_50k_experiment["FILES"]["VOCABULARY_FILE"] = model1_50k_vocab.rstr()
    #model1_50k_experiment["FILES"]["DICTIONARY_FILE"] = model1_50k_dict.rstr()
    #model1_50k_experiment["DIRECTORIES"]["OUTPUT_PATH"] = ""
    # baseline = env.CreateSmallASRDirectory(Dir(os.path.join(base_path, "baseline")),
    #                                        [env.Value(model1_50k_experiment["FILES"]),
    #                                         env.Value(model1_50k_experiment["DIRECTORIES"]),
    #                                         env.Value(model1_50k_experiment["PARAMETERS"]),
    #                                         ])
                                      #database_file,
                                      # language_model_file,
                                      # dictionary_file,
                                       
                                      # mel
                                      # ps
                                      # pss
                                      # tags
                                      # tree
                                       # topo
                                      # topotree
                                      #Dir(experiment["DATA_PATH"]),
                                      #Dir(experiment["IBM_PATH"]),
                                      #Dir(os.path.join(experiment["OUTPUT_PATH"], "baseline"))
                                      #)


    # for mass in [.01, .05, .1, .2, .4, .8]:
    #     base = os.path.join("work", "%s_midline_%f" % (name, mass))
    #     midline_lm, midline_vocab, midline_dict = env.AugmentLanguageModel([os.path.join(base, x) for x in ["midline_lm.arpabo.gz", "midline_vocab.txt", "midline_dict.txt"]],
    #                                                                        [os.path.join(experiment["IBM_PATH"], "buildLM/lm.3gm.arpabo.gz"),
    #                                                                         os.path.join(experiment["IBM_PATH"], "input/dict.test"),
    #                                                                         os.path.join(experiment["IBM_PATH"], "input/dict.train"),
    #                                                                         Value(mass),
    #                                                                         ])
    
    #     midline = env.CreateASRDirectory(Dir(base),
    #                                      [midline_lm,
    #                                       midline_vocab,
    #                                       midline_dict,
    #                                       os.path.join(experiment["IBM_PATH"], "segment", "db", experiment["DATABASE"]),
    #                                       Dir(experiment["DATA_PATH"]),
    #                                       Dir(experiment["IBM_PATH"]),
    #                                       Dir(os.path.join(experiment["OUTPUT_PATH"], "%s_midline_%f" % (name, mass)))
    #                                       ])




    # model1_50k_lm, model1_50k_vocab, model1_50k_dict = env.AugmentLanguageModel(["work/model1_50k_lm.arpabo.gz", "work/model1_50k_vocab.txt", "work/model1_50k_dict.txt"],
    #                                                                             [os.path.join(experiment["IBM_PATH"], "buildLM/lm.3gm.arpabo.gz"),
    #                                                                              os.path.join(experiment["IBM_PATH"], "input/dict.test"),
    #                                                                              "data/model1_50k.txt",
    #                                                                              Value(.1),
    #                                                                              ])


    # model1_50k = env.CreateASRDirectory(Dir(os.path.join("work", "%s_model1_50k" % name)),
    #                                     [model1_50k_lm,
    #                                      model1_50k_vocab,
    #                                      model1_50k_dict,
    #                                      os.path.join(experiment["IBM_PATH"], "segment", "db", experiment["DATABASE"]),
    #                                      Dir(experiment["DATA_PATH"]),
    #                                      Dir(experiment["IBM_PATH"]),
    #                                      Dir(os.path.join(experiment["OUTPUT_PATH"], "model1_50k"))
    #                                      ])

    #pronunciation_model = env.TrainPronunciationModel("work/pronunciation_model_1.txt", ["input/dict.train", Value(5)])
    #for i in range(2, 6):
    #    pronunciation_model = env.TrainPronunciationModel("work/pronunciation_model_%d.txt" % i, ["input/dict.train", Value(5), pronunciation_model])
    #env.Experiment(env.Dir(os.path.join("work", name)), Value(experiment))
    #audio_files = env.Glob(os.path.join(experiment["AUDIO_PATH"], "*"))
    #transcript_files = env.Glob(os.path.join(experiment["TRANSCRIPT_PATH"], "*"))
    #lexicons, locale, skip_roman = [experiment[x] for x in ["LEXICONS", "LOCALE", "SKIP_ROMAN"]]
    #base = os.path.join("work", name)
    #audio_path = experiment["PATH"]
    #env.BaseDictionary([os.path.join(base, x) for x in ["dictionary.txt", "phones.txt", "tags.txt"]], [Value(locale), Value(skip_roman)] + lexicons)
    #for data_type in ["training", "dev"]:
    #    env.CollectRawText(os.path.join(base, "%s_raw_text" % (data_type)), env.Glob(os.path.join(audio_path, "*", data_type, "transcription", "*")))
