#! /usr/bin/env python

## Copyright 2000 by LivingLogic AG, Bayreuth, Germany.
## Copyright 2000 by Walter D�rwald
##
## See the file LICENSE for licensing details

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

	def asHTML(self, mode=None):
		cases = self.find(type=case)

		return xsc.Null

class case(xsc.Element):
	empty = 0
	attrHandlers = {"case": xsc.TextAttr}

	def asHTML(self, mode=None):
		return self.content.asHTML(mode)

class If(xsc.Element):
	empty = 0
	attrHandlers = {"cond": CondAttr}
	name = "if"

	def asHTML(self, mode=None):
		intruecondition = self.__testCond(self["cond"], mode)
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
		return truecondition.asHTML(mode)

	def __testCond(self, attr, mode):
		cond = attr.asHTML(mode).asPlainString()
		result = eval(str(cond), procinst.__dict__)
		return result

class ElIf(xsc.Element):
	empty = 1
	attrHandlers = {"cond": CondAttr}
	name = "elif"

	def asHTML(self, mode=None):
		return xsc.Null

class Else(xsc.Element):
	empty = 1
	name = "else"

	def asHTML(self, mode=None):
		return xsc.Null

namespace = xsc.Namespace("cond", "http://www.livinglogic.de/DTDs/cond.dtd", vars())

