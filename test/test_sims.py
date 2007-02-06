#! /usr/bin/env/python
# -*- coding: iso-8859-1 -*-

## Copyright 1999-2006 by LivingLogic AG, Bayreuth/Germany.
## Copyright 1999-2006 by Walter D�rwald
##
## All Rights Reserved
##
## See xist/__init__.py for the license


from __future__ import with_statement

import warnings

import py.test

from ll.xist import xsc, sims
from ll.xist.ns import html, php


oldfilters = None


def setup_module(module):
	global oldfilters
	oldfilters = warnings.filters[:]

	warnings.filterwarnings("error", category=sims.EmptyElementWithContentWarning)
	warnings.filterwarnings("error", category=sims.WrongElementWarning)
	warnings.filterwarnings("error", category=sims.ElementWarning)
	warnings.filterwarnings("error", category=sims.IllegalTextWarning)


def teardown_module(module):
	warnings.filters = oldfilters


def test_empty():
	with xsc.Pool():
		class el1(xsc.Element):
			model = sims.Empty()

		e = el1()
		e.asBytes()
	
		e = el1("gurk")
		py.test.raises(sims.EmptyElementWithContentWarning, e.asBytes)
	
		e = el1(php.php("gurk"))
		py.test.raises(sims.EmptyElementWithContentWarning, e.asBytes)
	
		e = el1(xsc.Comment("gurk"))
		py.test.raises(sims.EmptyElementWithContentWarning, e.asBytes)
	
		e = el1(el1())
		py.test.raises(sims.EmptyElementWithContentWarning, e.asBytes)


def test_elements():
	with xsc.Pool():
		class el11(xsc.Element):
			xmlname = "el1"
			xmlns = "ns1"
		class el12(xsc.Element):
			xmlname = "el2"
			xmlns = "ns1"
		class el21(xsc.Element):
			xmlname = "el1"
			xmlns = "ns2"
		class el22(xsc.Element):
			xmlname = "el2"
			xmlns = "ns2"

		el11.model = sims.Elements(el11, el21)
	
		e = el11()
		e.asBytes()
	
		e = el11("foo")
		py.test.raises(sims.IllegalTextWarning, e.asBytes)
	
		e = el11(php.php("gurk"))
		e.asBytes()
	
		e = el11(xsc.Comment("gurk"))
		e.asBytes()
	
		e = el11(el11())
		e.asBytes()
	
		e = el11(el21())
		e.asBytes()
	
		e = el11(el12())
		py.test.raises(sims.WrongElementWarning, e.asBytes)
	
		e = el11(el22())
		py.test.raises(sims.WrongElementWarning, e.asBytes)


def test_elementsortext():
	with xsc.Pool():
		class el11(xsc.Element):
			xmlname = "el1"
			xmlns = "ns1"
		class el12(xsc.Element):
			xmlname = "el2"
			xmlns = "ns1"
		class el21(xsc.Element):
			xmlname = "el1"
			xmlns = "ns2"
		class el22(xsc.Element):
			xmlname = "el2"
			xmlns = "ns2"

		el11.model = sims.ElementsOrText(el11, el21)
	
		e = el11()
		e.asBytes()
	
		e = el11("foo")
		e.asBytes()
	
		e = el11(php.php("gurk"))
		e.asBytes()
	
		e = el11(xsc.Comment("gurk"))
		e.asBytes()
	
		e = el11(el11())
		e.asBytes()
	
		e = el11(el21())
		e.asBytes()
	
		e = el11(el12())
		py.test.raises(sims.WrongElementWarning, e.asBytes)
	
		e = el11(el22())
		py.test.raises(sims.WrongElementWarning, e.asBytes)


def test_noelements():
	with xsc.Pool():
		class el1(xsc.Element):
			xmlns = "ns1"
			model = sims.NoElements()
		class el2(xsc.Element):
			xmlns = "ns2"

		e = el1()
		e.asBytes()
	
		e = el1("foo")
		e.asBytes()
	
		e = el1(php.php("gurk"))
		e.asBytes()
	
		e = el1(xsc.Comment("gurk"))
		e.asBytes()
	
		e = el1(el1())
		py.test.raises(sims.ElementWarning, e.asBytes)

		# Elements from a different namespace are OK
		e = el1(el2())
		e.asBytes()


def test_noelementsortext():
	with xsc.Pool():
		class el1(xsc.Element):
			xmlns = "ns1"
			model = sims.NoElementsOrText()
		class el2(xsc.Element):
			xmlns = "ns2"

		e = el1()
		e.asBytes()
	
		e = el1("foo")
		py.test.raises(sims.IllegalTextWarning, e.asBytes)
	
		e = el1(php.php("gurk"))
		e.asBytes()
	
		e = el1(xsc.Comment("gurk"))
		e.asBytes()
	
		e = el1(el1())
		py.test.raises(sims.ElementWarning, e.asBytes)
	
		# Elements from a different namespace are OK
		e = el1(el2())
		e.asBytes()
