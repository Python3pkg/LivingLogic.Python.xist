#! /usr/bin/env/python
# -*- coding: iso-8859-1 -*-

## Copyright 1999-2005 by LivingLogic AG, Bayreuth/Germany.
## Copyright 1999-2005 by Walter D�rwald
##
## All Rights Reserved
##
## See xist/__init__.py for the license

import sys, unittest, cStringIO, warnings

from xml.sax import saxlib
from xml.parsers import expat

import py.test

from ll import url
from ll.xist import xsc, parsers, cssparsers, presenters, converters, helpers, options, sims, xnd, xfind
from ll.xist.ns import wml, ihtml, html, chars, abbr, specials, htmlspecials, meta, form, php, xml, tld, docbook


# set to something ASCII, so presenters work, even if the system default encoding is ascii
options.reprtab = "  "


def createattr():
	return html.span.Attrs.lang(
		True,
		False,
		url.URL("http://www.python.org/"),
		html.abbr(
			xml.XML10(),
			"hurz",
			specials.tab(),
			abbr.xist(),
			None,
			1,
			2.0,
			"3",
			u"4",
			(5, 6),
			[7, 8],
			html.span("gurk"),
			title="hurz"
		)
	)


def createattrs():
	return html.span.Attrs(
		lang=(
			True,
			False,
			url.URL("http://www.python.org/"),
			html.abbr(
				xml.XML10(),
				"hurz",
				specials.tab(),
				abbr.xist(),
				None,
				1,
				2.0,
				"3",
				u"4",
				(5, 6),
				[7, 8],
				html.span("gurk"),
				title="hurz"
			)
		)
	)


def createelement():
	return html.span(
		1,
		2,
		class_="gurk",
		id=(1, 2, (3, 4)),
		lang=(
			True,
			False,
			url.URL("http://www.python.org/"),
			html.abbr(
				xml.XML10(),
				"hurz",
				specials.tab(),
				abbr.xist(),
				None,
				1,
				2.0,
				"3",
				u"4",
				(5, 6),
				[7, 8],
				html.span("gurk"),
				title="hurz"
			)
		)
	)


def createfrag():
	return xsc.Frag(
		xml.XML10(),
		html.DocTypeHTML401transitional(),
		xsc.Comment("gurk"),
		"hurz",
		specials.tab(),
		abbr.xist(),
		None,
		True,
		False,
		1,
		2.0,
		"3",
		u"4",
		(5, 6),
		[7, 8],
		html.div(
			align="left"
		),
		url.URL("http://www.python.org/"),
		html.span(
			1,
			2,
			class_="gurk",
			id=(1, 2, (3, 4)),
			lang=(
				True,
				False,
				url.URL("http://www.python.org/"),
				html.abbr(
					xml.XML10(),
					"hurz",
					specials.tab(),
					abbr.xist(),
					None,
					1,
					2.0,
					"3",
					u"4",
					(5, 6),
					[7, 8],
					html.span("gurk"),
					title="hurz"
				)
			)
		)
	)


def allnodes():
	return (xsc.Null, createattr(), createattrs(), createelement(), createfrag())


def check_lenunicode(node, _len, content):
	assert len(node) == _len
	assert unicode(node) == content


def test_fraglen():
	check_lenunicode(xsc.Frag(), 0, u"")
	check_lenunicode(xsc.Frag(1), 1, u"1")
	check_lenunicode(xsc.Frag(1, 2, 3), 3, u"123")
	check_lenunicode(xsc.Frag(None), 0, u"")
	check_lenunicode(xsc.Frag(None, None, None), 0, u"")
	check_lenunicode(xsc.Frag(1, None, 2, None, 3, None, 4), 4, u"1234")
	check_lenunicode(xsc.Frag(1, (2, 3)), 3, u"123")
	check_lenunicode(xsc.Frag(1, (None, None)), 1, u"1")


def test_append():
	for cls in (xsc.Frag, html.div):
		node = cls()
		node.append(1)
		check_lenunicode(node, 1, u"1")
		node.append(2)
		check_lenunicode(node, 2, u"12")
		node.append()
		check_lenunicode(node, 2, u"12")
		node.append(3, 4)
		check_lenunicode(node, 4, u"1234")
		node.append(None)
		check_lenunicode(node, 4, u"1234")
		node.append((5, 6))
		check_lenunicode(node, 6, u"123456")


def test_extend():
	for cls in (xsc.Frag, html.div):
		node = cls()
		node.extend([1])
		check_lenunicode(node, 1, u"1")
		node.extend([2])
		check_lenunicode(node, 2, u"12")
		node.extend([])
		check_lenunicode(node, 2, u"12")
		node.extend([None])
		check_lenunicode(node, 2, u"12")
		node.extend([3, 4])
		check_lenunicode(node, 4, u"1234")
		node.extend([[], [[], [5], []]])
		check_lenunicode(node, 5, u"12345")


def test_insert():
	for cls in (xsc.Frag, html.div):
		node = cls()
		node.insert(0, 1)
		check_lenunicode(node, 1, u"1")
		node.insert(0, 2)
		check_lenunicode(node, 2, u"21")
		node.insert(0, 3, 4)
		check_lenunicode(node, 4, u"3421")
		node.insert(0, None)
		check_lenunicode(node, 4, u"3421")
		node.insert(0, (5, 6))
		check_lenunicode(node, 6, u"563421")


def test_iadd():
	for cls in (xsc.Frag, html.div):
		node = cls()
		node += [1]
		check_lenunicode(node, 1, u"1")
		node += [2]
		check_lenunicode(node, 2, u"12")
		node += []
		check_lenunicode(node, 2, u"12")
		node += [None]
		check_lenunicode(node, 2, u"12")
		node += [3, 4]
		check_lenunicode(node, 4, u"1234")
		node += [[], [[], [5], []]]
		check_lenunicode(node, 5, u"12345")


def test_len():
	for cls in (xsc.Frag, html.div):
		check_lenunicode(cls(), 0, u"")
		check_lenunicode(cls(1), 1, u"1")
		check_lenunicode(cls(1, 2, 3), 3, u"123")
		check_lenunicode(cls(None), 0, u"")
		check_lenunicode(cls(None, None, None), 0, u"")
		check_lenunicode(cls(1, None, 2, None, 3, None, 4), 4, u"1234")
		check_lenunicode(cls(1, (2, 3)), 3, u"123")
		check_lenunicode(cls(1, (None, None)), 1, u"1")


def test_standardmethods():
	for node in allnodes():
		node.compact()
		node.normalized()
		list(node.walk((True, xsc.enterattrs, xsc.entercontent)))
		node.find((True, xsc.enterattrs, xsc.entercontent))
		node.pretty()
		node.clone()
		node.conv()
		node.normalized().compact().pretty()


def test_standardmethods2():
	for node in (createelement(), createfrag()):
		node.sorted()
		node.shuffled()
		node.reversed()


def test_stringify():
	for node in allnodes():
		unicode(node)
		str(node)
		node.asString()
		node.asBytes()


def test_asText():
	for node in allnodes():
		node.asText()
		node.asText(monochrome=True)
		node.asText(squeezeBlankLines=True)
		node.asText(lineNumbers=True)
		node.asText(width=120)


def test_number():
	node = html.div(class_=1234)
	assert int(node["class_"]) == 1234
	assert long(node["class_"]) == 1234L
	assert abs(float(node["class_"]) - 1234.) < 1e-2
	node = html.div(class_="1+1j")
	compl = complex(node["class_"])
	assert abs(compl.real - 1.) < 1e-2
	assert abs(compl.imag - 1.) < 1e-2


def test_prefix():
	node = html.div()
	assert node.xmlprefix() == "html"


def test_write():
	node = html.div()
	io = cStringIO.StringIO()
	node.write(io, xhtml=2)
	assert io.getvalue() == "<div/>"


def test_mul():
	node = xsc.Frag("a")
	assert 3*node == xsc.Frag(list("aaa"))
	assert node*3 == xsc.Frag(list("aaa"))

	node = html.div()
	assert 3*node == xsc.Frag(html.div(), html.div(), html.div())
	assert node*3 == xsc.Frag(html.div(), html.div(), html.div())


def test_text():
	s = "test"
	node = xsc.Text(s)
	hash(node)
	assert len(node), 4
	assert node[1] == xsc.Text("e")
	assert 3*node == xsc.Text(3*s)
	assert node*3 == xsc.Text(s*3)
	assert node[1:3] == xsc.Text("es")
	assert node.capitalize() == xsc.Text("Test")
	assert node.center(8) == xsc.Text("  test  ")
	assert node.count("t") == 2
	assert node.endswith("st") is True
	assert node.index("s") == 2
	assert node.isalpha() is True
	assert node.isalnum() is True
	assert node.isdecimal() is False
	assert node.isdigit() is False
	assert node.islower() is True
	assert node.isnumeric() is False
	assert node.isspace() is False
	assert node.istitle() is False
	assert node.isupper() is False
	assert node.join(xsc.Frag(list("abc"))) == xsc.Frag("a", "test", "b", "test", "c")
	assert node.ljust(6) == xsc.Text("test  ")
	assert node.ljust(6, ".") == xsc.Text("test..")
	assert node.lower() == xsc.Text("test")
	assert xsc.Text("  test").lstrip() == xsc.Text("test")
	assert node.replace("s", "x") == xsc.Text("text")
	assert node.rjust(6) == xsc.Text("  test")
	assert node.rjust(6, ".") == xsc.Text("..test")
	assert xsc.Text("test  ").rstrip() == xsc.Text("test")
	assert node.rfind("s") == 2
	assert node.rindex("s") == 2
	assert node.split("e") == xsc.Frag("t", "st")
	assert xsc.Text("a\nb\n").splitlines() == xsc.Frag("a", "b")
	assert node.startswith("te") is True
	assert xsc.Text("  test  ").strip() == xsc.Text("test")
	assert node.swapcase() == xsc.Text("TEST")
	assert node.title() == xsc.Text("Test")
	assert node.upper() == xsc.Text("TEST")


def test_charref():
	node = chars.ouml()
	hash(node)
	assert len(node) == 1
	assert node[0] == xsc.Text(u"�")
	assert 3*node == xsc.Text(u"���")
	assert node*3 == xsc.Text(u"���")
	assert node[1:-2] == xsc.Text()
	assert node.capitalize() == xsc.Text(u"�")
	assert node.center(5) == xsc.Text(u"  �  ")
	assert node.count(u"t") == 0
	assert node.endswith(u"�") is True
	assert node.index(u"�") == 0
	assert node.isalpha() is True
	assert node.isalnum() is True
	assert node.isdecimal() is False
	assert node.isdigit() is False
	assert node.islower() is True
	assert node.isnumeric() is False
	assert node.isspace() is False
	assert node.istitle() is False
	assert node.isupper() is False
	assert node.ljust(3) == xsc.Text(u"�  ")
	assert node.ljust(3, ".") == xsc.Text(u"�..")
	assert node.lower() == xsc.Text(u"�")
	assert node.replace(u"�", "x") == xsc.Text("x")
	assert node.rjust(3) == xsc.Text(u"  �")
	assert node.rjust(3, ".") == xsc.Text(u"..�")
	assert node.rfind(u"�") == 0
	assert node.rindex(u"�") == 0
	assert node.startswith(u"�") is True
	assert node.swapcase() == xsc.Text(u"�")
	assert node.title() == xsc.Text(u"�")
	assert node.upper() == xsc.Text(u"�")


def test_getsetitem():
	for cls in (xsc.Frag, html.div):
		for attr in ("class_", (xml, "lang")):
			node = cls(html.div("foo", html.div({attr: "gurk"}), "bar"))
			assert node[[]] is node
			assert str(node[[0, 1, attr]]) == "gurk"
			node[[0, 1, attr]] = "hurz"
			assert str(node[[0, 1, attr]]) == "hurz"
			i = node[0][xsc.Text]
			assert str(i.next()) == "foo"
			assert str(i.next()) == "bar"
			py.test.raises(StopIteration, i.next)
			py.test.raises(ValueError, node.__setitem__, [], None)
			py.test.raises(ValueError, node.__delitem__, [])


def test_conv():
	def mappedmapper(node, converter):
		if isinstance(node, xsc.Text):
			node = node.replace("gurk", "hurz")
		return node

	node = createfrag()
	node.conv()
	node.conv(converters.Converter())
	node.mapped(mappedmapper, converters.Converter())


def test_repr():
	tests = allnodes()
	allpresenters = [c for c in presenters.__dict__.itervalues() if isinstance(c, type) and c is not presenters.Presenter and issubclass(c, presenters.Presenter)]
	for node in tests:
		repr(node)
		for class_ in allpresenters:
			presenter = class_()
			# do it multiple time, to make sure the presenter gets properly reset
			for i in xrange(3):
				node.repr(presenter)
		for showlocation in (False, True):
			for showpath in (False, True):
				presenter = presenters.TreePresenter(showlocation=showlocation, showpath=showpath)
				# do it multiple time, to make sure the presenter gets properly reset
				for i in xrange(3):
					node.repr(presenter)


def test_attrsclone():
	class newa(html.a):
		def convert(self, converter):
			attrs = self.attrs.clone()
			attrs["href"].insert(0, "foo")
			e = html.a(self.content, attrs)
			return e.convert(converter)
	e = newa("gurk", href="hurz")
	e = e.conv().conv()
	assert unicode(e["href"]) == "foohurz"
	assert str(e["href"]) == "foohurz"


def test_attributes():
	node = html.h1("gurk", {(xml, "lang"): "de"}, lang="de")
	assert node.attrs.has("lang")
	assert node.attrs.has((xml, "lang"))
	assert "lang" in node.attrs
	assert (xml, "lang") in node.attrs


def test_attributekeysvaluesitems():
	def check(node, xml, attrname, attrvalue):
		assert node.attrs.allowedkeys(xml=xml) == [attrname]
		iter = node.attrs.iterallowedkeys(xml=xml)
		assert iter.next() == attrname
		py.test.raises(StopIteration, iter.next)

		assert node.attrs.allowedvalues() == [node.Attrs.attr_]
		iter = node.attrs.iterallowedvalues()
		assert iter.next() == node.Attrs.attr_
		py.test.raises(StopIteration, iter.next)

		assert node.attrs.alloweditems(xml=xml) == [(attrname, node.Attrs.attr_)]
		iter = node.attrs.iteralloweditems(xml=xml)
		assert iter.next() == (attrname, node.Attrs.attr_)
		py.test.raises(StopIteration, iter.next)

		if attrvalue:
			assert node.attrs.keys(xml=xml) == [attrname]
			iter = node.attrs.iterkeys(xml=xml)
			assert iter.next() == attrname
			py.test.raises(StopIteration, iter.next)
		else:
			assert node.attrs.keys(xml=xml) == []
			iter = node.attrs.iterkeys(xml=xml)
			py.test.raises(StopIteration, iter.next)

		if attrvalue:
			res = node.attrs.values()
			assert len(res) == 1
			assert res[0].__class__ is node.Attrs.attr_
			assert unicode(res[0]) == attrvalue
			iter = node.attrs.itervalues()
			res = iter.next()
			assert res.__class__ is node.Attrs.attr_
			assert unicode(res) == attrvalue
			py.test.raises(StopIteration, iter.next)
		else:
			res = node.attrs.values()
			assert len(res) == 0
			iter = node.attrs.itervalues()
			py.test.raises(StopIteration, iter.next)

		if attrvalue:
			res = node.attrs.items(xml=xml)
			assert len(res) == 1
			assert res[0][0] == attrname
			assert res[0][1].__class__ is node.Attrs.attr_
			assert unicode(res[0][1]) == attrvalue
			iter = node.attrs.iteritems(xml=xml)
			res = iter.next()
			assert res[0] == attrname
			assert res[1].__class__ is node.Attrs.attr_
			assert unicode(res[1]) == attrvalue
			py.test.raises(StopIteration, iter.next)
		else:
			res = node.attrs.items(xml=xml)
			assert len(res) == 0
			iter = node.attrs.iteritems(xml=xml)
			py.test.raises(StopIteration, iter.next)

	class Test1(xsc.Element):
		class Attrs(xsc.Element.Attrs):
			class attr_(xsc.TextAttr):
				xmlname = "attr"
				default = 42
	class Test2(xsc.Element):
		class Attrs(xsc.Element.Attrs):
			class attr_(xsc.TextAttr):
				xmlname = "attr"

	for (xml, attrname) in ((False, u"attr_"), (True, u"attr")):
		check(Test1(), xml, attrname, u"42")
		check(Test1(attr_=17), xml, attrname, u"17")
		check(Test1(attr_=None), xml, attrname, None)

		check(Test2(), xml, attrname, None)
		check(Test2(attr_=17), xml, attrname, u"17")
		check(Test2(attr_=None), xml, attrname, None)


class XISTTest(unittest.TestCase):
	def test_attributeswithout(self):
		# Use a sub namespace of xml to test the issubclass checks
		class xml2(xml):
			class Attrs(xml.Attrs):
				class lang(xml.Attrs.lang):
					default = 42

		node = html.h1("gurk",
			{(xml2, "space"): 1, (xml2, "lang"): "de", (xml2, "base"): "http://www.livinglogic.de/"},
			lang="de",
			style="color: #fff",
			align="right",
			title="gurk",
			class_="important",
			id=42,
			dir="ltr"
		)
		keys = node.attrs.keys()
		keys.sort()
		keys.remove("class_")

		keys1 = node.attrs.without(["class_"]).keys()
		keys1.sort()
		self.assertEqual(keys, keys1)

		keys.remove((xml2, "space"))
		keys2 = node.attrs.without(["class_", (xml, "space")]).keys()
		keys2.sort()
		self.assertEqual(keys, keys2)

		keys.remove((xml2, "lang"))
		keys.remove((xml2, "base"))
		keys3 = node.attrs.without(["class_"], [xml]).keys()
		keys3.sort()
		self.assertEqual(keys, keys3)

		# Check that non existing attrs are handled correctly
		keys4 = node.attrs.without(["class_", "src"], keepglobals=False).keys()
		keys4.sort()
		self.assertEqual(keys, keys4)

	def test_attributeswith(self):
		# Use a sub namespace of xml to test the issubclass checks
		class xml2(xml):
			class Attrs(xml.Attrs):
				class lang(xml.Attrs.lang):
					default = 42

		node = html.h1("gurk",
			{(xml2, "space"): 1, (xml2, "lang"): "de"},
			lang="de",
			align="right"
		)
		keys = node.attrs.keys()
		keys.sort()
		keys.remove("lang")

		self.assertEquals(node.attrs.with(["lang"]).keys(), ["lang"])

		keys1 = node.attrs.with(["lang", "align"]).keys()
		keys1.sort()
		self.assertEqual(keys1, ["align", "lang"])

		keys = ["lang", (xml2, "lang")]
		keys.sort()
		keys2 = node.attrs.with(keys).keys()
		keys2.sort()
		self.assertEqual(keys2, keys)

		keys = ["lang", (xml2, "lang"), (xml2, "space")]
		keys.sort()
		keys3 = node.attrs.with(["lang"], [xml]).keys()
		keys3.sort()
		self.assertEqual(keys3, keys)

	def test_defaultattributes(self):
		class Test(xsc.Element):
			class Attrs(xsc.Element.Attrs):
				class withdef(xsc.TextAttr):
					default = 42
				class withoutdef(xsc.TextAttr):
					pass
		node = Test()
		self.assert_(node.attrs.has("withdef"))
		self.assert_(not node.attrs.has("withoutdef"))
		self.assertRaises(xsc.IllegalAttrError, node.attrs.has, "illegal")
		node = Test(withdef=None)
		self.assert_(not node.attrs.has("withdef"))

	def check_listiter(self, listexp, *lists):
		for l in lists:
			count = 0
			for item in l:
				self.assert_(item in listexp)
				count += 1
			self.assertEqual(count, len(listexp))

	def test_attributedictmethods(self):
		class Test(xsc.Element):
			class Attrs(xsc.Element.Attrs):
				class withdef(xsc.TextAttr):
					default = 42
				class withoutdef(xsc.TextAttr):
					pass
				class another(xsc.URLAttr):
					pass

		node = Test(withoutdef=42)

		self.check_listiter(
			[ "withdef", "withoutdef" ],
			node.attrs.keys(),
			node.attrs.iterkeys()
		)
		self.check_listiter(
			[ Test.Attrs.withdef(42), Test.Attrs.withoutdef(42)],
			node.attrs.values(),
			node.attrs.itervalues()
		)
		self.check_listiter(
			[ ("withdef", Test.Attrs.withdef(42)), ("withoutdef", Test.Attrs.withoutdef(42)) ],
			node.attrs.items(),
			node.attrs.iteritems()
		)

		self.check_listiter(
			[ "another", "withdef", "withoutdef" ],
			node.attrs.allowedkeys(),
			node.attrs.iterallowedkeys()
		)
		self.check_listiter(
			[ Test.Attrs.another, Test.Attrs.withdef, Test.Attrs.withoutdef ],
			node.attrs.allowedvalues(),
			node.attrs.iterallowedvalues()
		)
		self.check_listiter(
			[ ("another", Test.Attrs.another), ("withdef", Test.Attrs.withdef), ("withoutdef", Test.Attrs.withoutdef) ],
			node.attrs.alloweditems(),
			node.attrs.iteralloweditems()
		)

	def test_fragattrdefault(self):
		class testelem(xsc.Element):
			class Attrs(xsc.Element.Attrs):
				class testattr(xsc.TextAttr):
					default = 42

		node = testelem()
		self.assertEquals(unicode(node["testattr"]), "42")
		self.assertEquals(unicode(node.conv()["testattr"]), "42")

		node["testattr"].clear()
		self.assert_(not node.attrs.has("testattr"))
		self.assert_(not node.conv().attrs.has("testattr"))

		node = testelem(testattr=23)
		self.assertEquals(unicode(node["testattr"]), "23")
		self.assertEquals(unicode(node.conv()["testattr"]), "23")

		del node["testattr"]
		self.assertEquals(unicode(node["testattr"]), "")
		self.assertEquals(unicode(node.conv()["testattr"]), "")

		node["testattr"] = 23
		node["testattr"] = None
		self.assert_("testattr" not in node.attrs)
		self.assert_("testattr" not in node.conv().attrs)

		node = testelem(testattr=None)
		self.assert_("testattr" not in node.attrs)
		self.assert_("testattr" not in node.conv().attrs)

	def test_checkisallowed(self):
		class testelem(xsc.Element):
			class Attrs(xsc.Element.Attrs):
				class testattr(xsc.TextAttr):
					pass

		class testelem2(testelem):
			pass

		class testelem3(testelem2):
			class Attrs(testelem2.Attrs):
				class testattr3(xsc.TextAttr):
					pass

		class testelem4(testelem3):
			class Attrs(testelem3.Attrs):
				testattr = None

		node = testelem()
		self.assertEquals(node.attrs.isallowed("testattr"), True)
		self.assertEquals(node.attrs.isallowed("notestattr"), False)

		node = testelem2()
		self.assertEquals(node.attrs.isallowed("testattr"), True)
		self.assertEquals(node.attrs.isallowed("notestattr"), False)

		node = testelem3()
		self.assertEquals(node.attrs.isallowed("testattr"), True)
		self.assertEquals(node.attrs.isallowed("testattr3"), True)

		node = testelem4()
		self.assertEquals(node.attrs.isallowed("testattr"), False)
		self.assertEquals(node.attrs.isallowed("testattr3"), True)

	def test_withsep(self):
		for class_ in (xsc.Frag, html.div):
			node = class_(1,2,3)
			self.assertEquals(unicode(node.withsep(",")), u"1,2,3")
			node = class_(1)
			self.assertEquals(unicode(node.withsep(",")), u"1")
			node = class_()
			self.assertEquals(unicode(node.withsep(",")), u"")

	def test_allowedattr(self):
		self.assertEquals(html.a.Attrs.allowedattr("href"), html.a.Attrs.href)
		self.assertRaises(xsc.IllegalAttrError, html.a.Attrs.allowedattr, "gurk")
		self.assertEquals(html.a.Attrs.allowedattr((xml, "lang")), xml.Attrs.lang)

	def test_plaintableattrs(self):
		e = htmlspecials.plaintable(border=3)
		self.assert_(isinstance(e["border"], html.table.Attrs.border))
		self.assert_(isinstance(e["cellpadding"], html.table.Attrs.cellpadding))
		e = e.conv()
		self.assert_(isinstance(e["border"], html.table.Attrs.border))
		self.assert_(isinstance(e["cellpadding"], html.table.Attrs.cellpadding))

	def test_attrupdate(self):
		node = html.a(href="gurk", class_="hurz")
		node.attrs.update(xml.Attrs(lang="de"), {"href": "gurk2", "id": 42})
		self.assertEquals(unicode(node["href"]), u"gurk2")
		self.assertEquals(unicode(node["id"]), u"42")
		self.assertEquals(unicode(node[(xml, "lang")]), u"de")

		node = html.a(href="gurk", class_="hurz")
		node.attrs.updatenew(xml.Attrs(lang="de"), {"href": "gurk2", "id": 42})
		self.assertEquals(unicode(node["href"]), u"gurk")
		self.assertEquals(unicode(node["id"]), u"42")
		self.assertEquals(unicode(node[(xml, "lang")]), u"de")

		node = html.a(href="gurk", class_="hurz")
		node.attrs.updateexisting({"href": "gurk2", "id": 42})
		self.assertEquals(unicode(node["href"]), u"gurk2")
		self.assertEquals("id" in node.attrs, False)
		self.assertEquals((xml, "lang") in node.attrs, False)

		node = html.a({(xml, "lang"): "de"}, href="gurk", class_="hurz")
		self.assertEquals(unicode(node[(xml, "lang")]), u"de")

		node = html.a(xml.Attrs(lang="de"), href="gurk", class_="hurz")
		self.assertEquals(unicode(node[(xml, "lang")]), u"de")

		class Gurk(xsc.Element):
			model = False
			class Attrs(xsc.Element.Attrs):
				class gurk(xsc.TextAttr): pass
				class hurz(xsc.TextAttr): default = "hinz+kunz"

		node1 = Gurk()
		node2 = Gurk(hurz=None)
		node1.attrs.update(node2.attrs)
		self.assert_("hurz" not in node1.attrs)

		node1 = Gurk(hurz=None)
		node2 = Gurk()
		node1.attrs.update(node2.attrs)
		self.assert_("hurz" in node1.attrs)

		node = Gurk(Gurk(hurz=None).attrs)
		self.assert_("hurz" not in node.attrs)

		attrs = Gurk.Attrs(Gurk.Attrs(hurz=None))
		self.assert_("hurz" not in attrs)

		# No global attributes inside global attributes
		self.assertRaises(xsc.IllegalAttrError, xml.Attrs, xml.Attrs(lang="de"))

	def test_classrepr(self):
		repr(xsc.Base)
		repr(xsc.Node)
		repr(xsc.Null.__class__)
		repr(xsc.Element)
		repr(xsc.ProcInst)
		repr(xsc.Entity)
		repr(xsc.CharRef)
		repr(xsc.Element.Attrs)
		repr(xml.Attrs)
		repr(xml.Attrs.lang)

	def test_itemslice(self):
		for cls in (xsc.Frag, html.div):
			# __get(item|slice)__
			e = cls(range(6))
			self.assertEqual(e[2], xsc.Text(2))
			self.assertEqual(e[-1], xsc.Text(5))
			self.assertEqual(e[:], e)
			self.assertEqual(e[:2], cls(0, 1))
			self.assertEqual(e[-2:], cls(4, 5))
			self.assertEqual(e[::2], cls(0, 2, 4))
			self.assertEqual(e[1::2], cls(1, 3, 5))
			self.assertEqual(e[::-1], cls(range(5, -1, -1)))
			e[1] = 10
			self.assertEqual(e, cls(0, 10, 2, 3, 4, 5))
			e[1] = None
			self.assertEqual(e, cls(0, 2, 3, 4, 5))
			e[1] = ()
			self.assertEqual(e, cls(0, 3, 4, 5))

			# __set(item|slice)__
			e = cls(range(6))
			e[-1] = None
			self.assertEqual(e, cls(0, 1, 2, 3, 4))

			e = cls(range(6))
			e[1:5] = (100, 200)
			self.assertEqual(e, cls(0, 100, 200, 5))

			e = cls(range(6))
			e[:] = (100, 200)
			self.assertEqual(e, cls(100, 200))

			e = cls(range(6))
			e[::2] = (100, 120, 140)
			self.assertEqual(e, cls(100, 1, 120, 3, 140, 5))

			e = cls(range(6))
			e[1::2] = (110, 130, 150)
			self.assertEqual(e, cls(0, 110, 2, 130, 4, 150))

			e = cls(range(6))
			e[::-1] = range(6)
			self.assertEqual(e, cls(range(5, -1, -1)))

			# __del(item|slice)__
			e = cls(range(6))
			del e[0]
			self.assertEqual(e, cls(1, 2, 3, 4, 5))
			del e[-1]
			self.assertEqual(e, cls(1, 2, 3, 4))

			e = cls(range(6))
			del e[1:5]
			self.assertEqual(e, cls(0, 5))

			e = cls(range(6))
			del e[2:]
			self.assertEqual(e, cls(0, 1))

			e = cls(range(6))
			del e[-2:]
			self.assertEqual(e, cls(0, 1, 2, 3))

			e = cls(range(6))
			del e[:2]
			self.assertEqual(e, cls(2, 3, 4, 5))

			e = cls(range(6))
			del e[:-2]
			self.assertEqual(e, cls(4, 5))

			e = cls(range(6))
			del e[:]
			self.assertEqual(e, cls())

			e = cls(range(6))
			del e[::2]
			self.assertEqual(e, cls(1, 3, 5))

			e = cls(range(6))
			del e[1::2]
			self.assertEqual(e, cls(0, 2, 4))

		e = html.div(range(6), id=42)
		self.assertEqual(e[2], xsc.Text(2))
		self.assertEqual(e[-1], xsc.Text(5))
		self.assertEqual(e[:], e)
		self.assertEqual(e[:2], cls(0, 1, id=42))
		self.assertEqual(e[-2:], cls(4, 5, id=42))
		self.assertEqual(e[::2], cls(0, 2, 4, id=42))
		self.assertEqual(e[1::2], cls(1, 3, 5, id=42))
		self.assertEqual(e[::-1], cls(range(5, -1, -1), id=42))

	def test_clone(self):
		for cls in (xsc.Frag, html.div):
			e = html.div(1)

			src = cls(1, e, e)

			dst = src.clone()
			self.assert_(src is not dst)
			self.assert_(src[0] is dst[0])
			self.assert_(src[1] is not dst[1])
			self.assert_(dst[1] is not dst[2])

			e.append(e) # create a cycle

			dst = src.copy()
			self.assert_(src is not dst)
			self.assert_(src[0] is dst[0])
			self.assert_(src[1] is dst[1])
			self.assert_(dst[1] is dst[2])

			dst = src.deepcopy()
			self.assert_(src is not dst)
			self.assert_(src[0] is dst[0])
			self.assert_(src[1] is not dst[1])
			self.assert_(dst[1] is dst[2])

		e = html.div(id=(17, html.div(23), 42))
		for src in (e, e.attrs):
			dst = src.clone()
			self.assert_(src["id"] is not dst["id"])
			self.assert_(src["id"][0] is dst["id"][0])
			self.assert_(src["id"][1] is not dst["id"][1])

		e["id"][1] = e # create a cycle
		e["id"][2] = e # create a cycle
		for src in (e, e.attrs):
			dst = src.copy()
			self.assert_(src["id"] is dst["id"])
			self.assert_(src["id"][0] is dst["id"][0])
			self.assert_(src["id"][1] is dst["id"][1])
			self.assert_(dst["id"][1] is dst["id"][2])
			dst = src.deepcopy()
			self.assert_(src["id"] is not dst["id"])
			self.assert_(src["id"][0] is dst["id"][0])
			self.assert_(src["id"][1] is not dst["id"][1])
			self.assert_(dst["id"][1] is dst["id"][2])

	def check_sortreverse(self, method):
		for class_ in (xsc.Frag, html.div):
			node = class_(3, 2, 1)
			node2 = getattr(node, method)()
			self.assertEqual(node, class_(3, 2, 1))
			self.assertEqual(node2, class_(1, 2, 3))

	def test_sorted(self):
		self.check_sortreverse("sorted")

	def test_reversed(self):
		self.check_sortreverse("reversed")




class CSSParseTest(unittest.TestCase):
	def test_parse(self):
		csshandler = cssparsers.ParseHandler()
		s = "div {border: 0px;}"
		self.assertEqual(csshandler.parseString(s), s)
		s = "div {background-image: url(gurk.gif);}"
		self.assertEqual(csshandler.parseString(s), s)
		s = "div {background-image: url(gurk.gif);}"
		self.assertEqual(
			csshandler.parseString(s, base="root:hurz/index.css"),
			"div {background-image: url(root:hurz/gurk.gif);}"
		)

	def test_publish(self):
		csshandler = cssparsers.PublishHandler()
		s = "div {border: 0px;}"
		self.assertEqual(csshandler.parseString(s), s)
		s = "div {background-image: url(gurk.gif);}"
		self.assertEqual(csshandler.parseString(s), s)
		s = "div {background-image: url(root:hurz/gurk.gif);}"
		self.assertEqual(
			csshandler.parseString(s, base="root:hurz/index.css"),
			"div {background-image: url(gurk.gif);}"
		)

	def test_collect(self):
		csshandler = cssparsers.CollectHandler()
		s = """
			div.c1 {background-image: url(root:hurz/hinz.gif);}
			div.c1 {background-image: url(root:hurz/kunz.gif);}
		"""
		csshandler.parseString(s)
		self.assertEqual(len(csshandler.urls), 2)
		self.assertEqual(csshandler.urls[0], url.URL("root:hurz/hinz.gif"))
		self.assertEqual(csshandler.urls[1], url.URL("root:hurz/kunz.gif"))


class DTD2XSCTest(unittest.TestCase):
	def dtd2ns(self, s, xmlname, xmlurl=None, shareattrs=None):
		from xml.parsers.xmlproc import dtdparser

		dtd = dtdparser.load_dtd_string(s)
		data = xnd.fromdtd(dtd, xmlname=xmlname, xmlurl=xmlurl)

		if shareattrs is not None:
			data.shareattrs(shareattrs)

		mod = {"__name__": xmlname}
		encoding = "iso-8859-1"
		code = data.aspy(encoding=encoding, asmod=False).encode(encoding)
		exec code in mod

		return mod["__ns__"]

	def test_convert(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo (bar+)>
		<!ATTLIST foo
			id    ID    #IMPLIED
			xmlns CDATA #FIXED "http://xmlns.foo.com/foo"
		>
		<!ELEMENT bar EMPTY>
		<!ATTLIST bar
			bar1 CDATA               #REQUIRED
			bar2 (bar2)              #IMPLIED
			bar3 (bar3a|bar3b|bar3c) #IMPLIED
			bar-4 (bar-4a|bar-4b)    #IMPLIED
			bar_4 (bar_4a|bar_4b)    #IMPLIED
			bar_42 (bar_42a|bar_42b) #IMPLIED
			class CDATA              #IMPLIED
			foo:bar CDATA            #IMPLIED
		>
		"""
		ns = self.dtd2ns(dtdstring, "foo")

		self.assert_(issubclass(ns, xsc.Namespace))
		self.assertEqual(ns.xmlname, "foo")
		self.assertEqual(ns.xmlurl, "http://xmlns.foo.com/foo")
		self.assert_(isinstance(ns.foo.model, sims.Elements))
		self.assertEqual(len(ns.foo.model.elements), 1)
		self.assertEqual(ns.foo.model.elements[0], ns.bar)
		self.assert_(issubclass(ns.foo.Attrs.id, xsc.IDAttr))
		self.assert_("xmlns" not in ns.foo.Attrs)
		self.assert_(isinstance(ns.bar.model, sims.Empty))

		self.assert_("bar" not in ns.bar.Attrs)

		self.assert_(issubclass(ns.bar.Attrs.bar1, xsc.TextAttr))
		self.assertEqual(ns.bar.Attrs.bar1.required, True)

		self.assert_(issubclass(ns.bar.Attrs.bar2, xsc.BoolAttr))
		self.assertEqual(ns.bar.Attrs.bar2.required, False)

		self.assert_(issubclass(ns.bar.Attrs.bar3, xsc.TextAttr))
		self.assertEqual(ns.bar.Attrs.bar3.required, False)
		self.assertEqual(ns.bar.Attrs.bar3.values, ("bar3a", "bar3b", "bar3c"))

		# Attributes are alphabetically sorted
		self.assert_(issubclass(ns.bar.Attrs.bar_4, xsc.TextAttr))
		self.assertEqual(ns.bar.Attrs.bar_4.xmlname, "bar-4")
		self.assertEqual(ns.bar.Attrs.bar_4.values, ("bar-4a", "bar-4b"))

		self.assert_(issubclass(ns.bar.Attrs.bar_42, xsc.TextAttr))
		self.assertEqual(ns.bar.Attrs.bar_42.xmlname, "bar_4")
		self.assertEqual(ns.bar.Attrs.bar_42.values, ("bar_4a", "bar_4b"))

		self.assert_(issubclass(ns.bar.Attrs.bar_422, xsc.TextAttr))
		self.assertEqual(ns.bar.Attrs.bar_422.xmlname, "bar_42")
		self.assertEqual(ns.bar.Attrs.bar_422.values, ("bar_42a", "bar_42b"))

	def test_charref(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo (EMPTY)>
		<!ENTITY bar "&#xff;">
		"""
		ns = self.dtd2ns(dtdstring, "foo")

		self.assertEqual(ns.bar.codepoint, 0xff)

	def test_keyword(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo EMPTY>
		<!ATTLIST foo
			class CDATA              #IMPLIED
		>
		"""
		ns = self.dtd2ns(dtdstring, "foo")
		self.assert_(issubclass(ns.foo.Attrs.class_, xsc.TextAttr))
		self.assertEqual(ns.foo.Attrs.class_.__name__, "class_")
		self.assertEqual(ns.foo.Attrs.class_.xmlname, u"class")

	def test_quotes(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo EMPTY>
		"""
		ns = self.dtd2ns(dtdstring, "foo", xmlurl='"')
		self.assertEqual(ns.xmlurl, '"')

	def test_unicode(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo EMPTY>
		"""
		ns = self.dtd2ns(dtdstring, "foo", xmlurl=u'\u3042')
		self.assertEqual(ns.xmlurl, u'\u3042')

	def test_unicodequotes(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo EMPTY>
		"""
		ns = self.dtd2ns(dtdstring, "foo", xmlurl=u'"\u3042"')
		self.assertEqual(ns.xmlurl, u'"\u3042"')

	def test_badelementname(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT class EMPTY>
		"""
		ns = self.dtd2ns(dtdstring, "foo")
		self.assert_(issubclass(ns.class_, xsc.Element))

	def test_shareattrsnone(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo (bar)>
		<!ATTLIST foo
			baz CDATA              #IMPLIED
		>
		<!ELEMENT bar EMPTY>
		<!ATTLIST bar
			baz CDATA              #IMPLIED
		>
		"""
		ns = self.dtd2ns(dtdstring, "foo", shareattrs=None)
		self.assert_(not hasattr(ns, "baz"))

	def test_shareattrsdupes(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo (bar)>
		<!ATTLIST foo
			baz  CDATA             #IMPLIED
			baz2 CDATA             #IMPLIED
		>
		<!ELEMENT bar EMPTY>
		<!ATTLIST bar
			baz  CDATA             #IMPLIED
			baz2 CDATA             #REQUIRED
		>
		"""
		ns = self.dtd2ns(dtdstring, "foo", shareattrs=False)
		self.assert_(issubclass(ns.foo.Attrs.baz, ns.baz.baz))
		self.assert_(issubclass(ns.bar.Attrs.baz, ns.baz.baz))
		self.assert_(not hasattr(ns, "baz2"))
		self.assert_(not ns.foo.Attrs.baz2.required)
		self.assert_(ns.bar.Attrs.baz2.required)

	def test_shareattrsall(self):
		dtdstring = """<?xml version='1.0' encoding='us-ascii'?>
		<!ELEMENT foo (bar)>
		<!ATTLIST foo
			baz  CDATA             #IMPLIED
			bazz CDATA             #IMPLIED
		>
		<!ELEMENT bar EMPTY>
		<!ATTLIST bar
			baz  CDATA             #IMPLIED
			bazz CDATA             #REQUIRED
		>
		"""
		ns = self.dtd2ns(dtdstring, "foo", shareattrs=True)
		self.assert_(issubclass(ns.foo.Attrs.baz, ns.baz.baz))
		self.assert_(issubclass(ns.bar.Attrs.baz, ns.baz.baz))

		self.assertNotEqual(ns.foo.Attrs.bazz.__bases__[0], xsc.TextAttr)
		self.assertNotEqual(ns.bar.Attrs.bazz.__bases__[0], xsc.TextAttr)
		self.assertNotEqual(ns.foo.Attrs.bazz.__bases__, ns.bar.Attrs.bazz.__bases__)

		self.assert_(not ns.foo.Attrs.bazz.required)
		self.assert_(ns.bar.Attrs.bazz.required)


def test_walk_1():
	node = createfrag()
	def filter(*args):
		return (True, xsc.enterattrs, xsc.entercontent, True)

	def check(inmode, outmode):
		# call only for code coverage
		list(node.walk((True, xsc.entercontent, True), inmode=inmode, outmode=outmode))
		list(node.walk(filter, inmode=inmode, outmode=outmode))

	modes = (xsc.walknode, xsc.walkpath, xsc.walkindex, xsc.walkrootindex)
	for inmode in modes:
		for outmode in modes:
			yield check, inmode, outmode


def test_walk_2():
	def check(node, filter, result, inmode=xsc.walknode, outmode=xsc.walknode):
		def node2str(node):
			if isinstance(node, xsc.Node):
				if isinstance(node, xsc.Text):
					return "#"
				else:
					return node.xmlname
			else:
				return ".".join(map(node2str, node))
	
		assert map(node2str, node.walk(filter, inmode=inmode, outmode=outmode)) == result

	node = html.div(
		html.tr(
			html.th("gurk"),
			html.td("hurz"),
			id=html.b(42)
		),
		class_=html.i("hinz")
	)

	def filtertopdown(node):
		return (isinstance(node, xsc.Element), xsc.entercontent)
	def filterbottomup(node):
		return (xsc.entercontent, isinstance(node, xsc.Element))
	def filtertopdownattrs(node):
		return (isinstance(node, xsc.Element), xsc.enterattrs, xsc.entercontent)
	def filterbottomupattrs(node):
		return (xsc.enterattrs, xsc.entercontent, isinstance(node, xsc.Element))
	def filtertopdowntextonlyinattr(path):
		for node in path:
			if isinstance(node, xsc.Attr):
				inattr = True
				break
		else:
			inattr = False
		node = path[-1]
		if isinstance(node, xsc.Element):
			return (True, xsc.enterattrs, xsc.entercontent)
		if inattr and isinstance(node, xsc.Text):
			return (True, )
		else:
			return (xsc.entercontent, )

	def filtertopdownattrwithoutcontent(node):
		if isinstance(node, xsc.Element):
			return (True, xsc.entercontent, xsc.enterattrs)
		elif isinstance(node, (xsc.Attr, xsc.Text)):
			return (True, )
		else:
			return (xsc.entercontent, )

	yield check, node, filtertopdown, ["div", "tr", "th", "td"]
	yield check, node, filterbottomup, ["th", "td", "tr", "div"]
	yield check, node, filtertopdownattrs, ["div", "i", "tr", "b", "th", "td"]
	yield check, node, filtertopdownattrs, ["div", "div.class.i", "div.tr", "div.tr.id.b", "div.tr.th", "div.tr.td"], xsc.walknode, xsc.walkpath
	yield check, node, filterbottomupattrs, ["div.class.i", "div.tr.id.b", "div.tr.th", "div.tr.td", "div.tr", "div"], xsc.walknode, xsc.walkpath
	yield check, node, filtertopdowntextonlyinattr, ["div", "div.class.i", "div.class.i.#", "div.tr", "div.tr.id.b", "div.tr.id.b.#", "div.tr.th", "div.tr.td"], xsc.walkpath, xsc.walkpath
	yield check, node, filtertopdownattrwithoutcontent, ["div", "div.tr", "div.tr.th", "div.tr.th.#", "div.tr.td", "div.tr.td.#", "div.tr.id", "div.class"], xsc.walknode, xsc.walkpath


def test_walk_walkindex():
	e = html.div(
		"foo",
		html.a(
			"bar",
			xml.Attrs(lang="en"),
			href="baz",
		),
		"gurk",
	)
	res = list(e.walk(xsc.FindTypeAllAttrs(xsc.Text), outmode=xsc.walkindex))
	exp = [
		[0],
		[1, 0],
		[1, "href", 0],
		[1, (xml, "lang"), 0], # FIXME: This depends on dictionary iteration order
		[2]
	]
	assert res == exp


def test_walk_walkindexisnode():
	# Check that all walk modes return the same data
	def check(node):
		l1 = list(node.walk(xsc.FindTypeAllAttrs(xsc.Text), outmode=xsc.walknode))
		l2 = list(node.walk(xsc.FindTypeAllAttrs(xsc.Text), outmode=xsc.walkpath))
		l3 = list(node.walk(xsc.FindTypeAllAttrs(xsc.Text), outmode=xsc.walkindex))
		l4 = list(node.walk(xsc.FindTypeAllAttrs(xsc.Text), outmode=xsc.walkrootindex))
		assert len(l1) == len(l2) == len(l3) == len(l4)
		for (subnode, path, index, (root, rindex)) in zip(l1, l2, l3, l4):
			assert subnode is path[-1]
			assert subnode is node[index]
			assert subnode is root[rindex]

	for node in allnodes():
		yield check, node
