import sys
import Queue
import concurrent.futures
import logging
import threading
from contextlib import contextmanager

from .base import AbstractExecutor, run_task_func_wrapper

log = logging.getLogger(__name__)

class ObjectPool(object):

    def __init__(self, obj_cls, max_size, init_size=0, init_args=(), init_kwargs={}):
        self.obj_cls = obj_cls
        self.max_size = max_size
        self._init_args = init_args
        self._init_kwargs = init_kwargs
        self._size = init_size
        self._queue = Queue.Queue()
        for _ in xrange(init_size):
            self._create_object()

    def get(self, block=False, timeout=sys.maxint):
        if self._queue.empty() and self._size < self.max_size:
            self._create_object()
        return self._queue.get(block, timeout)

    def _create_object(self):
        obj = self.obj_cls(*self._init_args, **self._init_kwargs)
        self._queue.put(obj)
        self._size += 1

    @contextmanager
    def get_context(self, timeout=sys.maxint):
        obj = self.get(True, timeout)
        try:
            yield obj
        finally:
            self.give_back(obj)

    def give_back(self, obj):
        self._queue.put(obj)

    def __iter__(self):
        return iter(self._queue.queue)


class MultithreadingExecutor(AbstractExecutor):
    def __init__(self, task_cls, max_threads, multiple_instances=False):
        super(MultithreadingExecutor, self).__init__(task_cls)
        self._max_threads = max_threads
        self._multiple_instances = multiple_instances
        if multiple_instances:
            self._tasks_pool = ObjectPool(task_cls, max_threads, init_size=max_threads)
        else:
            self._task = task_cls()
        #self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_threads)
        #self._futures = []
        self._threads = []
        self._threads_counter = Counter(0, condition=True,
                                        condition_trigger=max_threads-1)

    def setup_tasks(self):
        if self._multiple_instances:
            for task in self._tasks_pool:
                task.setup()
        else:
            self._task.setup()

    def join(self, timeout=sys.maxint):
        super(MultithreadingExecutor, self).join()
        #concurrent.futures.wait(self._futures,
        #                        timeout=sys.maxint,
        #                        return_when=concurrent.futures.ALL_COMPLETED)
        for t in self._threads:
            t.join()

    def available(self):
        return self._threads_counter < self._max_threads

    def wait_available(self):
        with self._threads_counter:
            while self._threads_counter == self._max_threads:
                self._threads_counter._condition.wait()

    def _run_task(self, run_id):
        #f = self._thread_pool.submit(self._run_on_thread_pool, run_id)
        #self._futures.append(f)
        self._threads_counter.inc()
        t = threading.Thread(target=self._run_on_thread_pool, args=(run_id,))
        self._threads.append(t)
        t.start()

    def _run_on_thread_pool(self, run_id):
        def go(run_id):
            if self._multiple_instances:
                with self._tasks_pool.get_context() as task:
                    result = run_task_func_wrapper(task.run, run_id)
            else:
                result = run_task_func_wrapper(self._task.run, run_id)
            self.on_async_run_finished(result)

        try:
            go(run_id)
        except:
            log.debug("DEUUU MEEERDA", exc_info=True)
        finally:
            self._threads.remove(threading.current_thread())
            self._threads_counter.dec()





class Counter(object):
    """
    An atomic/thread-safe counter.

    It tries to look like a simple int when printing and allows
    comparisons with ints as well.

    It uses an internal lock if some lock is not supplied at __init__.
    A condition can also be passed in the arguments. In that case the condition
    is notified whenever the counter reaches `condition_trigger`.

    >>> from utilslib.multithreading import Counter
    >>> i = Counter()
    >>> i.inc()
    >>> i == 0
    False
    >>> i > 0
    True
    >>> print i
    1
    >>> print repr(i)
    Counter(1)
    >>> i.dec()
    >>> i == 0
    True
    >>> with i.inc_while():
    ...   print i
    ...
    1
    >>> print i
    0

    """
    def __init__(self, n=0, lock=None, condition=None, condition_trigger=0):
        """
        Arguments:
          n           starting number of the counter
          lock        lock to use internally. if None a new Lock is created
          condition   condition to notify whenever counter == `condition_trigger`
                      if condition == True, a condition object will be created
          condition_trigger   Counter value that triggers condition.notify
        """
        self._n = n
        if lock is None:
            lock = threading.RLock()
        self._lock = lock
        if condition == True:
            condition = threading.Condition(lock=self._lock)
        self._condition = condition
        self._condition_trigger = condition_trigger

    @property
    def n(self):
        return self._n

    def inc(self, i=1):
        """
        Increment counter.
        """
        with self._lock:
            self._n += i
            if self._condition is not None and self._n == self._condition_trigger:
                self._condition.notify()
            ret_n = self._n
        return ret_n

    def dec(self, i=1):
        """
        Decrement counter.
        """
        with self._lock:
            self._n -= i
            if self._condition is not None and self._n == self._condition_trigger:
                self._condition.notify()
            ret_n = self._n
        return ret_n

    @contextmanager
    def inc_while(self, i=1):
        """
        Context that increments and decrements the counter on exit.
        It always decrements the counter back even in case of Exceptions raised.
        """
        self.inc(i)
        try:
            yield
        finally:
            self.dec(i)

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def __eq__(self, o):
        if isinstance(o, Counter):
            return self._n == o._n
        return self._n == o

    def __lt__(self, o):
        if isinstance(o, Counter):
            return self._n < o._n
        return self._n < o

    def __gt__(self, o):
        if isinstance(o, Counter):
            return self._n > o._n
        return self._n > o

    def __ge__(self, o):
        if isinstance(o, Counter):
           return self._n >= o._n
        return self._n >= o

    def __str__(self):
        return str(self._n)

    def __repr__(self):
        return "Counter(%d)" % self._n

