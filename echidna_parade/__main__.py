import argparse
import os.path
import multiprocessing
import sys

from echidna_parade.config import create_parade_config
from echidna_parade.campaign import run_campaign


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        type=os.path.abspath,
        nargs="+",
        default=None,
        help="FILES argument for echidna-test",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="name for parade (directory where output files are placed)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="parade to resume (directory name with existing run)",
    )
    parser.add_argument(
        "--contract", type=str, default=None, help="CONTRACT argument for echidna-test"
    )
    parser.add_argument(
        "--config",
        type=argparse.FileType("r"),
        default=None,
        help="CONFIG argument for echidna-test",
    )
    parser.add_argument(
        "--bases",
        type=argparse.FileType("r"),
        default=None,
        help="file containing a list of additional configuration files to randomly choose among for non-initial runs",
    )
    parser.add_argument(
        "--ncores",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of cores to use (swarm instances to run in parallel (default = all available)",
    )
    parser.add_argument(
        "--corpus_dir",
        type=os.path.abspath,
        default=None,
        help="Directory to store the echidna-parade corpus (useful when existing corpus available)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Total testing time, use -1 for no timeout (default = 3600)",
    )
    parser.add_argument(
        "--gen_time",
        type=int,
        default=300,
        help="Per-generation testing time (default = 300)",
    )
    parser.add_argument(
        "--initial_time",
        type=int,
        default=300,
        help="Initial run testing time (default = 300)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed (default = None)."
    )
    parser.add_argument(
        "--minseqLen",
        type=int,
        default=10,
        help="Minimum sequence length to use (default = 10).",
    )
    parser.add_argument(
        "--maxseqLen",
        type=int,
        default=300,
        help="Maximum sequence length to use (default = 300).",
    )
    parser.add_argument(
        "--PdefaultLen",
        type=float,
        default=0.5,
        help="Probability of using default/base length (default = 0.5)",
    )
    parser.add_argument(
        "--PdefaultDict",
        type=float,
        default=0.5,
        help="Probability of using default/base dictionary usage frequency (default = 0.5)",
    )
    parser.add_argument(
        "--prob",
        type=float,
        default=0.5,
        help="Probability of including functions in swarm config (default = 0.5).",
    )
    parser.add_argument(
        "--always",
        type=str,
        nargs="+",
        default=[],
        help="functions to ALWAYS include in swarm configurations",
    )
    parser.add_argument(
        "--no-slither",
        action="store_true",
        help="Do not run Slither (mostly for Vyper contracts, which Slither cannot handle).",
    )
    parser.add_argument(
        "--functions",
        type=str,
        nargs="+",
        default=[],
        help="Alternative way to specify ABI for functions, when Slither cannot be used.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Kill echidna subprocesses if they do not finish on time. Useful for a fair benchmarking.",
    )
    parsed_args = parser.parse_args(sys.argv[1:])
    return (parsed_args, parser)


def main():
    parsed_args, parser = parse_args()
    config = create_parade_config(parsed_args, parser)
    run_campaign(config)


if __name__ == "__main__":
    main()
