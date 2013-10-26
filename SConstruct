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
            
        # baseline experiment
        baseline_vocab = env.File(os.path.join(models, "models", "vocab"))
        baseline_pronunciations = env.File(os.path.join(models, "models", "dict.test"))
        baseline_lm = env.File(os.path.join(models, "models", "lm.3gm.arpabo.gz"))
        baseline_experiment = env.CreateSmallASRDirectory(Dir(os.path.join("work", "experiments", language, pack, "baseline", "baseline", "baseline")), 
                                                          experiment({"VOCABULARY_FILE" : baseline_vocab.rstr(),
                                                                      "PRONUNCIATIONS_FILE" : baseline_pronunciations.rstr(),
                                                                      "LANGUAGE_MODEL_FILE" : baseline_lm.rstr(),
                                                                      "OUTPUT_PATH" : os.path.join(env["OUTPUT_PATH"], language, pack, "baseline", "baseline", "baseline"),
                                                                      })
                                                          )

        # triple-oracle experiment
        oracle_pronunciations, oracle_pnsp, oracle_tags = env.AppenToAttila([os.path.join(base_path, x) for x in ["oracle_pronunciations.txt", "oracle_pnsp.txt", "oracle_tags.txt"]],
                                                                        [os.path.join(data, "conversational", "reference_materials", "lexicon.txt"),
                                                                         os.path.join(data, "scripted", "reference_materials", "lexicon.txt"),
                                                                         env.Value(locale)])
        oracle_text, oracle_text_words = env.CollectText([os.path.join(base_path, x) for x in ["oracle_text.txt", "oracle_text_words.txt"]], 
                                                         [env.Dir(x) for x in glob(os.path.join(data, "*/*/transcription"))])
        oracle_vocabulary = env.PronunciationsToVocabulary(os.path.join(base_path, "oracle_vocabulary.txt"), oracle_pronunciations)
        oracle_lm = env.IBMTrainLanguageModel(os.path.join(base_path, "oracle_lm.3gm.arpabo.gz"), [oracle_text, oracle_text_words, env.Value(3)])


        oracle_path = os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle")
        triple_oracle_experiment = env.CreateSmallASRDirectory(Dir(os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle")),
                                                               experiment({"VOCABULARY_FILE" : oracle_vocabulary[0].rstr(),
                                                                           "PRONUNCIATIONS_FILE" : oracle_pronunciations.rstr(),
                                                                           "LANGUAGE_MODEL_FILE" : oracle_lm[0].rstr(),
                                                                           "OUTPUT_PATH" : os.path.join(env["OUTPUT_PATH"], language, pack, "oracle", "oracle", "oracle"),
                                                                           })
                                                               )
        
        construct = env.SubmitJob(os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle", "construct.timestamp"), 
                                  [triple_oracle_experiment, env.Value({"name" : "construct",
                                                                        "commands" : ["${ATTILA_PATH}/tools/attila/attila construct.py"],
                                                                        "path" : oracle_path,
                                                                         })])

        #test = env.SubmitJob(os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle", "test.timestamp"), 
        #                     [construct])

        #score = env.SubmitJob(os.path.join("work", "experiments", language, pack, "oracle", "oracle", "oracle", "score.timestamp"), 
        #                      [test])

        # babelgum experiments
        for model, (probs, prons) in locations.get("babelgum", {}).iteritems():
            continue
            for size in [50000]:
                all_bg_probabilities, all_bg_pronunciations = env.BabelGumLexicon([os.path.join(base_path, x) for x in ["babelgum_%s_%d_probabilities.txt" % (model, size), 
                                                                                                                        "babelgum_%s_%d_pronunciations.txt" % (model, size)]], 
                                                                                  [probs, prons, env.Value(size)])
                env.NoClean([all_bg_probabilities, all_bg_pronunciations])


                bg_pron_correct_pron, bg_vocab_correct_pron = env.ReplacePronunciations(
                    [os.path.join(base_path, x) for x in ["bg_%s_%d_pron_correct_pron.txt" % (model, size), "bg_%s_%d_vocab_correct_pron.txt" % (model, size)]],
                    [all_bg_pronunciations, oracle_pronunciations])

                for weight in [.1]:
                    bg_vocab, bg_pron, bg_lm = env.AugmentLanguageModel(
                        [os.path.join(base_path, "bg_%s_%d_%f_noprobabilities_%s" % (model, size, weight, x)) for x in ["vocab.txt", "pronunciations.txt", "lm.3gm.arpabo.gz"]],
                        [baseline_pronunciations, baseline_lm, all_bg_pronunciations, env.Value(weight)]
                        )

                    babelgum_experiment = env.CreateSmallASRDirectory(Dir(os.path.join("work", "experiments", language, pack, "babelgum", "babelgum", "babelgum")),
                                                                      experiment({"VOCABULARY_FILE" : bg_vocab.rstr(),
                                                                                  "PRONUNCIATIONS_FILE" : bg_pron.rstr(),
                                                                                  "LANGUAGE_MODEL_FILE" : bg_lm.rstr(),
                                                                                  "OUTPUT_PATH" : os.path.join(env["OUTPUT_PATH"], language, pack, "babelgum", "babelgum", "babelgum"),
                                                                                  })
                                                                      )

                    lim_bg_pronunciations , lim_bg_probabilities = env.FilterBabelGum([os.path.join(base_path, "babelgum_basic_50000_lim_%s.txt") for x in ["pronunciations", "probabilities"]],
                                                                                      [all_bg_pronunciations, all_bg_probabilities, oracle_vocabulary])

                    #bg_vocab_lim, bg_pron_lim, bg_lm_lim = env.AugmentLanguageModel(
                    #    [os.path.join(base_path, "bg_%s_%d_%f_noprobabilities_%s" % (model, size, weight, x)) for x in ["vocab_lim.txt", "pronunciations_lim.txt", "lim_lm.3gm.arpabo.gz"]],
                    #    [baseline_pronunciations, baseline_lm, lim_bg_pronunciations, env.Value(weight)]
                    #    )

                    #bg_vocab_lim, bg_pron_lim, bg_lm_lim = env.FilterWords(
                    #    [os.path.join(base_path, "bg_%s_%d_%f_noprobabilities_%s" % (model, size, weight, x)) for x in ["vocab_lim.txt", "pronunciations_lim.txt", "lim_lm.3gm.arpabo.gz"]],
                    #    [bg_vocab, bg_pron, bg_lm, oracle_vocabulary]
                    #    )

                    #babelgum_limited_experiment = env.CreateSmallASRDirectory(Dir(os.path.join("work", "experiments", language, pack, "limited_babelgum", "babelgum", "babelgum")),
                    #                                                  experiment({"VOCABULARY_FILE" : bg_vocab_lim.rstr(),
                    #                                                              "PRONUNCIATIONS_FILE" : bg_pron_lim.rstr(),
                    #                                                              "LANGUAGE_MODEL_FILE" : bg_lm_lim.rstr(),
                    #                                                              "OUTPUT_PATH" : os.path.join(env["OUTPUT_PATH"], language, pack, "limited_babelgum", "babelgum", "babelgum"),
                    #                                                              })
                    #                                                  )
                
