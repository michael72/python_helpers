'''
Created on 16.02.2020

@author: Michael Schulte
'''
import os
import stat
import sys
import traceback
import ExecHelper
from typing import List


def getLines(filename: str, strip: bool=True):
    with open(filename, 'r') as f:
        for line in f:
            yield line.strip() if strip else line

       
def isWritable(filename: str) -> bool:
    return os.path.exists(filename) and (os.stat(filename).st_mode & stat.S_IWRITE) == stat.S_IWRITE


def makeWritable(filename: str) -> None:
    if os.path.exists(filename) and not isWritable(filename):
        os.chmod(filename, stat.S_IWRITE)    


def forceRemove(filename: str) -> None:
    if os.path.exists(filename):
        makeWritable(filename)
        os.remove(filename)

            
def getCommonDir(fileNames: List[str]) -> str:
    ''' Gets the common parent directory of given file paths '''
    commonDir = None 
    for f in fileNames:
        curDir = os.path.dirname(f)
        if commonDir == None:
            commonDir = curDir
        else:
            commonDirParts = commonDir.split(os.path.sep)
            # compare all directory elements (between seperators)
            for idx, (commonDirPart, currentDirPart) in enumerate(zip(commonDirParts, curDir.split(os.path.sep))):
                if commonDirPart != currentDirPart:
                    commonDir = os.path.sep.join(commonDirParts[:idx])
                    break
    return commonDir


class BackupFile:
    ''' Easy handling for changing files:
    + writes to a backup file (ending with ~)
    + removes the backup on error automatically
    + on success:
    + renames the original to an additional backup (ending with double ~~) 
    + renames the backup to the original
    + removes the additional backup
     
    As a result the original file should be completely available
    or - in rare cases - it is not available, but the "~~"-file is present. 
    '''

    def __init__(self, origFile, openArgs='wb'):
        self.origFile = origFile
        self.backupFile = origFile + '~'
        self.backBackup = self.backupFile + '~' 
        self.fileHandle = None 
        self.openArgs = openArgs
     
    def create(self):
        forceRemove(self.backupFile)
        self.fileHandle = open(self.backupFile, self.openArgs).__enter__() 
     
    @classmethod
    def checkRestore(cls, chkFile):
        ''' Use this method to check in advance if the original file has been deleted and should be restored
        :param chkFile: is either the original file or the back-backup (with ~~) - the file with only one ~ could be in unfinished state
        '''
        if chkFile.endswith('~~'):
            backBackup = chkFile
            origFile = chkFile[:-2]
        else:
            origFile = chkFile
            backBackup = origFile + '~~'

        if os.path.exists(backBackup):
            if not os.path.exists(origFile):
                os.rename(backBackup, origFile)
            else:
                forceRemove(backBackup)
        return origFile 
     
    def restore(self):
        try:
            self.fileHandle.close()
        except BaseException:
            pass
        if os.path.exists(self.backupFile):
            os.remove(self.backupFile)
     
    def finish(self):
        self.fileHandle.close()
        if os.path.exists(self.origFile) and os.path.exists(self.backupFile):
            forceRemove(self.backBackup)
            os.rename(self.origFile, self.backBackup)
            os.rename(self.backupFile, self.origFile)
            forceRemove(self.backBackup)
     
    def write(self, content):
        self.fileHandle.write(content)
     
    def __enter__(self):
        self.create()
        return self
     
    def __exit__(self, tpe, value, tb):
        if tb: 
            self.restore();
            sys.stderr.write("Error when creating backed up file %s\n" % (self.origFile))
            traceback.print_exception(tpe, value, tb, None, sys.stderr)
            sys.stderr.write("Backup was rolled back\n")
        else:
            self.finish()
            
    @staticmethod
    def workOnContent(filename, fun):
        changed = False
        with BackupFile(filename) as bk: 
            with open(filename, 'r') as reader:
                for line in reader:
                    line = line.rstrip('\r\n')
                    outline = fun(line)
                    changed = changed or line != outline
                    if outline != None:
                        bk.write(outline + '\r\n')
            if not changed:
                bk.restore()
        return bk
                
    @staticmethod
    def workOnContentLines(filename, fun):
        with BackupFile(filename) as bk:
            linesIn = list(ExecHelper.readLines(filename))
            changed, linesOut = fun(linesIn)
            if changed:
                for line in linesOut:
                    bk.write(line + '\r\n')        
            else:
                bk.restore()
        return bk
