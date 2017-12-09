from threading import Thread
import sys
from multiprocessing import Condition
from sphinx.pycode.pgen2.token import ASYNC

# python 2.x 
if sys.version_info[0] < 3: 
    def re_raise(*_): # dummy definition - to be replaced in exec
        pass
    exec('''def re_raise(tp, value, tb):
    raise tp, value, tb''')


class EntryLock(object):
    ''' Helper class for locking - actually wraps a Condition object '''    
    def __init__(self):
        self.lock = Condition()
        self.closed = False
    def __enter__(self):
        self.lock.acquire()
    def __exit__(self, *_):
        self.lock.release()
    def wait(self):
        assert(not self.closed) 
        self.lock.wait()
    def notify(self):
        self.lock.notify()
    def close(self):
        ''' final closing operation - lock should not be used any more '''
        with self:
            self.closed = True
            self.lock.notify_all()

class AsyncExec(object):
    '''
    Executes function calls asynchronously starting immediately with the first call.
    If an exception occured the exception is re-raised in the join call. 
    
    :param num_threads: number of threads to use in parallel
    :param add_results: either None or an empty list where the function call results are appended.
    '''
    def __init__(self, num_threads = 8, add_results=None):
        self.pending_calls = []
        self.workers = []
        self.num_threads = num_threads
        self.exception = None
        self.running = True
        self.add_results = add_results
        self.lock = EntryLock()
        
        while len(self.workers) < self.num_threads:
            t = Thread(target=self.__loop)
            self.workers.append(t)
            t.start()
    
    def add(self, fun, *params):
        if not self.running:
            raise BaseException("Wrong state - cannot add actions to already closing / closed AsyncExec")
        with self.lock:
            self.pending_calls.append((fun, list(params)))
            self.lock.notify()

    def join(self):
        self.running = False
        
        with self.lock:
            if (len(self.pending_calls) == 0):
                self.lock.close()
                
        # wait for workers to finish
        for worker in self.workers:
            worker.join()

        if self.exception:
            # re-raise exception
            exc_type, exc_inst, tb = self.exception
            if sys.version_info[0] >= 3:
                raise exc_inst.with_traceback(tb)
            else:
                re_raise(exc_type, exc_inst, tb)
        
    def __loop(self):
        ''' internal function called from thread '''
        while not self.exception and not self.lock.closed:
            fun = None
            with self.lock:
                if len(self.pending_calls) > 0:
                    fun, params = self.pending_calls.pop()
                elif not self.running:
                    self.lock.close()
                else:
                    self.lock.wait()
            
            if fun and not self.exception:
                try:
                    result = fun(*params)
                    if self.add_results != None:
                        with self.lock:
                            self.add_results.append(result)
                except:
                    self.exception = sys.exc_info()
            
    def __call__(self, fun, *params):
        self.add(fun, *params)
        
    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self.join()
            
if __name__ == '__main__':
    import time
    
    def testOuter():
        def testfun(t, loops, msg):
            for _ in range(loops):
                time.sleep(t)
                sys.stdout.write(msg)
            #raise BaseException("TEST " + msg)
        if False:
            with AsyncExec(3) as exc:
                exc(testfun, 0.5, 5, '*')
                exc(testfun, 0.5, 10, '+')
                exc(testfun, 1.5, 4, '-')
                exc(testfun, 1, 10, '=')
                exc(testfun, 0.1, 10, 'x')
            print("")
            
        def fib(i):
            if i <= 1:
                return i
            return fib(i-2) + fib(i-1)
        
        results = []
        exc = AsyncExec(add_results = results)
        exc.add(fib, 10)
        exc.add(fib, 1)
        exc.add(fib, 31)
        exc.add(fib, 22)
        exc.join()
        print(results)
    
    testOuter()
