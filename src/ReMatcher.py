import re
import copy


class ReMatcher(object):
    ''' Easier use of regular expressions 
    
    Instead of:
    regex = re.compile('my regex')
    ...
    m = regex.match('bla')
    if m:
        some, content = m.groups()

    You can use:
    myPattern = ReMatcher('my regex')
    ...    
    if myPattern('bla'):
        some, content = myPattern.groups()
    
    or even perform an (exhaustive) search:
    
    for item in myPattern('bla bla'):
        print(item)
    '''
    def __init__(self, matchstring):
        self.regex = re.compile(matchstring)

    def match(self,chk):
        self.m = self.regex.match(chk)
        return bool(self.m)
    
    def findall(self, chk):
        return self.regex.findall(chk)
    
    def __call__(self, chk):
        ''' shortcut for both match and findall '''
        return self.regex.findall(chk)

    def group(self,i):
        return self.m.group(i)
    
    def groups(self):
        return self.m.groups()
    
    def copy(self):
        return copy.copy(self)
    
    def __iter__(self):
        return self
        
