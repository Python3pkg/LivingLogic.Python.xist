#! /usr/bin/env python
# -*- coding: Latin-1 -*-

## Copyright 1999-2002 by LivingLogic AG, Bayreuth, Germany.
## Copyright 1999-2002 by Walter D�rwald
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
<doc:par>A XSC module that contains a collection of useful elements.</doc:par>
"""

__version__ = tuple(map(int, "$Revision$"[11:-2].split(".")))
# $Source$

import sys, types, time as time_, string

from ll.xist import xsc, parsers
import ihtml, html, meta

class plaintable(html.table):
	"""
	<doc:par>a &html; table where the values of the attributes <lit>cellpadding</lit>,
	<lit>cellspacing</lit> and <lit>border</lit> default to <lit>0</lit>.</doc:par>
	"""
	empty = False
	class Attrs(html.table.Attrs):
		class cellpadding(html.table.Attrs.cellpadding):
			default = 0
		class cellspacing(html.table.Attrs.cellspacing):
			default = 0
		class border(html.table.Attrs.border):
			default = 0

	def convert(self, converter):
		e = html.table(self.content, self.attrs)
		return e.convert(converter)

class plainbody(html.body):
	"""
	<doc:par>a &html; body where the attributes <lit>leftmargin</lit>, <lit>topmargin</lit>,
	<lit>marginheight</lit> and <lit>marginwidth</lit> default to <lit>0</lit>.</doc:par>
	"""
	empty = False
	class Attrs(html.body.Attrs):
		class leftmargin(html.body.Attrs.leftmargin):
			default = 0
		class topmargin(html.body.Attrs.topmargin):
			default = 0
		class marginheight(html.body.Attrs.marginheight):
			default = 0
		class marginwidth(html.body.Attrs.marginwidth):
			default = 0

	def convert(self, converter):
		e = html.body(self.content, self.attrs)
		return e.convert(converter)

class z(xsc.Element):
	"""
	<doc:par>puts it's content into french quotes</doc:par>
	"""
	empty = False

	def convert(self, converter):
		e = xsc.Frag(u"�", self.content.convert(converter), u"�")

		return e

	def __unicode__(self):
		return u"�" + unicode(self.content) + u"�"

class filesize(xsc.Element):
	"""
	<doc:par>the size (in bytes) of the file whose URL is the attribute href
	as a text node.</doc:par>
	"""
	empty = True
	class Attrs(xsc.Element.Attrs):
		class href(xsc.URLAttr): pass

	def convert(self, converter):
		size = self["href"].contentlength(root=converter.root)
		if size is not None:
			return xsc.Text(size)
		else:
			return xsc.Text("?")

class filetime(xsc.Element):
	"""
	<doc:par>the time of the last modification of the file whose URL is in the attibute href
	as a text node.</doc:par>
	"""
	empty = True
	class Attrs(xsc.Element.Attrs):
		class href(xsc.URLAttr): pass
		class format(xsc.TextAttr): pass

	def convert(self, converter):
		return xsc.Text(self["href"].lastmodified)

class time(xsc.Element):
	"""
	<doc:par>the current time (i.e. the time when <pyref method="convert"><method>convert</method></pyref>
	is called). You can specify the format of the string in the attribute format, which is a
	<function>strftime</function> compatible string.</doc:par>
	"""
	empty = True
	class Attrs(xsc.Element.Attrs):
		class format(xsc.TextAttr): pass

	def convert(self, converter):
		if self.hasAttr("format"):
			format = unicode(self["format"].convert(converter))
		else:
			format = "%d. %b. %Y, %H:%M"

		return xsc.Text(time_.strftime(format, time_.gmtime(time_.time())))

class x(xsc.Element):
	"""
	<doc:par>element whose content will be ignored when converted to &html;:
	this can be used to comment out stuff. The content of the element must
	of course still be weelformed and parsable.</doc:par>
	"""
	empty = False

	def convert(self, converter):
		return xsc.Null

class pixel(html.img):
	"""
	<doc:par>element for single pixel images, the default is the image
	<filename>root:Images/Pixels/dot_clear.gif</filename>, but you can specify the color
	as a six digit hex string, which will be used as the filename,
	i.e. <markup>&lt;pixel color="000000"/&gt;</markup> results in
	<markup>&lt;img src="root:Images/Pixels/000000.gif"&gt;</markup>.</doc:par>

	<doc:par>In addition to that you can specify width and height attributes
	(and every other allowed attribute for the img element) as usual.</doc:par>
	"""

	empty = True
	class Attrs(html.img.Attrs):
		class color(xsc.ColorAttr): pass
		src = None

	def convert(self, converter):
		e = html.img()
		color = "0"
		for attr in self.attrs.keys():
			if attr == "color":
				color = self["color"]
			else:
				e[attr] = self[attr]
		if not e.hasAttr("alt"):
			e["alt"] = u""
		if not e.hasAttr("width"):
			e["width"] = 1
		if not e.hasAttr("height"):
			e["height"] = 1
		e["src"] = ("root:images/pixels/", color, ".gif")

		return e.convert(converter)

class caps(xsc.Element):
	"""
	<doc:par>returns a fragment that contains the content string converted to caps and small caps.
	This is done by converting all lowercase letters to uppercase and packing them into a
	<markup>&lt;span class="nini"&gt;...&lt;/span&gt;</markup>. This element is meant to be a workaround until all
	browsers support the CSS feature "font-variant: small-caps".</doc:par>
	"""
	empty = False

	lowercase = unicode(string.lowercase, "latin-1") + u" "

	def convert(self, converter):
		e = unicode(self.content.convert(converter))
		result = xsc.Frag()
		if e: # if we have nothing to do, we skip everything to avoid errors
			collect = ""
			last_was_lower = e[0] in self.lowercase
			for c in e:
				if (c in self.lowercase) != last_was_lower:
					if last_was_lower:
						result.append(html.span(collect.upper(), class_="nini"))
					else:
						result.append(collect)
					last_was_lower = not last_was_lower
					collect = ""
				collect = collect + c
			if collect:
				if last_was_lower:
					result.append(html.span(collect.upper(), class_="nini" ))
				else:
					result.append(collect)
		return result

	def __unicode__(self):
			return unicode(self.content).upper()

class endash(xsc.Element):
	empty = True

	def convert(self, converter):
		return xsc.Text("-")

	def __unicode__(self):
		return u"-"

class emdash(xsc.Element):
	empty = True

	def convert(self, converter):
		return xsc.Text("-")

	def __unicode__(self):
		return u"-"

class include(xsc.Element):
	empty = True
	class Attrs(xsc.Element.Attrs):
		class src(xsc.URLAttr): pass

	def convert(self, converter):
		e = parsers.parseURL(self["src"].forInput())

		return e.convert(converter)

class par(html.div):
	empty = False
	class Attrs(html.div.Attrs):
		class noindent(xsc.BoolAttr): pass

	def convert(self, converter):
		e = html.div(self.content, self.attrs.without(["noindent"]))
		if not self.hasAttr("noindent"):
			e["class_"] = "indent"
		return e.convert(converter)

class autoimg(html.img):
	"""
	<doc:par>An image were width and height attributes are automatically generated.
	If the attributes are already there, they are taken as a
	formatting template with the size passed in as a dictionary with the keys
	<code>width</code> and <code>height</code>, i.e. you could make your image twice
	as wide with <code>width="2*%(width)d"</code>.</doc:par>
	"""
	def convert(self, converter):
		if converter.target=="ihtml":
			e = ihtml.img(self.attrs)
		else:
			e = html.img(self.attrs)
		e._addImageSizeAttributes(converter.root, "src", "width", "height")
		return e.convert(converter)

class autoinput(html.input):
	"""
	<doc:par>Extends <pyref module="ll.xist.ns.html" class="input"><class>input</class></pyref>
	with the ability to automatically set the size, if this element
	has <code>type=="image"</code>.</doc:par>
	"""
	def convert(self, converter):
		if self.hasAttr("type") and self["type"].convert(converter) == u"image":
			e = html.input(self.content, self.attrs)
			e._addImageSizeAttributes(converter.root, "src", "size", None) # no height
			return e.convert(converter)
		else:
			return html.img.convert(self, converter)

class loremipsum(xsc.Element):
	empty = True
	class Attrs(xsc.Element.Attrs):
		class len(xsc.IntAttr): pass

	text = "Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diem nonummy nibh euismod tincidnut ut lacreet dolore magna aliguam erat volutpat. Ut wisis enim ad minim veniam, quis nostrud exerci tution ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis te feugifacilisi. Duis antem dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zril delinit au gue duis dolore te feugat nulla facilisi."

	def convert(self, converter):
		if self.hasAttr("len"):
			text = self.text[:int(self["len"].convert(converter))]
		else:
			text = self.text
		return xsc.Text(text)

class redirectpage(xsc.Element):
	empty = True
	class Attrs(xsc.Element.Attrs):
		class href(xsc.URLAttr): pass

	def convert(self, converter):
		url = self["href"]
		e = html.html(
			html.head(
				meta.contenttype(),
				html.title("Redirection")
			),
			html.body(
				"Your browser doesn't understand redirects. This page has been redirected to ",
				html.a(url, href=url)
			)
		)
		return e.convert(converter)

class wrap(xsc.Element):
	"""
	<doc:par>a wrapper element that returns its content.
	This is e.g. useful if you want to parse a
	file that starts with <pyref module="ll.xist.ns.jsp"><module>&jsp;</module></pyref>
	processing instructions.</doc:par>
	<doc:par>This is also used for publishing, when <lit>xmlns</lit> attributes
	are required, but the root is not an element.</doc:par>
	"""
	empty = False

	def convert(self, converter):
		return self.content.convert(converter)

class javascript(xsc.Element):
	"""
	<doc:par>can be used for javascript.</doc:par>
	"""
	empty = False
	class Attrs(xsc.Element.Attrs):
		class src(xsc.TextAttr): pass

	def convert(self, converter):
		e = html.script(self.content, language="javascript", type="text/javascript", src=self["src"])
		return e.convert(converter)

# Control characters (not part of HTML)
class lf(xsc.CharRef): "line feed"; codepoint = 10
class cr(xsc.CharRef): "carriage return"; codepoint = 13
class tab(xsc.CharRef): "horizontal tab"; codepoint = 9
class esc(xsc.CharRef): "escape"; codepoint = 27

xmlns = xsc.Namespace("specials", "http://xmlns.livinglogic.de/xist/ns/specials", vars())

