#! /usr/bin/env python

from xist import xsc,html,specials

url =	"http://starship.python.net/crew/amk/quotations/python-quotes.xml"

class quotations(xsc.Element):
	empty = 0

	def asHTML(self):
		header = html.head(
			html.title("Python quotes"),
			html.link(rel="stylesheet",href="python-quotes.css")
		)

		description = html.div("(Generated from ",html.a(url,href=url),")")

		# We want to get rid of the excessive whitespace
		quotations = self.findNodes(type = quotation)

		e = xsc.Frag(
			html.DocTypeHTML40transitional(),
			html.html(
				header,
				html.body(
					html.h1("Python quotes"),
					description,
					quotations
				)
			)
		)

		return e.asHTML()

class quotation(xsc.Element):
	empty = 0

	def asHTML(self):
		e = html.div(self.content,Class="quotation")

		return e.asHTML()

class source(xsc.Element):
	empty = 0

	def asHTML(self):
		e = html.div(self.content,Class="source")

		return e.asHTML()

class author(xsc.Element):
	empty = 0

	def asHTML(self):
		e = self.content

		return e.asHTML()

class foreign(xsc.Element):
	empty = 0

	def asHTML(self):
		e = html.em(self.content)

		return e.asHTML()

xsc.registerAllElements(vars(),"pq")

if __name__ == "__main__":
	e = xsc.xsc.parse(url)
	e = e.findNodes(type = quotations)[0]
	e = e.compact().asHTML()
	print e.asString()

