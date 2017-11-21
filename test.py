# -*- coding: utf-8 -*-

try:
    from PyPDF2 import PdfFileReader, PdfFileWriter
except ImportError:
    import sys
    sys.path.append('PyPDF2/')

from PdfBookmark import PdfBookmark

bm1 = PdfBookmark('Samples/a1.pdf')
bm1.exportBookmarks('Samples/a1.bm')

bm0 = PdfBookmark('Samples/a0.pdf')
bm0.importBookmarks('Samples/a1.bm')
