import logging
import time
import sys
from collections import OrderedDict

from ..stats import Stats
from ..sorted_collection import SortedCollection

log = logging.getLogger(__name__)

def run_task_func_wrapper(f, run_id):
    result = RunResult(run_id)
    try:
        start_time = time.time()
        f()
        run_time = time.time() - start_time
        result.run_time = run_time
    except Exception:
        #log.debug("Run crashed", exc_info=True)
        result.exc = sys.exc_info()[:2]

    return result


class Run(object):
    def __init__(self, run_id, start_time):
        self.id = run_id
        self.finished = False
        self.result = None
        self.start_time = start_time

    @property
    def finish_time(self):
        return self.start_time + self.result.run_time if self.finished else None

    @property
    def run_time(self):
        return self.result.run_time if self.finished else None

    def __str__(self):
        return "Run(id=%d, %s)" % (self.id, self.start_time)


class RunResult(object):
    def __init__(self, run_id):
        self.run_id = run_id
        self.exc = None
        self.run_time = None


class AbstractExecutor(object):
    def __init__(self, task_cls):
        self.task_cls = task_cls
        self._start_time = None
        self._end_time = None
        self._all_runs = SortedCollection(key=lambda x: x.start_time)
        self._running_runs = OrderedDict()
        self._finished_runs = OrderedDict()
        self._n_runs = 0
        self.stats = Stats(self)

    @property
    def running_time(self):
        return time.time() - self._start_time

    def start(self):
        log.debug("Starting")
        self.setup_tasks()
        self._start_time = time.time()

    def finish(self):
        """Extend me if needed"""
        log.debug("Finishing")
        self._end_time = time.time()

    def join(self):
        "Extend me"
        log.debug("Waiting")
        pass

    def setup_tasks(self):
        raise NotImplementedError()

    def available(self):
        raise NotImplementedError()

    def wait_available(self):
        raise NotImplementedError()

    def _run_task(self, run_id):
        raise NotImplementedError()

    def async_run_task(self):
        run_id = self._n_runs
        self._n_runs += 1
        run = Run(run_id, self.running_time)
        self._running_runs[run_id] = run
        self._all_runs.append(run)
        self._run_task(run_id)
        return run

    def on_async_run_finished(self, result):
        run = self._running_runs.get(result.run_id)
        run.result = result
        run.finished = True
        del self._running_runs[result.run_id]
        self._finished_runs[result.run_id] = run

    def runs_from_range(self, start=None, end=None):
        if start is None:
            start = 0
        if end is None:
            end = sys.maxint
        return self._all_runs.slice_items(start, end)

    def nr_running_runs(self):
        return len(self._running_runs)

    def nr_finished_runs(self):
        return len(self._finished_runs)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.finish()
        self.join()