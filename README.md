# python_helpers
Library of python helpers

## AsyncExec ##
Execute functions asynchronously in a defined number of threads with one synchronization point.

```python
with AsyncExec as ex:
    ex(somefun, params)
    ex(some_other_fun, maybe_other_params)
  
# here the function calls are synchronized
# (first) exception is forwarded
```
