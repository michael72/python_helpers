'''
Created on 16.02.2020

@author: Michael Schulte
'''
from _collections import deque
from multiprocessing import Condition
import os
import subprocess
import sys
from tempfile import mkstemp
from threading import Thread


def readLines(cmd, cwd=os.getcwd(), stderr=sys.stderr, shell=False, env=None):
    ''' Read the (stdout) output of a shell command line by line. 
    The code also handles the "GeneratorExit" event - i.e. when the file is read line by line, the searched lines are found and the loop is exited with break.
    
    Example:
    found = False
    for line in readLines(['mycommand', 'myparam1', 'myparam2'], cwd=mydir):
        if line == mySearchedLine:
            found = True
            break # GeneratorExit handled
     
    :param cmd: the command to be executed. On windows the command may have to wrapped with 'cmd /c' to execute batch or shell commands.
        cmd may either be a list or a string. If it contains a redirect '>' a batch file will be written and executed (Windows).
    :param cwd: current working directory to execute the command
    :param stderr: where stderr output (channel 2) of the command will be mapped. 
        - Default: sys.stderr will forward the messages to stderr output. 
        - None: no output of stderr
        - subprocess.PIPE: stderr output will be returned along the stdout lines to be parsed.
    :param shell: parameter is forwarded to Popen. See documentation there. Can be a security hazard. Interprets wildcards and access to env variables is set.
    '''
    if not isinstance(cmd, list):
        cmd = str(cmd).strip().split()

    isWindows = sys.platform.startswith("win")
    if isWindows:        
        si = subprocess.STARTUPINFO()
        # prevent cmd window to be shown 
        si.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE

    def oswrite(fh, txt):
        os.write(fh, txt.encode())

    callYield = True
    if stderr == None:
        callYield = False
        stderr = subprocess.PIPE
    tmpfile = None
        
    if env != None or (len(cmd) > 2 and '>' in cmd[-2] and '<' not in cmd[-2]):
        if isWindows:
            # piping or setting the env does not really work
            # hence: create a temporary batch file, add the correct environment and execute the batch file
            fh, tmpfile = mkstemp(suffix=".bat")
            oswrite(fh, "@echo off\r\n")  # suppress all output from the batch
            # set all environment variables that are in env-parameter but not in the os.environ
            if env != None:
                for k, v in env.items():
                    v2 = os.environ.get(k)
                    if v != v2:
                        oswrite(fh, "@set %s=%s\r\n" % (k, v))
            # set the correct directory
            if cwd != None:
                oswrite(fh, "@cd /d %s\r\n" % cwd)
            # leave out the cmd call within the batch file
            if cmd[0] == "cmd":
                cmd = cmd[2:]
            # support for piping ('>') is in this call
            oswrite(fh, " ".join(cmd) + "\r\n")
            
            oswrite(fh, "exit\r\n")
            cmd = ['cmd', '/c', tmpfile]
            os.close(fh)
        else:
            raise BaseException("Currently only implemented for Windows / Batch")

    try:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=stderr, shell=shell, env=env, startupinfo=si)
    except WindowsError as ex:
        sys.stderr.write(" ".join(cmd) + "\n")
        raise ex

    if stderr == subprocess.PIPE and callYield:
        lock = Condition()
        lines = deque()  # deque with lock is safer than multiprocessing.Queue
        
        def append_line(lines, lock, line):
            with lock:
                lines.append(line)
                lock.notify()
            
        # both stderr and stdout are returned (quasi in paralell)
        def enqueue_output(out, lines, lock):
            try:
                for line in iter(out.readline, b''):
                    append_line(lines, lock, line)
            except ValueError:
                # out was already closed
                pass
            try:
                append_line(lines, lock, '')
                out.close()
            except:
                pass  # out has been closed already
        
        tstd = Thread(target=enqueue_output, args=(proc.stdout, lines, lock))
        terr = Thread(target=enqueue_output, args=(proc.stderr, lines, lock))
        
        tstd.daemon = True  # thread dies with the program
        terr.daemon = True  # thread dies with the program
        
        tstd.start()
        terr.start()

        def getLineFromQ():
            with lock:
                try:
                    while (len(lines) == 0):
                        lock.wait()
                    return lines.popleft()
                except:
                    return ''  # queue is going to be closed 

        getLine = getLineFromQ
    else:
        # only read stdoutput
        getLine = proc.stdout.readline
    
    line = ' '
    while line:
        line = getLine()  # call either stdout.readline or the parallel version above
        if line:
            try:
                yield line.decode('utf-8', 'ignore').rstrip()  # utf-8 is converted to a usual string
            except GeneratorExit:
                # outer loop has finished: clean up
                try:
                    proc.stderr.close()
                except BaseException:
                    # could be stderr was already closed here
                    pass
                try:
                    proc.stdout.close()
                except BaseException:
                    # could be stdout was already closed here
                    pass
                break
            except:
                pass
    if tmpfile:
        os.remove(tmpfile)
