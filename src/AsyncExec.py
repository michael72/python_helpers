import sys
from threading import Thread
from multiprocessing import Condition

# python 2.x 
if sys.version_info[0] < 3: 
    def re_raise(*_): # dummy definition - to be replaced in exec
        pass
    exec('''def re_raise(tp, value, tb):
    raise tp, value, tb''')



class AsyncExec(object):
    '''
    Executes function calls asynchronously starting immediately with the first call.
    If an exception occured the exception is re-raised in the join call. 
    
    :param num_threads: number of threads to use in parallel
    :param add_results: either None or an empty list where the function call results are appended.
    '''
    def __init__(self, num_threads = 8, add_results=False):
        self.pending_calls = []
        self.workers = []
        self.num_threads = num_threads
        self.exception = None
        self.running = True
        self.add_results = add_results
        self.results = [] if add_results else None
        self.lock = create_close_condition()
        
        while len(self.workers) < self.num_threads:
            t = Thread(target=self.__loop)
            t.daemon = True
            self.workers.append(t)
            t.start()
    
    def fun(self, fun_call):
        return AsyncFun(fun_call, self)
    
    def add(self, fun, *params):
        if not self.running:
            raise BaseException("Wrong state - cannot add actions to already closing / closed AsyncExec")
        with self.lock:
            self.pending_calls.append((fun, params))
            self.lock.notify()
        return self

    def join(self):
        ''' Wait for the running threads to finish and join to main thread. 
        :return: results of function calls - if add_results was set in init
        :raises: re-raises any exception that was caught during the function call '''
        assert(self.running) # join should be called once only
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
        return self.results
    
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
                    if self.add_results:
                        with self.lock:
                            self.results.append(result)
                except:
                    if not self.exception:
                        self.exception = sys.exc_info()
                    with self.lock:
                        self.pending_calls = []
                        self.lock.close()
            
    def __call__(self, fun, *params):
        self.add(fun, *params)
        
    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self.join()
            

def create_close_condition():
    ''' adds a close function and a closed property to the Condition function '''
    lock = Condition()
    lock.closed = False
    def close():
        with lock:
            lock.closed = True
            lock.notify_all()
    lock.close = close
    return lock


class AsyncFun(object):
    ''' Helper class to set one specific function in AsyncExec. '''
    def __init__(self, fun, async_exec):
        self.fun = fun
        self.async_exec = async_exec
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.async_exec.__exit__(*args)
    def __call__(self, *args):
        return self.add(*args)
    def add(self, *args):
        self.async_exec.add(self.fun, *args)
        return self
    def join(self):
        return self.async_exec.join()
        

if __name__ == '__main__':
    import time
    
    def testOuter():
        def fib(i):
            if i <= 1:
                return i
            return fib(i-2) + fib(i-1)
        
        exc = AsyncExec(add_results = True)      
        exc.add(fib, 10)
        exc.add(fib, 1)
        exc.add(fib, 33)
        exc.add(fib, 22)
        exc.join()
        print(exc.results)

        def testfun(t, loops, msg):
            for _ in range(loops):
                time.sleep(t)
                sys.stdout.write(msg)
                sys.stdout.flush()
            #raise BaseException("TEST " + msg)
        if True:
            with AsyncExec(3).fun(testfun) as test_print:
                test_print(0.5, 5, '*')
                test_print(0.5, 10, '+')
                test_print(1.5, 4, '-')
                test_print(1, 10, '=')
                test_print(0.1, 10, 'x')
            print("")
            
    
    testOuter()
