#! /usr/bin/env python
# -*- coding: utf-8 -*-

from ll.xist import xsc, sims, parsers
from ll.xist.ns import html, htmlspecials, meta, xml, chars


class xmlns(xsc.Namespace):
	xmlname = "media"
	xmlurl = "http://xmlns.livinglogic.de/xist/demo/media"


class name(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()

	def convert(self, converter):
		return self.content.convert(converter)


class rc(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()

	def convert(self, converter):
		return self.content.convert(converter)


class duration(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()

	def convert(self, converter):
		return xsc.Frag(self.content.convert(converter), " min")


class place(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()

	def convert(self, converter):
		return self.content.convert(converter)


class date(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()

	def convert(self, converter):
		return self.content.convert(converter)


class price(xsc.Element):
	xmlns = xmlns
	model = sims.NoElements()
	class Attrs(xsc.Element.Attrs):
		class currency(xsc.TextAttr): pass

	def convert(self, converter):
		return xsc.Frag(self.content, " ", self["currency"]).convert(converter)


class purchase(xsc.Element):
	xmlns = xmlns
	model = sims.Elements(place, date, price)

	def convert(self, converter):
		e = html.div(self[place], class_="purchase")
		for e2 in self[price]:
			e.append(": ", e2)
		e.append(" ")
		for e2 in self[date]:
			e.append("(", e2, ")")
		return e.convert(converter)


class ld(xsc.Element):
	xmlns = xmlns
	model = sims.Elements(name, duration, purchase)

	def convert(self, converter):
		e = html.li(
			html.span(self[name], class_="name")
		)
		for e2 in self[duration]:
			e.append(" (", e2, ")")
		e.append(self[purchase])
		return e.convert(converter)


class dvd(xsc.Element):
	xmlns = xmlns
	model = sims.Elements(name, rc, duration, purchase)

	def convert(self, converter):
		e = html.li(
			html.span(self[name], class_="name")
		)
		durations = xsc.Frag(self[duration])
		rcs = xsc.Frag(self[rc])
		if len(durations) or len(rcs):
			e.append(" (")
			if len(durations):
				e.append(durations[0])
				if len(rcs):
					e.append("; ")
			if len(rcs):
				e.append("RC ", rcs.withsep(", "))
			e.append(")")
		e.append(self[purchase])
		return e.convert(converter)


class media(xsc.Element):
	xmlns = xmlns
	model = sims.Elements(ld, dvd)

	def convert(self, converter):
		def namekey(node):
			return unicode(node[name][0].content)

		dvds = xsc.Frag(self[dvd]).sorted(key=namekey)
		lds = xsc.Frag(self[ld]).sorted(key=namekey)

		e = xsc.Frag(
			xml.XML10(), "\n",
			html.DocTypeXHTML10transitional(), "\n",
			html.html(
				html.head(
					meta.contenttype(),
					html.title("Media"),
					meta.stylesheet(href="Media.css")
				),
				htmlspecials.plainbody(
					html.h1("Media")
				)
			)
		)
		if lds:
			e[-1][-1].append(html.h2(len(lds), " LDs"), html.ol(lds))
		if dvds:
			e[-1][-1].append(html.h2(len(dvds), " DVDs"), html.ol(dvds))
		return e.convert(converter)




if __name__ == "__main__":
	prefixes = xsc.Prefixes([xmlns, chars.xmlns], xml=xml)
	node = parsers.parseFile("Media.xml", prefixes=prefixes)
	node = node[media][0]
	node = node.conv()
	print node.bytes(encoding="us-ascii")
