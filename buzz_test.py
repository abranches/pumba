import random
import string
import logging
import sys
import gevent.monkey
from buzz_search import buzz_client
from .task import Task

def random_query(size=3):
    return "".join([random.choice(string.letters) for i in xrange(size)])

class SphinxGevent(Task):

    executor = "gevent"
    max_threads = 5000
    multiple_instances = True

    def setup(self):
        gevent.monkey.patch_all()
        self.p = buzz_client.BuzzClient()

    def run(self):
        r = self.p.query(random_query())
