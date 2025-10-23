from config import Config
from mem_hierarchy import MemoryHierarchySimulator
import argparse
import os
import sys

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Memory Hierarchy Simulator runner"
    )
    parser.add_argument(
        "-c", "--config",
        default="trace.config",
        help="Path to config file (default: %(default)s)",
    )
    parser.add_argument(
        "-t", "--trace",
        default="-",  # default to stdin, not a hardcoded file
        help='Trace file path (use "-" or omit to read from stdin; default: "%(default)s")',
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Enable verbose output (default)",
    )
    group.add_argument(
        "-q", "--quiet",
        dest="verbose",
        action="store_false",
        help="Quiet mode (turn off verbose output)",
    )
    parser.set_defaults(verbose=True)
    return parser.parse_args()

def main():
    args = parse_args()

    use_stdin = (args.trace == "-")

    # validation
    if not os.path.exists(args.config):
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(2)

    if not use_stdin and not os.path.exists(args.trace):
        print(f"error: trace file not found: {args.trace}", file=sys.stderr)
        sys.exit(2)

    mem_sim_config = Config.from_config_file(args.config)
    if args.verbose:
        print(mem_sim_config)
    trace_path = "/dev/stdin" if use_stdin else args.trace
    simulator = MemoryHierarchySimulator(mem_sim_config)
    simulator.simulate(trace_path, verbose=args.verbose)


if __name__ == '__main__':
    main()