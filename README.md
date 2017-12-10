# python_helpers
Library of python helpers - compatible with Python 2.7.x and 3.x

## AsyncExec ##
Execute functions asynchronously in a defined number of threads with one synchronization point. Exceptions are forewarded to the caller.

In Python 2.7.x using `Pool` or `Queue` with a local function would yield a 
> PicklingError: Can't pickle <type 'function'>

`AsyncExec` using a local function also works with Python 2.7.x. 

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
print(results)     # results are in the same order as were the added function calls
print(exc.results) # also works

# Shortcut for a single function with different parameters
with AsyncExec().fun(some_fun) as asyncfun:
    asyncfun(params)
    asyncfun(other_params)

# Using mapping functionality on a single function
def fib(i):
    return i if i <= 1 else fib(i-2) + fib(i-1)
    
res = dict(AsyncExec().fun(fib).map(range(25))) # map returns a list of tuples (param, result)
print(res) # prints {0: 0, ..., 23: 28657, 24: 46368}


```
