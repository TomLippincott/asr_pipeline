import sys
import os.path
import logging
from glob import glob
import asr_tools
import mpi_tools

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
    ("PYTHON_INTERPRETER", "", None),
    ("SCORE_SCRIPT", "", None),
    ("INDUS_DB", "", None),
    ("SCLITE_BINARY", "", None),
    ("JAVA_NORM", "", "${BABEL_REPO}/KWS/examples/babel-dryrun/javabin"),
    ("OVERLAY", "", None),
    ("LIBRARY_OVERLAY", "", "${OVERLAY}/lib:${OVERLAY}/lib64"),
    ("EXPERIMENTS", "", {}),
    ("LANGUAGE_MODELS", "", {}),
    ("LOG_LEVEL", "", logging.INFO),
    ("LOG_DESTINATION", "", sys.stdout),
    ("HAS_TORQUE", "", False),
    )

#
# create the actual build environment we'll be using: basically, just import the builders from site_scons/kws_tools.py
#
env = Environment(variables=vars, ENV={}, TARFLAGS="-c -z", TARSUFFIX=".tgz",
                  tools=["default", "textfile"] + [x.TOOLS_ADD for x in [asr_tools, mpi_tools]],
                  BUILDERS={"CopyFile" : Builder(action="cp ${SOURCE} ${TARGET}")}
                  )

#
# initialize the Python logging system (though we don't really use it in this build, could be useful later)
#
if isinstance(env["LOG_DESTINATION"], basestring):
    logging.basicConfig(format="\t%(asctime)s %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"], filename=env["LOG_DESTINATION"])
else:
    logging.basicConfig(format="\t%(asctime)s %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"])

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

# always refer to sets of lexicon files in the order: vocabulary, pronunciations, language model

scores = []

for language, packs in env["LANGUAGES"].iteritems():
    for pack, locations in packs.iteritems():
        data = locations["data"]
        models = locations["models"]
        locale = locations["locale"]
        base_path = os.path.join("work", language, pack)
        output_path = os.path.join(env["OUTPUT_PATH"], language, pack)
        
        def experiment(substitutions={}):
            files = {"LANGUAGE_MODEL_FILE" : None, #os.path.join(models, "models", "lm.3gm.arpabo.gz"),
                     "PRONUNCIATIONS_FILE" : None, #os.path.join(models, "models", "dict.test"),
                     "VOCABULARY_FILE" : None, #os.path.join(models, "models", "vocab"),
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
                     }
            directories = {"PCM_PATH" : data,
                           "OUTPUT_PATH" : None, #os.path.join(output_path, "baseline"),
                           "CMS_PATH" : os.path.join(models, "adapt", "cms"),
                           "FMLLR_PATH" : os.path.join(models, "adapt", "fmllr"),
                           "MODEL_PATH" : os.path.join(models, "models"),
                           }
            parameters = {"SAMPLING_RATE" : 8000,                    
                          "FEATURE_TYPE" : "plp",
                          "AC_WEIGHT" : 0.053,
                          "MAX_ERROR" : 15000,
                          "USE_DISPATCHER" : False,
                          }

            for k in files.keys():
                files[k] = substitutions.get(k, files[k])

            for k in directories.keys():
                directories[k] = substitutions.get(k, directories[k])

            for k in parameters.keys():
                parameters[k] = parameters.get(k, parameters[k])
                
            return [env.Value(x) for x in [files, directories, parameters]]


        def submit(path, setup):
            if not env["HAS_TORQUE"]:
                return
            construct = env.SubmitJob(os.path.join(path, "construct.timestamp"), 
                                      [setup, env.Value({"name" : "construct",
                                                                       "commands" : ["${ATTILA_PATH}/tools/attila/attila construct.py"],
                                                                       "path" : path,
                                                                       "other" : ["#PBS -W group_list=yeticcls"],
                                                                       "interval" : 10,
                                                                       })])
            
            test = env.SubmitJob(os.path.join(path, "test.timestamp"), 
                                 [construct, env.Value({"name" : "test",
                                                        "commands" : ["${ATTILA_PATH}/tools/attila/attila test.py -w %f -n %s -j $${PBS_ARRAYID} -l 1" % (.13, 50)],
                                                        "path" : path,
                                                        "array" : 20,
                                                        "other" : ["#PBS -W group_list=yeticcls"],
                                                        "interval" : 120,
                                                        })])

            score = env.ScoreResults(os.path.join(path, "ctm", "scoring", "babel106.dev.sys"), 
                                     [env.Value("106.dev"), env.Value(os.path.abspath(os.path.join(path, "ctm")))])
            env.Depends(score, test)
            return score


        # baseline experiment
        baseline_path = os.path.join("work", "experiments", language, pack, "baseline", "baseline", "baseline")
        baseline_vocabulary = env.File(os.path.join(models, "models", "vocab"))
        baseline_pronunciations = env.File(os.path.join(models, "models", "dict.test"))
        baseline_languagemodel = env.File(os.path.join(models, "models", "lm.3gm.arpabo.gz"))

        baseline_experiment = env.CreateSmallASRDirectory(Dir(baseline_path), 
                                                          experiment({"VOCABULARY_FILE" : baseline_vocabulary.rstr(),
                                                                      "PRONUNCIATIONS_FILE" : baseline_pronunciations.rstr(),
                                                                      "LANGUAGE_MODEL_FILE" : baseline_languagemodel.rstr(),
                                                                      "OUTPUT_PATH" : baseline_path,
                                                                      })
                                                          )
        scores.append(submit(baseline_path, baseline_experiment))

        # triple-oracle experiment
        oracle_pronunciations, oracle_pnsp, oracle_tags = env.AppenToAttila([os.path.join(base_path, x) for x in ["oracle_pronunciations.txt", "oracle_pnsp.txt", "oracle_tags.txt"]],
                                                                        [os.path.join(data, "conversational", "reference_materials", "lexicon.txt"),
                                                                         os.path.join(data, "scripted", "reference_materials", "lexicon.txt"),
                                                                         env.Value(locale)])
        oracle_text, oracle_text_words = env.CollectText([os.path.join(base_path, x) for x in ["oracle_text.txt", "oracle_text_words.txt"]], 
                                                         [env.Dir(x) for x in glob(os.path.join(data, "*/*/transcription"))])
        oracle_vocabulary = env.PronunciationsToVocabulary(os.path.join(base_path, "oracle_vocabulary.txt"), oracle_pronunciations)
        oracle_languagemodel = env.IBMTrainLanguageModel(os.path.join(base_path, "oracle_lm.3gm.arpabo.gz"), [oracle_text, oracle_text_words, env.Value(3)])


        oracle_path = os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle")
        triple_oracle_experiment = env.CreateSmallASRDirectory(Dir(os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle")),
                                                               experiment({"VOCABULARY_FILE" : oracle_vocabulary[0].rstr(),
                                                                           "PRONUNCIATIONS_FILE" : oracle_pronunciations.rstr(),
                                                                           "LANGUAGE_MODEL_FILE" : oracle_languagemodel[0].rstr(),
                                                                           "OUTPUT_PATH" : oracle_path,
                                                                           })
                                                               )
        scores.append(submit(oracle_path, triple_oracle_experiment))

        # babelgum experiments
        for model, (probs, prons) in locations.get("babelgum", {}).iteritems():
            for size in [50000]:
                babelgum_probabilities, babelgum_pronunciations = env.BabelGumLexicon([os.path.join(base_path, x) for x in ["babelgum_%s_%d_probabilities.txt" % (model, size), 
                                                                                                                            "babelgum_%s_%d_pronunciations.txt" % (model, size)]], 
                                                                                      [probs, prons, env.Value(size)])
                env.NoClean([babelgum_probabilities, babelgum_pronunciations])


                babelgum_correct_pronunciations_pronunciations, babelgum_correct_pronunciations_vocabulary = env.ReplacePronunciations(
                    [os.path.join(base_path, x) for x in ["babelgum_correct_pronunciations_%s_%d_pronunciations.txt" % (model, size), 
                                                          "babelgum_correct_pronunciations_%s_%d_vocabulary.txt" % (model, size)]],
                    [babelgum_pronunciations, oracle_pronunciations])


                babelgum_rightwords_pronunciations, babelgum_rightwords_probabilities = \
                    env.FilterBabelGum([os.path.join(base_path, "babelgum_rightwords_50000_%s.txt" % x) for x in ["pronunciations", "probabilities"]],
                                       [babelgum_pronunciations, babelgum_probabilities, oracle_vocabulary])

                babelgum_rightwords_rightpronunciations_pronunciations, babelgum_rightwords_rightpronunciations_vocabulary = env.ReplacePronunciations(
                    [os.path.join(base_path, x) for x in ["babelgum_rightwords_rightpronunciations_%s_%d_pronunciations.txt" % (model, size), 
                                                          "babelgum_rightwords_rightpronunciations_%s_%d_vocabulary.txt" % (model, size)]],
                    [babelgum_rightwords_pronunciations, oracle_pronunciations])

                for weight in [.1]:

                    # adding all babelgum vocabulary (uniform)
                    babelgum_uniform_vocabulary, babelgum_uniform_pronunciations, babelgum_uniform_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_uniform_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_pronunciations, env.Value(weight)]
                        )


                    babelgum_uniform_path = os.path.join("work", "experiments", language, pack, "babelgum", "babelgum", "uniform")
                    babelgum_uniform_experiment = env.CreateSmallASRDirectory(Dir(babelgum_uniform_path),
                                                                              experiment({"VOCABULARY_FILE" : babelgum_uniform_vocabulary.rstr(),
                                                                                          "PRONUNCIATIONS_FILE" : babelgum_uniform_pronunciations.rstr(),
                                                                                          "LANGUAGE_MODEL_FILE" : babelgum_uniform_languagemodel.rstr(),
                                                                                          "OUTPUT_PATH" : babelgum_uniform_path,
                                                                                          })
                                                                              )
                    scores.append(submit(babelgum_uniform_path, babelgum_uniform_experiment))

                    # adding all babelgum vocabulary (weighted)
                    babelgum_weighted_vocabulary, babelgum_weighted_pronunciations, babelgum_weighted_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_weighted_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_pronunciations, babelgum_probabilities, env.Value(weight)]
                        )

                    babelgum_weighted_path = os.path.join("work", "experiments", language, pack, "babelgum", "babelgum", "babelgum")
                    babelgum_weighted_experiment = env.CreateSmallASRDirectory(Dir(babelgum_weighted_path),
                                                                              experiment({"VOCABULARY_FILE" : babelgum_weighted_vocabulary.rstr(),
                                                                                          "PRONUNCIATIONS_FILE" : babelgum_weighted_pronunciations.rstr(),
                                                                                          "LANGUAGE_MODEL_FILE" : babelgum_weighted_languagemodel.rstr(),
                                                                                          "OUTPUT_PATH" : babelgum_weighted_path,
                                                                                          })
                                                                              )
                    scores.append(submit(babelgum_weighted_path, babelgum_weighted_experiment))

                    # adding all babelgum terms with corrected pronunciations (uniform)
                    babelgum_uniform_corrected_vocabulary, babelgum_uniform_corrected_pronunciations, babelgum_uniform_corrected_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_uniform_corrected_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_correct_pronunciations_pronunciations, env.Value(weight)]
                        )


                    babelgum_uniform_corrected_path = os.path.join("work", "experiments", language, pack, "babelgum", "babelgum_corrected", "uniform")
                    babelgum_uniform_corrected_experiment = env.CreateSmallASRDirectory(Dir(babelgum_uniform_corrected_path),
                                                                                        experiment({"VOCABULARY_FILE" : babelgum_uniform_corrected_vocabulary.rstr(),
                                                                                                    "PRONUNCIATIONS_FILE" : babelgum_uniform_corrected_pronunciations.rstr(),
                                                                                                    "LANGUAGE_MODEL_FILE" : babelgum_uniform_corrected_languagemodel.rstr(),
                                                                                                    "OUTPUT_PATH" : babelgum_uniform_corrected_path,
                                                                                                    })
                                                                                        )
                    scores.append(submit(babelgum_uniform_corrected_path, babelgum_uniform_corrected_experiment))

                    # adding all babelgum terms with corrected pronunciations (weighted)
                    babelgum_weighted_corrected_vocabulary, babelgum_weighted_corrected_pronunciations, babelgum_weighted_corrected_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_weighted_corrected_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_correct_pronunciations_pronunciations, babelgum_probabilities, env.Value(weight)]
                        )


                    babelgum_weighted_corrected_path = os.path.join("work", "experiments", language, pack, "babelgum", "babelgum_corrected", "weighted")
                    babelgum_weighted_corrected_experiment = env.CreateSmallASRDirectory(Dir(babelgum_weighted_corrected_path),
                                                                                        experiment({"VOCABULARY_FILE" : babelgum_weighted_corrected_vocabulary.rstr(),
                                                                                                    "PRONUNCIATIONS_FILE" : babelgum_weighted_corrected_pronunciations.rstr(),
                                                                                                    "LANGUAGE_MODEL_FILE" : babelgum_weighted_corrected_languagemodel.rstr(),
                                                                                                    "OUTPUT_PATH" : babelgum_weighted_corrected_path,
                                                                                                    })
                                                                                        )
                    scores.append(submit(babelgum_weighted_corrected_path, babelgum_weighted_corrected_experiment))


                    # adding just correct babelgum terms (uniform)
                    babelgum_rightwords_uniform_vocabulary, babelgum_rightwords_uniform_pronunciations, babelgum_rightwords_uniform_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_rightwords_uniform_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_rightwords_pronunciations, env.Value(weight)]
                        )

                    babelgum_rightwords_uniform_path = os.path.join("work", "experiments", language, pack, "babelgum_corrected", "babelgum", "uniform")
                    babelgum_rightwords_uniform_experiment = env.CreateSmallASRDirectory(Dir(babelgum_rightwords_uniform_path),
                                                                                         experiment({"VOCABULARY_FILE" : babelgum_rightwords_uniform_vocabulary.rstr(),
                                                                                                     "PRONUNCIATIONS_FILE" : babelgum_rightwords_uniform_pronunciations.rstr(),
                                                                                                     "LANGUAGE_MODEL_FILE" : babelgum_rightwords_uniform_languagemodel.rstr(),
                                                                                                     "OUTPUT_PATH" : babelgum_rightwords_uniform_path,
                                                                                                     })
                                                                                         )
                    scores.append(submit(babelgum_rightwords_uniform_path, babelgum_rightwords_uniform_experiment))


                    # adding just correct babelgum terms (weighted)
                    babelgum_rightwords_weighted_vocabulary, babelgum_rightwords_weighted_pronunciations, babelgum_rightwords_weighted_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_rightwords_weighted_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_rightwords_pronunciations, babelgum_rightwords_probabilities, env.Value(weight)]
                        )

                    babelgum_rightwords_weighted_path = os.path.join("work", "experiments", language, pack, "babelgum_corrected", "babelgum", "weighted")
                    babelgum_rightwords_weighted_experiment = env.CreateSmallASRDirectory(Dir(babelgum_rightwords_weighted_path),
                                                                                         experiment({"VOCABULARY_FILE" : babelgum_rightwords_weighted_vocabulary.rstr(),
                                                                                                     "PRONUNCIATIONS_FILE" : babelgum_rightwords_weighted_pronunciations.rstr(),
                                                                                                     "LANGUAGE_MODEL_FILE" : babelgum_rightwords_weighted_languagemodel.rstr(),
                                                                                                     "OUTPUT_PATH" : babelgum_rightwords_weighted_path,
                                                                                                     })
                                                                                         )
                    scores.append(submit(babelgum_rightwords_weighted_path, babelgum_rightwords_weighted_experiment))


                    # adding just correct babelgum terms with corrected pronunciations (uniform)
                    babelgum_rightwords_rightpronunciations_uniform_vocabulary, babelgum_rightwords_rightpronunciations_uniform_pronunciations, babelgum_rightwords_rightpronunciations_uniform_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_rightwords_rightpronunciations_uniform_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_rightwords_rightpronunciations_pronunciations, env.Value(weight)]
                        )

                    babelgum_rightwords_rightpronunciations_uniform_path = os.path.join("work", "experiments", language, pack, "babelgum_corrected", "babelgum_corrected", "uniform")
                    babelgum_rightwords_rightpronunciations_uniform_experiment = env.CreateSmallASRDirectory(Dir(babelgum_rightwords_rightpronunciations_uniform_path),
                                                                                         experiment({"VOCABULARY_FILE" : babelgum_rightwords_rightpronunciations_uniform_vocabulary.rstr(),
                                                                                                     "PRONUNCIATIONS_FILE" : babelgum_rightwords_rightpronunciations_uniform_pronunciations.rstr(),
                                                                                                     "LANGUAGE_MODEL_FILE" : babelgum_rightwords_rightpronunciations_uniform_languagemodel.rstr(),
                                                                                                     "OUTPUT_PATH" : babelgum_rightwords_rightpronunciations_uniform_path,
                                                                                                     })
                                                                                         )
                    scores.append(submit(babelgum_rightwords_rightpronunciations_uniform_path, babelgum_rightwords_rightpronunciations_uniform_experiment))


                    # adding just correct babelgum terms with corrected pronunciations (weighted)
                    babelgum_rightwords_rightpronunciations_weighted_vocabulary, babelgum_rightwords_rightpronunciations_weighted_pronunciations, babelgum_rightwords_rightpronunciations_weighted_languagemodel = env.AugmentLanguageModel(
                        [os.path.join(base_path, "babelgum_rightwords_rightpronunciations_weighted_%s_%d_%f_%s" % (model, size, weight, x)) for x in ["vocabulary.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_languagemodel, babelgum_rightwords_rightpronunciations_pronunciations, babelgum_rightwords_probabilities, env.Value(weight)]
                        )

                    babelgum_rightwords_rightpronunciations_weighted_path = os.path.join("work", "experiments", language, pack, "babelgum_corrected", "babelgum_corrected", "weighted")
                    babelgum_rightwords_rightpronunciations_weighted_experiment = env.CreateSmallASRDirectory(Dir(babelgum_rightwords_rightpronunciations_weighted_path),
                                                                                         experiment({"VOCABULARY_FILE" : babelgum_rightwords_rightpronunciations_weighted_vocabulary.rstr(),
                                                                                                     "PRONUNCIATIONS_FILE" : babelgum_rightwords_rightpronunciations_weighted_pronunciations.rstr(),
                                                                                                     "LANGUAGE_MODEL_FILE" : babelgum_rightwords_rightpronunciations_weighted_languagemodel.rstr(),
                                                                                                     "OUTPUT_PATH" : babelgum_rightwords_rightpronunciations_weighted_path,
                                                                                                     })
                                                                                         )
                    scores.append(submit(babelgum_rightwords_rightpronunciations_weighted_path, babelgum_rightwords_rightpronunciations_weighted_experiment))
