from __future__ import absolute_import

import argparse
import logging
import importlib

from .loader import hakuna_matata_load
from .benchmark import Benchmark

log = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module",
                        help="module name where the tasks are located")
    parser.add_argument("-d", "--duration", type=float, default=10.0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.CRITICAL)
    level = logging.DEBUG if args.verbose else logging.WARNING
    level = logging.DEBUG
    logging.getLogger(__name__).setLevel(level)
    logging.getLogger("pumba").setLevel(level)

    module = importlib.import_module(args.module)
    tasks = hakuna_matata_load(module)
    benchmark = Benchmark(tasks[0],
                          duration=args.duration,
                          terminal=not args.verbose)
    benchmark.start()
    #benchmark.export("/Users/pedro/pumba/myresults10", sample_frequency=10)
    #benchmark.export("/Users/pedro/pumba/myresults50", sample_frequency=50)
    #benchmark.export("/Users/pedro/pumba/myresults100", sample_frequency=100)
    benchmark.export("/Users/pedro/pumba/myresults")
    benchmark.export("/Users/pedro/pumba/myresults1", sample_frequency=1)

if __name__ == "__main__":
    main()
