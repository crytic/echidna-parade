import time
import os.path

from glob import glob
from shutil import copy
from slither import Slither
from sys import exit
from random import Random
from yaml import safe_load

from echidna_parade.echidna import (
    create_base_echidna_config,
    generate_echidna_config,
    create_echidna_process,
    detect_echidna_fail,
)


def get_callable_functions(config, base_config):

    prop_prefix = "echidna_"
    if "prefix" in base_config:
        prop_prefix = base_config["prefix"]

    public_functions = []
    for f in config.files:
        if not os.path.exists(f):
            raise ValueError("Specified file " + f + " does not exist!")
        if not config.no_slither:
            slither = Slither(f)
            for contract in slither.contracts:
                if "multi-abi" not in base_config or not base_config["multi-abi"]:
                    if (
                        config.contract is not None
                    ):  # if you don't tell us which contract, no pruning
                        if contract.name != config.contract:
                            continue
                for function in contract.functions_entry_points:
                    if not function.is_implemented:
                        continue
                    fname = function.full_name
                    if function.is_constructor or (fname.find(prop_prefix) == 0):
                        # Don't bother blacklisting constructors or echidna properties
                        continue
                    if function.visibility in ["public", "external"]:
                        public_functions.append(contract.name + "." + fname)
    return public_functions


def run_campaign(config):
    print("Starting echidna-parade with config={}".format(config))

    if config.resume is None:
        if os.path.exists(config.name):
            raise ValueError(
                config.name
                + ": refusing to overwrite existing directory; perhaps you meant to --resume?"
            )
        else:
            os.mkdir(config.name)

        print()
        print("Results will be written to:", os.path.abspath(config.name))
    else:
        print("Attempting to resume testing from", config.resume)
        if not os.path.exists(config.resume):
            raise ValueError("No parade directory found!")
        if not (os.path.exists(config.resume + "/initial")):
            raise ValueError(
                "No initial run present, does not look like a parade directory!"
            )

    rng = Random(config.seed)

    base_config = create_base_echidna_config(config)
    if not os.path.exists(base_config["corpusDir"]):
        os.mkdir(base_config["corpusDir"])

    print(base_config)

    bases = []
    if config.bases is not None:
        with open(config.bases, "r") as bfile:
            for line in bfile:
                base = line[:-1]
                y = safe_load(base)
                bases.append(y)

    public_functions = get_callable_functions(config, base_config)
    public_functions.extend(config.functions)

    print(
        "Identified",
        len(public_functions),
        "public and external functions:",
        ", ".join(public_functions),
    )
    if len(public_functions) == 0:
        print(
            "WARNING: something may be wrong; no public or external functions were found!"
        )
        print()

    print(public_functions)
    failures = []
    failed_props = {}
    start = time.time()
    elapsed = time.time() - start

    if config.resume is None:
        print()
        print("RUNNING INITIAL CORPUS GENERATION")
        prefix = config.name + "/initial"
        (pname, p, outf) = create_echidna_process(
            prefix, rng, public_functions, base_config, bases, config, initial=True
        )
        p.wait()
        outf.close()
        if p.returncode != 0:
            print(pname, "FAILED")
            detect_echidna_fail(failed_props, pname)
            failures.append(pname + "/echidna.out")

    generation = 1
    if config.resume is None:
        run_name = config.name
    else:
        run_name = config.resume
        generation = 1
        while os.path.exists(run_name + "/gen." + str(generation) + ".0"):
            generation += 1
        print("RESUMING PARADE AT GENERATION", generation)

    elapsed = time.time() - start
    while (config.timeout == -1) or (elapsed < config.timeout):
        print()
        print(
            "SWARM GENERATION #" + str(generation) + ": ELAPSED TIME",
            round(elapsed, 2),
            "SECONDS",
            ("/ " + str(config.timeout)) if config.timeout != -1 else "",
        )
        ps = []
        for i in range(config.ncores):
            prefix = run_name + "/gen." + str(generation) + "." + str(i)
            ps.append(
                create_echidna_process(
                    prefix, rng, public_functions, base_config, bases, config
                )
            )
        any_not_done = True
        gen_start = time.time()
        while any_not_done:
            any_not_done = False
            done = []
            for (pname, p, outf) in ps:
                if p.poll() is None:
                    any_not_done = True
                else:
                    done.append((pname, p, outf))
                    outf.close()
                    for f in glob(pname + "/corpus/coverage/*.txt"):
                        if not os.path.exists(
                            base_config["corpusDir"]
                            + "/coverage/"
                            + os.path.basename(f)
                        ):
                            print("COLLECTING NEW COVERAGE:", f)
                            copy(f, base_config["corpusDir"] + "/coverage")
                    if p.returncode != 0:
                        print(pname, "FAILED")
                        detect_echidna_fail(failed_props, pname)
                        failures.append(pname + "/echidna.out")
            for d in done:
                ps.remove(d)
            gen_elapsed = time.time() - gen_start
            if (config.no_wait) and (
                gen_elapsed > (config.gen_time + 60)
            ):  # full 60 second fudge factor here!
                print("Generation still running after timeout!  Killing echidna...")
                for (pname, p, outf) in ps:
                    outf.close()
                    for f in glob(pname + "/corpus/coverage/*.txt"):
                        if not os.path.exists(
                            base_config["corpusDir"]
                            + "/coverage/"
                            + os.path.basename(f)
                        ):
                            print("COLLECTING NEW COVERAGE:", f)
                            copy(f, base_config["corpusDir"] + "/coverage")
                    if p.poll() is None:
                        p.kill()
                any_not_done = False
        elapsed = time.time() - start
        generation += 1
    print("DONE!")
    print("RUNNING FINAL COVERAGE PASS...")
    try:
        os.remove(glob(base_config["corpusDir"] + "/covered.*.txt")[0])
    except IndexError:
        pass
    start = time.time()
    if config.resume is None:
        prefix = config.name + "/coverage"
    else:
        prefix = config.resume + "/coverage"
    (pname, p, outf) = create_echidna_process(
        prefix,
        rng,
        public_functions,
        base_config,
        bases,
        config,
        initial=True,
        coverage=True,
    )
    p.wait()
    outf.close()
    if p.returncode != 0:
        print(pname, "FAILED")
        detect_echidna_fail(failed_props, pname)
        failures.append(pname + "/echidna.out")
    print("COVERAGE PASS TOOK", round(time.time() - start, 2), "SECONDS")
    print()
    if len(failures) == 0:
        print("NO FAILURES")
        exit(0)
    else:
        print("SOME TESTS FAILED")
        print()
        print("Property results:")
        for prop in sorted(failed_props.keys(), key=lambda x: len(failed_props[x])):
            print("=" * 40)
            print(prop)
            print("FAILED", len(failed_props[prop]), "TIMES")
            print(
                "See:", ", ".join(map(lambda p: p + "/echidna.out", failed_props[prop]))
            )

        exit(len(failures))
