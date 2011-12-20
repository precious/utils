#!/usr/bin/python

import gtk
import os
import sys

clipboard = gtk.clipboard_get()
pixbuf = clipboard.wait_for_image()
if not pixbuf:
	exit(1)
else:
	path = sys.argv[1] if len(sys.argv) > 1 else os.getenv('HOME')
	path = os.tempnam(path) + '.png'
	pixbuf.save(path,'png')
	print path
