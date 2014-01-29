class Task(object):

    executor = "multithreading"
    max_threads = 5
    multiple_instances = False

    def setup(self):
        pass

    def run(self):
        raise NotImplemented()