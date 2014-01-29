import sys
import time
import random
import gevent
from .task import Task

import logging

#class MyTestThreading(Task):
class MyTestThreading(object):

    executor = "multithreading"
    max_threads = 1000
    multiple_instances = False

    def setup(self):
        pass

    def run(self):
        #logging.debug("ola")
        time.sleep(0.1)


class MyTestGevent(Task):
#class MyTestGevent(object):

    executor = "gevent"
    max_threads = 1000
    multiple_instances = False

    def setup(self):
        gevent.monkey.patch_all()

    def run(self):
        time.sleep(0.1)
        #logging.error("teste")
        #r = random.random()
        #logging.error("in")
        #self.n += 1
        #logging.error(self.n)
        pass
