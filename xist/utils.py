#! /usr/bin/env python

## Copyright 2000 by LivingLogic AG, Bayreuth, Germany.
## Copyright 2000 by Walter D�rwald
##
## See the file LICENSE for licensing details

"""
This module contains several functions and classes,
that are used internally by XIST.
"""

__version__ = "$Revision$"[11:-2]
# $Source$

codeEncoding = "iso-8859-1"

import sys
import os
import types

def stringFromCode(text):
	if type(text) is types.StringType:
		return unicode(text, codeEncoding)
	else:
		return text

def forceopen(name, mode):
	try:
		return open(name, mode)
	except IOError, e:
		if e[0] != 2: # didn't work for some other reason
			raise
		found = name.rfind("/")
		if found == -1:
			raise
		os.makedirs(name[:found])
		return open(name, mode)

class Code:
	def __init__(self, text, ignorefirst=0):
		# get the individual lines; ignore "\r" as this would mess up whitespace handling later
		lines = text.replace("\r", "").split("\n")
		# split of the whitespace at the beginning of each line
		for i in xrange(len(lines)):
			line = lines[i]
			rest = line.lstrip()
			white = line[:len(line)-len(rest)]
			lines[i] = [white, rest]
		# drop all empty lines at the beginning; if we drop a line we no longer have to handle the first specifically
		while lines and not lines[0][1]:
			del lines[0]
			ignorefirst = 0
		# drop all empty lines at the end
		while lines and not lines[-1][1]:
			del lines[-1]
		# complain, if the first line contains whitespace, although ignorewhitespace said it doesn't
		if ignorefirst and lines and lines[0][0]:
			raise ValueError("can't ignore the first line, as it does contain whitespace")
		# find the shortest whitespace in non empty lines
		shortestlen = sys.maxint
		for i in xrange(ignorefirst, len(lines)):
			if lines[i][1]:
				shortestlen = min(shortestlen, len(lines[i][0]))
		# remove the common whitespace; a check is done, whether the common whitespace is the same in all lines
		common = None
		if shortestlen:
			for i in xrange(ignorefirst, len(lines)):
				if lines[i][1]:
					test = lines[i][0][:shortestlen]
					if common is not None:
						if common != test:
							raise SyntaxError("indentation mixmatch")
					common = test
					lines[i][0] = lines[i][0][shortestlen:]
				else:
					lines[i][0] = u""
		self.lines = lines

	def indent(self):
		for line in self.lines:
			line[0] = "\t" + line[0]

	def funcify(self, name="__"):
		self.indent()
		self.lines.insert(0, [u"", u"def " + name + u"():"])

	def asString(self):
		v = []
		for line in self.lines:
			v += line
			v += "\n"
		return "".join(v)

