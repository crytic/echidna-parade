import os.path

from glob import glob
from shutil import copy
from subprocess import Popen
from yaml import safe_load, dump
from random import choice, randrange


def create_base_echidna_config(config):
    base_config = {}
    if config.config is not None:
        y = safe_load(config.config)
        for key in y:
            if key not in [
                "timeout",
                "testLimit",
                "stopOnFail",
                "corpusDir",
                "coverage",
            ]:
                base_config[key] = y[key]
    base_config["timeout"] = config.gen_time
    base_config["testLimit"] = 1000000000  # basically infinite, use timeout to control
    if "seqLen" not in base_config:
        base_config["seqLen"] = min(max(config.minseqLen, 100), config.maxseqLen)
    if "dictFreq" not in base_config:
        base_config["dictFreq"] = 0.40
    if config.corpus_dir is not None:
        base_config["corpusDir"] = config.corpus_dir
    else:
        if config.resume is None:
            base_config["corpusDir"] = os.path.abspath(config.name + "/corpus")
        else:
            base_config["corpusDir"] = os.path.abspath(config.resume + "/corpus")
    base_config["stopOnFail"] = False
    base_config["coverage"] = True
    return base_config


def generate_echidna_config(
    rng, public, basic, bases, config, prefix=None, initial=False, coverage=False
):
    new_config = dict(basic)
    new_config["filterFunctions"] = []
    new_config["filterBlacklist"] = True
    if initial:
        new_config["timeout"] = config.initial_time
    if coverage:
        new_config["timeout"] = 360000
        corpus_count = len(glob(new_config["corpusDir"] + "/coverage/*.txt"))
        new_config["testLimit"] = corpus_count * config.maxseqLen
    basic_list = []
    blacklist = True
    if "filterFunctions" in basic:
        basic_list = basic["filterFunctions"]
        if "filterBlacklist" in basic:
            if not basic["filterBlacklist"]:
                blacklist = False
    excluded = []
    for f in public:
        if blacklist:
            if f in config.always:
                continue
            if f in basic_list:
                excluded.append(f)
            elif (not (initial or coverage)) and (rng.random() > config.prob):
                excluded.append(f)
        else:
            if f in config.always:
                continue
            if f in basic_list:
                if (not (initial or coverage)) and (rng.random() <= config.prob):
                    excluded.append(f)
            else:
                excluded.append(f)
    if (len(excluded) == len(public)) and (len(public) > 0):
        # This should be quite rare unless you have very few functions or a very low config.prob!
        print("Degenerate blacklist configuration, trying again...")
        return generate_config(
            rng, public, basic, bases, config, prefix, initial, coverage
        )
    new_config["filterFunctions"] = excluded
    if not (initial or coverage):
        new_config["corpusDir"] = "corpus"
        new_config["mutConsts"] = []
        for i in range(4):
            # The below is pretty ad-hoc, you can uses bases to over-ride
            new_config["mutConsts"].append(choice([0, 1, 2, 3, 1000, 2000]))
        if rng.random() < config.PdefaultLen:
            new_config["seqLen"] = randrange(config.minseqLen, config.maxseqLen)
        if rng.random() < config.PdefaultDict:
            new_config["dictFreq"] = randrange(5, 95) / 100.0
        if bases:
            base = rng.choose(bases)
            for k in base:
                new_config[k] = base[k]

    return new_config


def create_echidna_process(
    prefix,
    rng,
    public_functions,
    base_config,
    bases,
    config,
    initial=False,
    coverage=False,
):
    g = generate_echidna_config(
        rng,
        public_functions,
        base_config,
        bases,
        config,
        prefix=prefix,
        initial=initial,
        coverage=coverage,
    )
    print(
        "- LAUNCHING echidna-test in",
        prefix,
        "blacklisting [",
        ", ".join(g["filterFunctions"]),
        "] with seqLen",
        g["seqLen"],
        "dictFreq",
        g["dictFreq"],
        "and mutConsts ",
        g.setdefault("mutConsts", [1, 1, 1, 1]),
    )
    try:
        os.mkdir(prefix)
    except OSError:
        pass
    if not (initial or coverage):
        os.mkdir(prefix + "/corpus")
        os.mkdir(prefix + "/corpus/coverage")
        for f in glob(base_config["corpusDir"] + "/coverage/*.txt"):
            copy(f, prefix + "/corpus/coverage/")
    with open(prefix + "/config.yaml", "w") as yf:
        yf.write(dump(g))
        outf = open(prefix + "/echidna.out", "w")
        call = ["echidna-test"]
    call.extend(config.files)
    call.extend(["--config", "config.yaml"])
    if config.contract is not None:
        call.extend(["--contract", config.contract])
        call.extend(["--format", "text"])
    return (
        prefix,
        Popen(call, stdout=outf, stderr=outf, cwd=os.path.abspath(prefix)),
        outf,
    )


def detect_echidna_fail(failed_props, prefix):
    with open(prefix + "/echidna.out", "r") as ffile:
        for line in ffile:
            if "failed" in line[:-1]:
                if line[:-1] not in failed_props:
                    print("NEW FAILURE:", line[:-1])
                    failed_props[line[:-1]] = [prefix]
                else:
                    failed_props[line[:-1]].append(prefix)
