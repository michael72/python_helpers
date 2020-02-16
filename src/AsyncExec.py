'''
Created on 16.02.2020

@author: Michael Schulte
'''

import sys
from threading import Thread
from multiprocessing import Condition, cpu_count


class AsyncExec(object):
    '''
    Executes function calls asynchronously starting immediately with the first call.
    If an exception occured the exception is re-raised in the join call or in the exit when used with 'with'. 
    
    Example:
    with AsyncExec().fun(myLongRunningCall) as exc:
        # ...
        exc(myParameters) # the function myLongRunningCall is executed with parameters in a thread
        
    # exception occurring in exc call are thrown when 'with' exits.
    
    :param num_threads: number of threads to use in parallel
    :param add_results: either None or an empty list where the function call results are appended.
    '''

    def __init__(self, num_threads=cpu_count(), add_results=False, result_callback=None):
        self.pending_calls = []
        self.workers = []
        self.num_threads = num_threads
        self.exception = None
        self.running = True
        self.add_results = add_results
        self.results = [] if add_results else None
        self.result_callback = result_callback
        self.lock = create_close_condition()
        
        # start the threads
        while len(self.workers) < self.num_threads:
            t = Thread(target=self.__run)
            t.daemon = True
            self.workers.append(t)
            t.start()
    
    def fun(self, fun_call):
        ''' Wrap the function call - so only the parameters have to be added '''
        return AsyncFun(fun_call, self)
            
    def __add(self, fun, *params):
        if not self.running:
            raise BaseException("Wrong state - cannot add actions to already closing / closed AsyncExec")
        idx = 0
        if self.add_results:
            idx = len(self.results)
            self.results.append(None)
        self.pending_calls.append((idx, fun, params))
        
    def add(self, fun, *params):
        ''' add a single function call with parameters '''
        with self.lock:
            self.__add(fun, *params)
            self.lock.notify()
        return self
    
    def add_calls(self, fun, params_list, lockit=True):
        ''' add a list of params for a given function 
        :param params_list: a list of parameters. A list of tuples will be unpacked. If the function receives one tuple, each tuple
        in the list must be packed as a single-element tuple.
        :param lockit: should be True, except when the lock is already acquired from the outside.
        '''
        if lockit:
            self.lock.acquire()
        if len(params_list) > 0:
            if isinstance(params_list[0], tuple):
                for params in params_list:
                    self.__add(fun, *params)
            else:
                for param in params_list:
                    self.__add(fun, param)                    
        if lockit:
            self.lock.notify_all()
            self.lock.release()
        return self
    
    def join(self):
        ''' Wait for the running threads to finish and join to main thread. 
        :return: results of function calls - if add_results was set in init
        :raises: re-raises any exception that was caught during the function call '''
        if self.running:
            self.running = False
            
            with self.lock:
                self.lock.notify_all()
                if (len(self.pending_calls) == 0):
                    self.lock.close()
                    
            # wait for workers to finish
            for worker in self.workers:
                worker.join()
                    
            with self.lock:
                self.lock.close()
    
            if self.exception:
                # re-raise exception
                _, exc_inst, tb = self.exception
                raise exc_inst.with_traceback(tb)

        return self.results
    
    def __run(self):
        ''' internal function called from thread '''
        while not self.exception and not self.lock.closed:
            fun = None
            with self.lock:
                if len(self.pending_calls) > 0:
                    idx, fun, params = self.pending_calls.pop()
                elif not self.running:
                    self.lock.close()
                else:
                    self.lock.wait()
            
            if fun and not self.exception:
                try:
                    result = fun(*params)
                    if self.add_results:
                        self.results[idx] = result
                except:
                    if not self.exception:
                        self.exception = sys.exc_info()
                    with self.lock:
                        self.pending_calls = []
                        self.lock.close()
                
                if self.result_callback and not self.exception:
                    with self.lock:
                        self.result_callback(result)    
            
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
    
    def map(self, params):
        ''' Take a list of parameters and returns a list of tuples with the params -> results. '''
        with self:
            if not self.async_exec.add_results:
                self.async_exec.add_results = True
                self.async_exec.results = []
                idx = 0
            else:
                idx = len(self.async_exec.results)
                self.async_exec.results.extend([None] * len(params))
            self.async_exec.add_calls(self.fun, params, lockit=False)
            return zip(params, self.join()[idx:])


if __name__ == '__main__':
    import time
    
    def testOuter():

        def fib(i):
            if i <= 1:
                return i
            return fib(i - 2) + fib(i - 1)

        if True:        
            exc = AsyncExec(add_results=True)      
            exc.add(fib, 10)
            exc.add(fib, 1)
            exc.add(fib, 30)
            exc.add(fib, 22)
            exc.join()
            print(exc.results)

        if True:        
            res = dict(AsyncExec().fun(fib).map(range(25)))
            print(res)

        def testfun(t, loops, msg):
            for _ in range(loops):
                time.sleep(t)
                sys.stdout.write(msg)
                sys.stdout.flush()
            #raise BaseException("Test exception: " + msg)

        if True:
            with AsyncExec(3).fun(testfun) as test_print:
                test_print(0.5, 5, '*')
                test_print(0.5, 10, '+')
                test_print(1.5, 4, '-')
                test_print(1, 10, '=')
                test_print(0.1, 10, 'x')
            print("")
    
    testOuter()
