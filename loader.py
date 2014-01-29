import inspect
import logging
from copy import copy

from .task import Task

log = logging.getLogger(__name__)

def is_test_class(cls):
    return inspect.isclass(cls) and cls != Task and Task in inspect.getmro(cls)

def create_test_from_func(func):
    t = copy.copy(Task)
    t.run = func
    return t

def hakuna_matata_load(obj):
    tests = []
    if type(obj) in (list, tuple):
        for item in obj:
            # I take no responsabilities for stack overflows!!
            tests.extend(hakuna_matata_load(item))
    elif is_test_class(obj):
        tests.append(obj)
    elif inspect.ismodule(obj):
        tests.extend([t[1] for t in inspect.getmembers(obj, is_test_class)])
    elif inspect.ismethod(obj) or inspect.isfunction(obj):
        tests.append(create_test_from_func(obj))
    else:
        log.error("Don't know what the hell is %s!!" % obj)

    return tests