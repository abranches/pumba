from __future__ import division
import time
import itertools
import logging
import sys
import numpy
import math
from collections import namedtuple

log = logging.getLogger(__name__)

GeneralStats = namedtuple("GeneralStats", ("submited_runs",
                                           "finished_runs",
                                           "failed_runs",
                                           "failed_ratio",
                                           "avg_run_time",
                                           "std_dev_run_time",
                                           "min_run_time",
                                           "max_run_time",))

def _ratio(a, b, default=0.0):
    return a/b if b != 0 else default

class Stats(object):
    def __init__(self, executor):
        self.executor = executor

    def general_stats(self, start_time=None, end_time=None):
        runs = self.executor.runs_from_range(start_time, end_time)
        return self._calc_stats(runs)

    def _calc_stats(self, runs):
        # standart deviation formula when mean is not known:
        # std_dev = sqrt((sum(xi**2) - (sum(xi)**2)/n) / (n-1))
        sum_run_time = 0
        sum_power_run_time = 0
        count_runs = 0
        count_failed = 0
        count_finished = 0
        min_time = sys.maxint
        max_time = 0.0
        for r in runs:
            count_runs += 1
            if r.finished:
                count_finished += 1
                if r.result.exc is not None:
                    count_failed += 1
                else:
                    sum_run_time += r.result.run_time
                    sum_power_run_time += r.result.run_time**2
                    min_time = min(min_time, r.result.run_time)
                    max_time = max(max_time, r.result.run_time)

        if min_time == sys.maxint:
            min_time = 0.0

        if count_finished <= 1:
            std_dev = 0.0
        else:
            std_dev = math.sqrt((sum_power_run_time - (sum_run_time**2)/count_finished) / (count_finished-1))

        return GeneralStats(submited_runs=count_runs,
                            finished_runs=count_finished,
                            failed_runs=count_failed,
                            failed_ratio=_ratio(count_failed, count_finished),
                            avg_run_time=_ratio(sum_run_time, count_finished),
                            std_dev_run_time=std_dev,
                            min_run_time=min_time,
                            max_run_time=max_time,
                            )


    def intervals_stats(self, step, start_time, end_time):
        stats = []
        for i in numpy.arange(start_time, end_time, step):
            runs = self.executor._all_runs.slice_items(i,
                                                       i+step)
            stats.append((i, self._calc_stats(runs)))
        return stats


