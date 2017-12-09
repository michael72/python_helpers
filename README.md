# python_helpers
Library of python helpers - compatible with Python 2.7.x and 3.x

## AsyncExec ##
Execute functions asynchronously in a defined number of threads with one synchronization point. Exceptions are forewarded to the caller.

AsyncExec using a local function works. In Python 2.7.x using `Pool` or `Queue` with a local function would yield a 
> PicklingError: Can't pickle <type 'function'>

```python
with AsyncExec as ex:
    ex(somefun, params)
    ex(some_other_fun, maybe_other_params)
  
# here the function calls are synchronized
# (first) exception is forwarded
```
