#! /usr/bin/env python

## Copyright 1999-2001 by LivingLogic AG, Bayreuth, Germany.
## Copyright 1999-2001 by Walter D�rwald
##
## All Rights Reserved
##
## Permission to use, copy, modify, and distribute this software and its documentation
## for any purpose and without fee is hereby granted, provided that the above copyright
## notice appears in all copies and that both that copyright notice and this permission
## notice appear in supporting documentation, and that the name of LivingLogic AG or
## the author not be used in advertising or publicity pertaining to distribution of the
## software without specific, written prior permission.
##
## LIVINGLOGIC AG AND THE AUTHOR DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
## INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL
## LIVINGLOGIC AG OR THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL
## DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
## IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR
## IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This modules contains elements for doing conditionals
on the XML level.
"""

__version__ = tuple(map(int, "$Revision$"[11:-2].split(".")))
# $Source$

import xsc, html, procinst

class CodeAttr(xsc.Attr):
	"""
	used for attributes that contain Python code
	"""

class CondAttr(CodeAttr):
	"""
	used for Python conditions
	"""

class switch(xsc.Element):
	empty = 0
	attrHandlers = {"var": xsc.TextAttr}

	def transform(self, transformer=None):
		cases = self.find(type=case)

		return xsc.Null

class case(xsc.Element):
	empty = 0
	attrHandlers = {"case": xsc.TextAttr}

	def transform(self, transformer=None):
		return self.content.transform(transformer)

class If(xsc.Element):
	empty = 0
	attrHandlers = {"cond": CondAttr}
	name = "if"

	def transform(self, transformer=None):
		intruecondition = self.__testCond(self["cond"], transformer)
		truecondition = xsc.Frag()
		for child in self.content:
			if isinstance(child, ElIf):
				if intruecondition:
					break
				else:
					intruecondition = self.__testCond(child["cond"])
			elif isinstance(child, Else):
				if intruecondition:
					break
				else:
					intruecondition = 1
			else:
				if intruecondition:
					truecondition.append(child)
		return truecondition.transform(transformer)

	def __testCond(self, attr, transformer):
		cond = attr.transform(transformer).asPlainString()
		result = eval(str(cond), procinst.__dict__)
		return result

class ElIf(xsc.Element):
	empty = 1
	attrHandlers = {"cond": CondAttr}
	name = "elif"

	def transform(self, transformer=None):
		return xsc.Null

class Else(xsc.Element):
	empty = 1
	name = "else"

	def transform(self, transformer=None):
		return xsc.Null

namespace = xsc.Namespace("cond", "http://www.livinglogic.de/DTDs/cond.dtd", vars())

