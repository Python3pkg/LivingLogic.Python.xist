#! /usr/bin/env python

from xist import xsc,html,specials

url = "http://starship.python.net/crew/amk/quotations/python-quotes.xml"

class quotations(xsc.Element):
	empty = 0

	def asHTML(self, mode=None):
		header = html.head(
			html.title("Python quotes"),
			html.link(rel="stylesheet", href="python-quotes.css")
		)

		description = html.div("(Generated from ", html.a(url, href=url), ")")

		# We want to get rid of the excessive whitespace
		quotations = self.find(type=quotation)

		e = xsc.Frag(
			html.DocTypeHTML401transitional(),
			html.html(
				header,
				html.body(
					html.h1("Python quotes"),
					description,
					quotations
				)
			)
		)

		return e.asHTML(mode)

class quotation(xsc.Element):
	empty = 0

	def asHTML(self, mode=None):
		e = html.div(self.content, class_="quotation")

		return e.asHTML(mode)

class source(xsc.Element):
	empty = 0

	def asHTML(self, mode=None):
		e = html.div(self.content, class_="source")

		return e.asHTML(mode)

class author(xsc.Element):
	empty = 0

	def asHTML(self, mode=None):
		e = self.content

		return e.asHTML(mode)

class foreign(xsc.Element):
	empty = 0

	def asHTML(self, mode=None):
		e = html.em(self.content)

		return e.asHTML(mode)

namespace = xsc.Namespace("pq","http://starship.python.net/crew/amk/quotations/quotations.dtd",vars())

if __name__ == "__main__":
	e = xsc.xsc.parse(url)
	e = e.find(type=quotations)[0]
	e = e.compact().asHTML()
	print e.asString()

