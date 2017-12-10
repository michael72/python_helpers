# python_helpers
Library of python helpers - compatible with Python 2.7.x and 3.x

## AsyncExec ##
Execute functions asynchronously in a defined number of threads with one synchronization point. Exceptions are forewarded to the caller.

AsyncExec using a local function works. In Python 2.7.x using `Pool` or `Queue` with a local function would yield a 
> PicklingError: Can't pickle <type 'function'>

```python
with AsyncExec(2) as ex:
    ex(somefun, params)
    ex(some_other_fun, maybe_other_params)
# here the function calls are synchronized
# (first) exception is forwarded

# Alternative function calls
exc = AsyncExec(append_results = true) # append function call results to a list
# ...
exc.add(oneCall)
# ...
exc.add(anotherCall)
# ...
results = exc.join() # wait for function calls to finish
print(results) 
print(exc.results) # also works

# Shortcut for a single function with different parameters
asyncfun = Async().fun(some_fun)
asyncfun(params)
asyncfun(other_params)

# Using mapping functionality on a single function
def fib(i):
    if i <= 1:
        return i
    return fib(i-2) + fib(i-1)
          
res = dict(AsyncExec().fun(fib).map(range(25)))
print(res) # prints {0: 0, ..., 23: 28657, 24: 46368}


```
