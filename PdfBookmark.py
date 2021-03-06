#!/usr/bin/python
# -*- coding: UTF-8 -*-

# Author: Shaoqian Qin
# Contact: qinshaoq@gmail.com
#
# Function:
#	1) Export PDF's bookmarks to a user-defined bookmark file
#	2) Import from bookmark file and add bookmarks to PDF
#
# Requirement:
#	Python 2.7, PyPDF2
#
# Bookmark file format(Example):
# *****************************************************************************
# * Chapter 1 Title 1 1                                                       *
# * Chapter 2 Title 2 4                                                       *
# * \t2.1 SubTitle 2.1 4.2                                                    *
# * \t\t2.1.1 SubTitle 2.1.1 4.5                                              *
# * \t2.2 SubTitle 2.2 7.3                                                    *
# * Chapter 3 Title 3 8                                                       *
# *****************************************************************************
# \t represents a Tab key, other white spaces are not available temporarily.
# The number of Tab represents the hierarchical structure of the bookmark.
# In each line, the content is |tabs| |bookmark title| |page ratio|.
# |bookmark title| and |page ratio| must be separated by white spaces.
# |page ratio| is a decimal number, the integer part represents the page number
# of the bookmark, the fractional part represents the location of the bookmark.
# .0 indicates that the bookmark is on the top of the page, .99 indicates that
# the bookmark is almost on the bottom of the page.

import sys, re, codecs
from PyPDF2 import PdfFileReader, PdfFileWriter

def _writeBookmarksToStream(outlines, stream, level):
    """
    Write bookmarks to the specified output stream.
    param outlines: PyPDF2.generic.Destination list
    param level: bookmark level, the topmost level is 0
    """
    for i in range(0, len(outlines)):
        outline = outlines[i]
        if type(outline) == list:
            _writeBookmarksToStream(outline, stream, level+1)
        else:
            for j in range(0,level):
                stream.write('\t')
            bmTitle = outline['/Title']
            bmRatio = outline['/Ratio']
            stream.write(bmTitle + ' ' + ('%.2f' % bmRatio) + '\n')

def readBookmarksFromFile(bmPathName):
    """
    Read bookmarks from file and store the content in dict list.
    return: outlines-dict list which has '/Title' and '/Ratio' keys
    """
    outlines = []
    lastTabNum = 0
    r = re.compile( r'\s*(.*)\s+(\d+\.*\d*)\s*' )
    r2 = re.compile( r'\s*\S.*' )
    for line in open(bmPathName):
        if not r2.match(line): # line contain only white spaces
            continue
        matchObj = r.match(line)
        if not matchObj:
            print 'bookmarks format error at: ' + line
            sys.exit(1)
        tabNum = matchObj.start(1)
        bmTitle = matchObj.group(1)
        pageRatio = float(matchObj.group(2))-1
        bmPage = int(pageRatio)
        bmRatio = pageRatio-bmPage
        outline={}
        outline['/Title'] = bmTitle
        outline['/Ratio'] = pageRatio
        tempOutlines = outlines
        if tabNum > lastTabNum+1:
            print 'bookmarks format extra tab(s) at: ' + line
            sys.exit(0)
        elif tabNum == lastTabNum+1:
            for i in range(0, tabNum-1):
                tempOutlines = tempOutlines[-1]
            tempOutlines.append([outline])
        else:
            for i in range(0, tabNum):
                tempOutlines = tempOutlines[-1]
            tempOutlines.append(outline)
        lastTabNum = tabNum
    return outlines

def _writeOutlinesToPdf(outlines, output, parent):
    """
    Add bookmarks stored in outlines.
    param output: PyPDF2.PdfFileWriter object
    param parent: parent bookmark
    """
    lastBm = parent
    for i in range(0, len(outlines)):
        outline = outlines[i]
        if not type(outline) == list:
            ratio = outline['/Ratio']
            bmTitle = (outline['/Title']).decode('UTF-8')
            bmTitle = (u'\uFEFF' + bmTitle).encode('UTF-16-BE') # see PDF reference(version 1.7) section 3.8.1
            bmPage = int(ratio)
            bmTop = (float)(output.getPage(0).mediaBox.getHeight())*(1-(ratio-bmPage))
            bmCur = output.addBookmark(bmTitle, bmPage, parent, None, False, False, '/FitH', bmTop)
            lastBm = bmCur
        else:
            _writeOutlinesToPdf(outline, output, lastBm)

class PdfBookmark(object):
    """
    This class supports import/export PDF's
    bookmarks from/to a file.
    """
    def __init__(self, pdfPathName):
        self.pdfFileName = pdfPathName
        self._pdfStream = open(self.pdfFileName, 'rb')
        self._pdfReader = PdfFileReader(self._pdfStream)

        self.pageLabels = self._getPageLabels()
        self.outlines = self._pdfReader.getOutlines()
        self._addPageRatio(self.outlines, self.pageLabels)

    def getBookmarks(self):
        """
        Retrieve this pdf's bookmarks.
        """
        return self.outlines

    def exportBookmarks(self, bmPathName):
        """
        Export bookmarks to specified bookmarksFileName, overwrites!
        """
        stream = codecs.open(bmPathName, 'w', encoding='utf8')
        _writeBookmarksToStream(self.outlines, stream, 0)
        print "Export %s's bookmarks to %s finished!" % (self.pdfFileName, bmPathName)

    def importBookmarks(self, bmPathName, saveAsPdfName=None):
        """
        Import the contents from a bmPathName and add these
        either current input PDF file or specified output PDF file.
        """
        outlines = readBookmarksFromFile(bmPathName)
        output = PdfFileWriter()
        for i in range(0, self._pdfReader.getNumPages()):
            output.addPage(self._pdfReader.getPage(i))
        _writeOutlinesToPdf(outlines, output, None)

        if saveAsPdfName == None:
            saveAsPdfName = self.pdfFileName[0:-4] + '_bookmark.pdf'
        stream = open(saveAsPdfName, 'wb')
        output.write(stream)
        print "Added bookmarks from %s to %s finished!" % (bmPathName, saveAsPdfName)

    def _getPageLabels(self):
        """
        Get the map from IndirectObject id to real page number.
        """
        pageLabels = {}
        pages = list(self._pdfReader.pages)
        for i in range(0, len(pages)):
            page = pages[i]
            pageLabels[page.indirectRef.idnum] = i+1
        return pageLabels

    def _addPageRatio(self, outlines, pageLabels):
        """
        Retrieves page ratio from Destination list.
        param outlines: Destination list
        param pageLabels: map from IndirectObject id to real page number
        """
        for i in range(0, len(outlines)):
            outline = outlines[i]
            if type(outline) == list:
                self._addPageRatio(outlines[i], pageLabels)
                continue
            elif not outline.has_key('/Page'):
                print "Error: outline has no key '/Page'"
                sys.exit(-1)
            pageHeight = outline['/Page']['/MediaBox'][-1]
            idIndirect = outline.page.idnum
            if pageLabels.has_key(idIndirect):
                pageNum = pageLabels[idIndirect]
            else:
                print 'Error: Page corresponds to IndirectObject %d not Found' % idIndirect
                sys.exit(-1)
            if outline.has_key('/Top'):
                top = outline['/Top']
            else:
                top = pageHeight
            if outline.has_key('/Zoom'):
                zoom = outline['/Zoom']
            else:
                zoom = 1
            outline = dict(outline)
            outline['/Ratio'] = pageNum + (1 - top / zoom / pageHeight)
            outlines[i] = outline

# for development/testing, hah
def main():
    if sys.platform == "win32":
        sys.path.append('D:/QSQ/Desktop/PyPDF2-master/')

    # read the original/input PDF file
    bm = PdfBookmark('Samples/a0.pdf')
    # show/view bookmarks dict
    print bm.getBookmarks()
    # import bookmarks/outlines text file
    bm.importBookmarks('Samples/a1.bm')

if __name__=='__main__':
    main()
