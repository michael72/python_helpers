'''
Created on 16.02.2020

@author: Michael Schulte
'''

from _collections import deque
from multiprocessing import Condition
import sys
from threading import Thread
import traceback
import types


class AsyncIterator():
    ''' Call the function on each element of the iterator asynchronously
    Either call:
    
    ai = AsyncIterator(myFun, items)
    ai.execute()
    
    # and work on ai.results or...
    
    with AsyncIterator(myFun, items) as ai:
      for item in ai:
        # work on the result item
    '''

    def __init__(self, fun, iterator, numThreads=3):
        ''' Create the AsyncIterator.
        :fun function taking one argument:
        :iterator iterating over a bunch of items:
        :numThreads number of parallel threads to work on:
        '''
        self.fun = fun
        self.iter = iterator
        self.numThreads = numThreads
        self.lock = Condition()
        self.lockRes = Condition()
        self.items = deque() 
        self.threads = []
        self.params = []
        self.results = []
        self.idx = -1
        self.feeding = self.numThreads > 1 and sys.version_info[0] < 3
        self.joined = False
        self.working = numThreads
        self.ex = None
        
    def start(self):
        ''' Starts the processing.
        '''
        if self.numThreads > 1:
            if self.feeding:
                self.threads.append(Thread(target=self._feed))
            else:
                # asynchronous feeding does not work with Python 3.x
                self._feed()
            for _ in range(self.numThreads):
                self.threads.append(Thread(target=self._run, args=(len(self.threads),)))
            for thread in self.threads:
                thread.daemon = True
                thread.start()
                
    def _feed(self):
        try:
            for item in self.iter:
                with self.lock:
                    self.items.append(item)
                    self.lock.notify()
        except BaseException as ex:
            traceback.print_exc()
            self.ex = ex
        finally:
            self.feeding = False
            with self.lock:
                self.lock.notify_all()

    def _run(self, threadId):
        ''' Executed in thred context.
        Run the function on each element and store the results.
        '''
        try:
            self.threadId = threadId
            while self.feeding or (len(self.items) > 0):
                item = None
                res = None
                with self.lock:
                    if (len(self.items) == 0):
                        self.lock.wait()
                    if len(self.items) > 0:
                        item = self.items.popleft()
                if item != None:
                    res = self.fun(item)
                if res != None:
                    if isinstance(res, types.GeneratorType):
                        res = list(res)  # generators within AsyncIterators have to be explicitly polled
                    with self.lock:
                        self.params.append(item)
                        with self.lockRes:
                            self.results.append(res)
                with self.lockRes:
                    self.lockRes.notify()

        except BaseException as ex:
            traceback.print_exc()
            self.ex = ex
        
        finally:
            with self.lockRes:
                if self.working > 0:
                    self.working -= 1
                if self.working == 0:
                    with self.lock:
                        self.lock.notify_all()
                    with self.lockRes:
                        self.lockRes.notify_all()

    def __enter__(self):
        if self.numThreads > 1: 
            self.start()
        return self
        
    def __iter__(self):
        self.idx = -1
        if self.numThreads > 1: 
            return self
        else:
            return map(self.fun, self.iter)

    def _next(self):
        self.idx += 1
        while self.idx >= len(self.results) and self.working > 0:
            with self.lockRes:
                if self.working > 0:
                    self.lockRes.wait()
        if self.idx < len(self.results):                
            return self.results[self.idx]
        raise StopIteration
        
    def next(self):
        return self._next()
    
    def __next__(self):
        return self._next()
        
    def join(self):
        ''' Waits until processing is finished and joins all threads. '''
        with self.lock:
            self.lock.notify_all()

        for t in self.threads:
            t.join() 

        self.joined = True
        if self.ex:
            raise(self.ex)
    
    def execute(self):
        self.start()
        return self.join()

    def __exit__(self, tpe, value, tb):
        if tb: 
            traceback.print_exception(tpe, value, tb, None, sys.stderr)
        self.join()
            
