'''
Created on 07.12.2017

@author: Michael
'''
from multiprocessing import Queue
from threading import Thread
import time
import sys
from Queue import Empty

class AsyncExec(object):
    '''
    Executes function calls asynchronously starting immediately with the first call.
    If an exception occured the exception is re-raised in the join call. 
    '''
    def __init__(self, num_threads = 8):
        self.pending_calls = Queue()
        self.workers = []
        self.num_threads = num_threads
        self.exception = None
        self.running = True

        while len(self.workers) < self.num_threads:
            t = Thread(target=self.loop)
            self.workers.append(t)
            t.start()
    
    def add(self, fun, *params):
        if not self.running:
            raise BaseException("Wrong state - cannot add actions to already closing / closed AsyncExec")
        self.pending_calls.put((fun, list(params)))

    def join(self):
        self.running = False
        # wait for workers to finish
        for worker in self.workers:
            worker.join()
            
        self.pending_calls.close()

        if self.exception:
            # re-raise exception
            exc_type, exc_inst, tb = self.exception
            if sys.api_version > (3,0):
                raise exc_type.with_traceback(tb)
            else:
                raise exc_type, exc_inst, tb
        
    def loop(self):
        while not self.exception:
            try:
                fun, params = self.pending_calls.get(block=self.running)
            except Empty:
                break
            try:
                if not self.exception:  
                    fun(*params)
            except:
                self.exception = sys.exc_info()
            
    def __call__(self, fun, *params):
        self.add(fun, *params)
        
    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self.join()
            
            
if __name__ == '__main__':
    
    def testfun(t, loops, msg):
        for _ in range(loops):
            time.sleep(t)
            sys.stdout.write(msg)
        raise BaseException("TEST " + msg)
    with AsyncExec(3) as exc:
        exc(testfun, 0.5, 5, '*')
        exc(testfun, 0.5, 10, '+')
        exc(testfun, 1.5, 4, '-')
        exc(testfun, 1, 10, '=')
    