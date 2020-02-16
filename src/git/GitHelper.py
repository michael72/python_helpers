'''
Created on 16.02.2020

@author: Michael Schulte
'''
from difflib import SequenceMatcher
import os

from ExecHelper import readLines
from ReMatcher import ReMatcher


class GitCmd:
    ''' Helper to call git '''
    def __init__(self, command, cwd):
        if not isinstance(command, list):
            self.command = list(command.split(' '))
        else:
            self.command = command
        self.cwd = cwd
    def add(self, item):
        self.command.append(item)
        return self
    def extend(self, items):
        self.command.extend(items)
        return self
    def execute(self):
        cmd = ["git"] + self.command
        return readLines(cmd, cwd=self.cwd)
    def __iter__(self):
        return self.execute()

class Git:
    @classmethod
    def git(cls, command, cwd):
        ''' 
        Create a GitCmd on the given directoy
        '''
        return GitCmd(command, cwd)
    
    @classmethod
    def changedFiles(cls, sandbox, extension = ""):
        ''' 
        Get all changed files of given sandbox directory
        
        :param sandbox: sandbox directory 
        :param extension: file extension. Default is empty (all file types are returned). 
        :return: all changed files of the given extension 
        '''
        for line in cls.git("status -s -uno", sandbox):
            line = line.strip()
            if (line[1] == 'M' or (line[0] == 'M') or (line[0] == 'A')) and (line.endswith(extension)):
                idx = line.find(' -> ')
                if idx != -1:
                    yield os.path.join(sandbox, line[idx+4:]).replace('/', os.path.sep)
                else:
                    idx = line.find(' ')
                    yield os.path.join(sandbox, line[idx+1:].strip().replace('/', os.path.sep)) 

    @classmethod
    def mergeDiff(cls, linesRemoved, linesAdded, changesOnly=False):
        '''
        Combines the added lines and removed lines.
         
        Finds the best matches from linesAdded to linesRemoved - i.e. these are the lines that were changed    
        Example: linesRemoved = [(1, "first"), (2, "third")], linesAdded = [(1, "First"), (2, "Second"), (3, "Third")]
        should result in [((1, "first"), (1, "First")), (None, (2, "Second")), ((3, "third"), (3, "Third"))] being matched
               and NOT in [((1, "first"), (1, "First")), ((3, "third"), (2, "Second")), (None, (3, "Third"))] 
        
        :param linesRemoved: list of ((lineNo, content)) for each removed line in the diff
        :param linesAdded: list of ((lineNo, content)) for each added line in the diff
        :param changesOnly: if True only the matching pairs of changed lines (removed + added) are returned  
        ''' 
        minLen = min(len(linesRemoved), len(linesAdded))
        maxLen = max(len(linesRemoved), len(linesAdded))

        if minLen < maxLen:
            moreAdded = len(linesAdded) > len(linesRemoved)
            (linesLonger, linesShorter) = (linesAdded, linesRemoved) if moreAdded else (linesRemoved, linesAdded)

            bestMatches = []
            shortIdx = 0
            bestIdx = -1
            while shortIdx < minLen:
                bestRatio = 0
                # idx is restricted to already matched items and a minimum of minLen items that have to be matched.
                for idx in range(bestIdx+1, maxLen - (minLen - shortIdx) + 1):
                    # try to find the best matching lines 
                    # - this is a greedy algorithm finding that does not find the perfect solution 
                    # but the best solution for the first item, then the best for the second and so on. 
                    ratio = SequenceMatcher(None, linesLonger[idx][1], linesShorter[shortIdx][1]).ratio()
                    if ratio > bestRatio:
                        bestRatio = ratio
                        bestIdx = idx
                bestMatches.append(bestIdx)
                shortIdx += 1

            shortCnt = 0
            for idx in range(maxLen):
                if moreAdded:
                    if idx in bestMatches:
                        yield((linesRemoved[shortCnt], linesAdded[bestMatches[shortCnt]]))
                        shortCnt += 1
                    elif not changesOnly:
                        yield((None, linesAdded[idx]))
                else:
                    if idx in bestMatches:
                        yield((linesRemoved[bestMatches[shortCnt]], linesAdded[shortCnt]))
                        shortCnt += 1
                    elif not changesOnly:
                        yield((linesRemoved[idx], None))
        else:
            for item in zip(linesRemoved, linesAdded):
                yield item
        del linesAdded[:]
        del linesRemoved[:]
    
    @classmethod
    def diff(cls, f, changesOnly=False):
        lineNoRemove = 0
        lineNoAdd = 0
        patPlusMinus = ReMatcher("@@.*\\-([0-9]+)[ ,]+.*\\+([0-9]+)[ ,]+.*")
        linesRemoved = []
        linesAdded = []
        started = False
                    
        for line in cls.git("diff", os.path.dirname(f)).extend(["-U0", "-w", "--patience"]).add(f):
            if line.startswith("@@") and patPlusMinus.match(line):
                started = True
                # new section: return the previous merged results
                for item in cls.mergeDiff(linesRemoved, linesAdded, changesOnly):
                    yield item
                lineNoRemove = int(patPlusMinus.group(1))
                lineNoAdd = int(patPlusMinus.group(2))
            elif started:
                if line.startswith('+'):
                    linesAdded.append((lineNoAdd, line[1:]))
                    lineNoAdd += 1
                elif line.startswith('-'):
                    linesRemoved.append((lineNoRemove, line[1:]))
                    lineNoRemove += 1
                else:
                    pass # ignore line
        # end of last section: return the last results
        for item in cls.mergeDiff(linesRemoved, linesAdded, changesOnly):
            yield item
        
if __name__ == '__main__':
    for item in Git.mergeDiff(linesRemoved = [(1, "first"), (2, "third")], linesAdded = [(1, "First"), (2, "Second"), (3, "Third")]):
        print(item)
