import random
import string
import logging
import sys
import gevent.monkey
from buzz_search import buzz_sphinx
buzz_sphinx.TIMEOUT = 2.0
#from buzz_search.buzz_sphinx import BuzzSphinxClientPool, BuzzSphinxClient
from .task import Task

def random_query(size=3):
    return "".join([random.choice(string.letters) for i in xrange(size)])

#class SphinxThreading(Task):
class SphinxThreading(object):

    executor = "multithreading"
    max_threads = 1000
    multiple_instances = True

    def setup(self):
        self.p = buzz_sphinx.BuzzSphinxClient("localhost", 9312)

    def run(self):
        r = self.p.query(random_query())


class SphinxGevent(Task):
#class SphinxGevent(object):

    executor = "gevent"
    max_threads = 5000
    multiple_instances = True

    def setup(self):
        gevent.monkey.patch_all()
        self.p = buzz_sphinx.BuzzSphinxClient("localhost", 9312)

    def run(self):
        r = self.p.query(random_query())
