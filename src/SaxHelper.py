'''
Created on 16.02.2020

@author: Michael Schulte
'''
import xml.sax

class SaxHelper(xml.sax.handler.ContentHandler):
    '''
    Helper for SAX content handler that adds the received characters
    to currentContent and parses the file with the given filename.
    
    class MyHandler(SaxHelper):
        # handle events
        
    with MyHandler(filename) as handler:
        # get handler results
    '''
    def __init__(self, filename, parent=None):
        self.currentContent = ''
        self.filename = filename
        self.parent = parent
    
    def characters(self, content):
        if len(self.currentContent) > 0:
            self.currentContent += '\n'
        self.currentContent += content.strip()
        
    def startElement(self, name, attrs):
        self.currentContent = ''
        xml.sax.handler.ContentHandler.startElement(self, name, attrs)

    def __enter__(self):
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        parser.parse(self.filename)
        return self
    
    def __exit__(self, _tp, exc_inst, tb):
        if exc_inst:
            raise exc_inst.with_traceback(tb)
            