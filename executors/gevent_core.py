import sys
import logging
import gevent
from gevent.queue import Queue
from gevent.pool import Pool

from .base import AbstractExecutor, run_task_func_wrapper

log = logging.getLogger(__name__)


class GeventExecutor(AbstractExecutor):
    def __init__(self, task_cls, max_threads, multiple_instances=False):
        super(GeventExecutor, self).__init__(task_cls)
        self._max_threads = max_threads
        self._multiple_instances = multiple_instances
        if multiple_instances:
            self._tasks_pool = Queue()
            for _ in xrange(max_threads):
                self._tasks_pool.put(task_cls())
        else:
            self._task = task_cls()
        self._thread_pool = Pool(size=max_threads)

    def setup_tasks(self):
        if self._multiple_instances:
            for task in self._tasks_pool.queue:
                task.setup()
        else:
            self._task.setup()

    def join(self, timeout=sys.maxint):
        super(GeventExecutor, self).join()
        self._thread_pool.join()

    def available(self):
        is_it = not self._thread_pool.full()
        #if not is_it:
        #    gevent.sleep(0)
        gevent.sleep(0)
        return is_it

    def wait_available(self):
        gevent.sleep(0)
        self._thread_pool.wait_available()

    def _run_task(self, run_id):
        self._thread_pool.apply_async(self._run_on_thread_pool, (run_id,))
        #gevent.sleep(0)

    def _run_on_thread_pool(self, run_id):
        try:
            if self._multiple_instances:
                try:
                    task = self._tasks_pool.get()
                    result = run_task_func_wrapper(task.run, run_id)
                finally:
                    self._tasks_pool.put(task)
            else:
                result = run_task_func_wrapper(self._task.run, run_id)
            self.on_async_run_finished(result)
        except:
            log.debug("DEUUU MEEERDA", exc_info=True)
