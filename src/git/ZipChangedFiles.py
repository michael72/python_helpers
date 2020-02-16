'''
Created on 16.02.2020

@author: Michael Schulte
'''

from datetime import datetime
import os
from zipfile import ZipFile

from git.GitHelper import Git


class ZipChangedFiles(object):

    def __init__(self, args):
        self.args = args
    
    def performZip(self):
        zipfile = self.args.outputfile
        if zipfile == None:
            dt = datetime.now()
            zipfile = self.args.projectpath + '_' + dt.strftime("%Y%m%d_%H%M%S.zip")
        if self.args.verbose:
            print("creating zip file " + zipfile)
        with ZipFile(zipfile, 'w') as myzip:
            for f in Git.changedFiles(self.args.projectpath):
                if self.args.verbose:
                    print("adding " + f)
                if not os.path.basename(f).startswith('.'):  # ignore .cproject, etc
                    myzip.write(f)                


def main():
    import argparse
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='Add changed and added files in git repo to a zip file')

    parser.add_argument('-v', '--verbose', help='Print additional info', required=False, default=False, action='store_true')
    parser.add_argument('-p', '--projectpath', help='local project path', required=True)
    parser.add_argument('-o', '--outputfile', help='output zip file', required=False, default=None)
    
    ZipChangedFiles(parser.parse_args()).performZip()


if __name__ == '__main__':
    main()
