import time
import prettytable
import logging
import threading
import os
import csv
import json
import shutil
import numpy
import itertools
import math

from executors.multithreading_core import MultithreadingExecutor
from executors.gevent_core import GeventExecutor

log = logging.getLogger(__name__)

PUMBA = """ _____                 _
|  __ \               | |
| |__) |   _ _ __ ___ | |__   __ _
|  ___/ | | | '_ ` _ \| '_ \ / _` |
| |   | |_| | | | | | | |_) | (_| |
|_|    \__,_|_| |_| |_|_.__/ \__,_|"""


class PumbaException(Exception):
    pass

def _create_executor(task):
        if task.executor == "multithreading":
            executor = MultithreadingExecutor(task,
                                              task.max_threads,
                                              task.multiple_instances)
        elif task.executor == "multiprocessing":
            pass
        elif task.executor == "gevent":
            executor = GeventExecutor(task,
                                      task.max_threads,
                                      task.multiple_instances)
        else:
            raise PumbaException("Invalid executor type `%s`" % task.executor)
        return executor


class _SingleBenchmark(object):

    def __init__(self, task, duration, terminal=True):
        self.task = task
        self.duration = duration
        self.interval = 1.0
        self.terminal = terminal

        self._running = False
        self._stop_flag = False
        self._start_time = None
        self._executor = None
        self._timer = None

    def start(self):
        log.debug("Starting benchmark of %s" % self.task)
        self._running = True
        self._start_time = time.time()
        self._executor = _create_executor(self.task)
        self._executor.start()

        self._timer = threading.Timer(self.interval, self._report_data)
        self._timer.daemon = False
        self._timer.start()
        self._run()

        self._executor.finish()
        self._running = False

    def _run(self):
        START_RPS = 0
        END_RPS = 1000
        rps = START_RPS

        now = time.time()
        last_run = now

        while now - self._start_time < self.duration and not self._stop_flag:
            now = time.time()
            runs_left = (now - last_run) * rps*1.05
            while runs_left > 1.0:
                self._executor.wait_available()
                self._executor.async_run_task()
                now = time.time()
                last_run = now
                runs_left -= 1.0
                time.sleep(0.0)
            p_dif = (now - self._start_time) / self.duration
            rps = (END_RPS-START_RPS) * p_dif + START_RPS
            #rps = abs(math.sin(math.radians(rps))) * END_RPS
            time.sleep(0.0)

        self._executor.join()
        log.debug("%r" % (self._executor.stats.general_stats(),))

    def _report_data(self):
        if self.terminal:
            print "\033[H\033[J"
            print self._terminal_output()
        else:
            log.debug(self._executor.stats.general_stats())
        if self._running:
            self._timer = threading.Timer(self.interval, self._report_data)
            self._timer.start()

    def _terminal_output(self):
        now = time.time()
        cols = ("interval", "Count", "Failed", "Min", "Max", "Std Dev", "Avg")
        t = prettytable.PrettyTable(cols, padding_width=5, border=False)
        t.align = "r"
        t.float_format = "0.3"
        l = []
        l.append(PUMBA)
        l.append("------------------------------------\n")
        l.append("Stress test of %s\n\n" % self._executor.task_cls)

        i = 0.0
        while i < min(now-self._start_time, self.duration):
            stats = self._executor.stats.general_stats(i, i+self.interval)
            values = (i, stats.finished_runs,
                      "%d (%d%%)" % (stats.failed_runs, int(stats.failed_ratio*100)),
                      stats.min_run_time,
                      stats.max_run_time,stats.std_dev_run_time, stats.avg_run_time,)
            t.add_row(values)
            i += self.interval

        stats = self._executor.stats.general_stats()
        values = ("Total", stats.finished_runs,
          "%d (%d%%)" % (stats.failed_runs, int(stats.failed_ratio*100)),
          stats.min_run_time,
          stats.max_run_time, stats.std_dev_run_time, stats.avg_run_time, )
        t.add_row(("-",)*len(cols))
        t.add_row(values)
        l.append(t.get_string())
        return "\n".join(l)



class Benchmark(object):
    EXPORT_FORMATS = ("html",)

    def __init__(self, tasks, duration, terminal=True):
        if type(tasks) not in (list, tuple):
            tasks = [tasks]
        self.tasks = tasks
        self.duration = duration
        self.terminal = terminal
        self._benchmarks = [_SingleBenchmark(t, duration, terminal) for t in self.tasks]

    def start(self):
        for b in self._benchmarks:
            b.start()

    def results(self, sample_interval=1.0):
        d = {}
        for b in self._benchmarks:
            run_time = []
            std_dev = []
            maxs = []
            failed = [(0.0, 0)]
            runs = [(0.0, 0)]
            for i, stat in b._executor.stats.intervals_stats(sample_interval,
                                                             0.0,
                                                             self.duration):
                i = round(i, 2)
                avg_time = round(stat.avg_run_time, 4)*1000
                run_time.append((i, avg_time))
                std_dev.append((i, round(stat.std_dev_run_time,4)*1000))
                m = 0
                iii = 0
                for run in b._executor.runs_from_range(i, i+sample_interval):
                    if run.result.exc is not None:
                        # this run resulted in failure
                        continue
                    #if run.run_time > m and stat.std_dev_run_time / run.run_time > 0.5:
                    if run.run_time > m:
                        m = run.run_time
                        iii = run.start_time
                    #if stat.std_dev_run_time / stat.avg_run_time > 0.9:
                    #    run_time.append((round(run.start_time,2), round(run.run_time,4)*1000))
                if m != 0:
                    maxs.append((round(iii,2), round(m,4)*1000))

            for i, stat in b._executor.stats.intervals_stats(1.0,
                                                             0.0,
                                                             self.duration):
                i = round(i+1.0, 2)
                failed.append((i, stat.failed_runs))
                runs.append((i, stat.submited_runs))

            d[b.task.__name__] = {"avg_run_time": run_time,
                                  "max_run_time": maxs,
                                  "std_dev": std_dev,
                                  "failed": failed,
                                  "runs": runs}
        return d

    def export(self, dir_path=None, formats=None, sample_frequency=None):
        if formats is None:
            formats = self.EXPORT_FORMATS
        if type(formats) not in (list, tuple):
            formats = (formats,)

        if sample_frequency is None:
            sample_interval = self.duration / 50.0
        else:
            sample_interval = 1.0 / sample_frequency

        #time.strftime("%Y%m%d%H%M%S")
        if dir_path is None:
            dir_path = "./benchmark"

        if os.path.exists(dir_path):
            for i in itertools.count(1):
                if not os.path.exists(dir_path+".%d" % i):
                    break
            dir_path += ".%d" % i

        os.mkdir(dir_path)

        for f in formats:
            getattr(self, "_export_%s" % f)(dir_path, sample_interval)

    def _export_html(self, dir_path, sample_interval):
        files = ["exporting.js",
                 "highcharts.js",
                 "jquery.min.js",
                 "bootstrap",
                 "template.html",
                 "template.css"]
        for f in files:
            path = os.path.join(os.path.dirname(__file__), "html", f)
            dst = os.path.join(dir_path, f)
            if os.path.isdir(path):
                shutil.copytree(path, dst)
            else:
                shutil.copy(path, dst)

        results_js_path = os.path.join(dir_path, "results.js")
        with open(results_js_path, "w") as f:
            f.write("var data = %s;" % json.dumps(self.results(sample_interval)))
