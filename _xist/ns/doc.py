import types, inspect

from xist import xsc, parsers
from xist.ns import html, docbook

class programlisting(xsc.Element):
	"""
	A literal listing of all or part of a program
	"""
	empty = 0

	def convert(self, converter):
		e = html.pre(class_="programlisting")
		for child in self.content:
			child = child.convert(converter)
			if isinstance(child, xsc.Text):
				for c in child:
					if c=="\t":
						if converter.target=="text":
							c = "   "
						else:
							c = html.span(u"���", class_="tab")
					e.append(c)
			else:
				e.append(child)
		if converter.target=="text":
			e = html.blockquote(e)
		return e.convert(converter)

class example(xsc.Element):
	"""
	A formal example, with a title
	"""
	empty = 0
	attrHandlers = {"title": xsc.TextAttr}

	def convert(self, converter):
		e = xsc.Frag(self.content)
		if converter.target!="text" and self.hasAttr("title"):
			e.append(html.div(self["title"], class_="example-title"))
		return e.convert(converter)

class option(xsc.Element):
	"""
	An option for a software command
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="option")
		return e.convert(converter)

class literal(xsc.Element):
	"""
	Inline text that is some literal value
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="literal")
		return e.convert(converter)

class function(xsc.Element):
	"""
	The name of a function or subroutine, as in a programming language
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="function")
		return e.convert(converter)

class classname(xsc.Element):
	"""
	The name of a class, in the object-oriented programming sense
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="classname")
		return e.convert(converter)

class replaceable(xsc.Element):
	"""
	Content that may or must be replaced by the user
	"""
	empty = 0

	def convert(self, converter):
		e = html.var(self.content, class_="replaceable")
		return e.convert(converter)

class markup(xsc.Element):
	"""
	A string of formatting markup in text that is to be represented literally
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="markup")
		return e.convert(converter)

class parameter(xsc.Element):
	"""
	A value or a symbolic reference to a value
	"""
	empty = 0

	def convert(self, converter):
		e = html.code(self.content, class_="parameter")
		return e.convert(converter)

class filename(xsc.Element):
	"""
	The name of a file
	"""
	empty = 0
	attrHandlers = {"class": xsc.TextAttr}

	def convert(self, converter):
		e = html.code(self.content, class_="filename")
		return e.convert(converter)

class app(xsc.Element):
	"""
	The name of a software program
	"""
	empty = 0
	attrHandlers = {"moreinfo": xsc.URLAttr}

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.application(self.content, moreinfo=self["moreinfo"])
		else:
			e = html.span(self.content, class_="app")
			if self.hasAttr("moreinfo"):
				e = html.a(e, href=self["moreinfo"])
		return e.convert(converter)

class para(xsc.Element):
	"""
	A paragraph
	"""
	empty = 0

	def convert(self, converter):
		e = html.p(self.content)
		return e.convert(converter)

class title(xsc.Element):
	"""
	The text of the title of a section of a document or of a formal block-level element
	"""
	empty = 0

	def convert(self, converter):
		if converter.target=="docbook":
			return docbook.title(self.content.convert(converter))
		else:
			return self.content.convert(converter)

class section(xsc.Element):
	"""
	A recursive section
	"""
	empty = 0
	attrHandlers = {"role": xsc.TextAttr}

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.section(self.content.convert(converter), role=self["role"])
			return e
		else:
			context = converter[self.__class__]
			if not hasattr(context, "depth"):
				context.depth = 1
			ts = xsc.Frag()
			cs = xsc.Frag()
			for child in self:
				if isinstance(child, title):
					ts.append(child)
				else:
					cs.append(child)
			e = xsc.Frag()
			for t in ts:
				h = html.namespace.elementsByName["h%d" % context.depth](class_=self["role"])
				if converter.target=="text":
					h.append(html.br(), t.content, html.br(), "="*len(t.content.convert(converter).asPlainString()))
				else:
					h.append(t.content)
				e.append(h)
			if self.hasAttr("role"):
				e.append(html.div(cs, class_=self["role"]))
			else:
				e.append(cs)
			context.depth += 1
			e = e.convert(converter)
			context.depth -= 1
			return e

class par(xsc.Element):
	"""
	"""
	empty = 0

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.para(self.content)
		else:
			e = html.p(self.content)
		return e.convert(converter)

class ulist(xsc.Element):
	"""
	A list in which each entry is marked with a bullet or other dingbat
	"""
	empty = 0

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.itemizedlist(self.content)
		else:
			e = html.ul(self.content)
		return e.convert(converter)

class olist(xsc.Element):
	"""
	A list in which each entry is marked with a sequentially incremented label
	"""
	empty = 0

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.orderedlist(self.content)
		else:
			e = html.ol(self.content)
		return e.convert(converter)

class item(xsc.Element):
	"""
	A wrapper for the elements of a list item
	"""
	empty = 0

	def convert(self, converter):
		if converter.target=="docbook":
			e = docbook.listitem(self.content)
		else:
			e = html.li(self.content)
		return e.convert(converter)

class self(xsc.Element):
	"""
	use this class when referring to the object for which a method has been
	called, e.g.:
	<doc:example>
	<doc:programlisting>
		this function fooifies the object &lt;self/&gt;.
	</doc:programlisting>
	</doc:example>
	"""
	empty = 0

	def convert(self, converter):
		return html.code("self", class_="self")

class pyref(xsc.Element):
	"""
	reference to a Python object:
	module, class, method, function, variable or argument
	"""
	empty = 0
	attrHandlers = {"module": xsc.TextAttr, "class": xsc.TextAttr, "method": xsc.TextAttr, "function": xsc.TextAttr, "var": xsc.TextAttr, "arg": xsc.TextAttr, "nolink": xsc.BoolAttr}

	base = "http://localhost:7464/"

	def convert(self, converter):
		if self.hasAttr("var"):
			var = self["var"].convert(converter).asPlainString()
		else:
			var = None
		if self.hasAttr("arg"):
			arg = self["arg"].convert(converter).asPlainString()
		else:
			arg = None
		if self.hasAttr("function"):
			function = self["function"].convert(converter).asPlainString()
		else:
			function = None
		if self.hasAttr("method"):
			method = self["method"].convert(converter).asPlainString()
		else:
			method = None
		if self.hasAttr("class"):
			class_ = self["class"].convert(converter).asPlainString()
		else:
			class_ = None
		if self.hasAttr("module"):
			module = self["module"].convert(converter).asPlainString().replace(u".", u"/")
		else:
			module = None

		e = self.content
		if converter is not None and converter.target=="docbook":
			if var is not None:
				e = e # FIXME
			elif arg is not None:
				e = docbook.parameter(e)
			elif function is not None:
				e = docbook.function(e)
			elif method is not None:
				e = docbook.function(e, role="method")
			elif class_ is not None:
				e = docbook.classname(e)
			elif module is not None:
				e = e # FIXME
		else:
			nolink = self.hasAttr("nolink")
			if var is not None:
				e = html.code(e, class_="pyvar")
			elif arg is not None:
				e = html.code(e, class_="pyarg")
			elif function is not None:
				e = html.code(e, class_="pyfunction")
				if not nolink and module is not None:
					e = html.a(e, href=(self.base, module, "/index.html#", function))
			elif method is not None:
				e = html.code(e, class_="pymethod")
				if not nolink and class_ is not None and module is not None:
					e = html.a(e, href=(self.base, module, "/index.html#", class_, "-", method))
			elif class_ is not None:
				e = html.code(e, class_="pyclass")
				if not nolink and module is not None:
					e = html.a(e, href=(self.base, module, "/index.html#", class_))
			elif module is not None:
				e = html.code(e, class_="pymodule")
				if not nolink:
					e = html.a(e, href=(self.base, module, "/index.html"))
			else:
				e = html.code(e)
		return e.convert(converter)

def getDoc(thing):
	if thing.__doc__ is None:
		return xsc.Null
	lines = thing.__doc__.split("\n")

	# find first nonempty line
	for i in xrange(len(lines)):
		if lines[i] and not lines[i].isspace():
			if i:
				del lines[:i]
			break

	if len(lines):
		# find starting white space of this line
		startwhite = ""
		for c in lines[0]:
			if c.isspace():
				startwhite += c
			else:
				break

		# remove this whitespace from every line
		for i in xrange(len(lines)):
			if lines[i][:len(startwhite)] == startwhite:
				lines[i] = lines[i][len(startwhite):]

		# remove empty lines
		while len(lines) and lines[0] == "":
			del lines[0]
		while len(lines) and lines[-1] == "":
			del lines[-1]

	doc = "\n".join(lines)

	try:
		node = parsers.parseString(doc)
	except SystemExit, KeyboardInterrupt:
		raise
	except:
		node = html.pre(doc, style="color: red")
	if not node.find(type=par): # optimization: one paragraph docstrings don't need a <doc:par> element.
		node = par(node)

	refs = node.find(type=pyref, subtype=1, searchchildren=1)
	if type(thing) is types.MethodType:
		for ref in refs:
			if not ref.hasAttr("module"):
				ref["module"] = inspect.getmodule(thing).__name__
				if not ref.hasAttr("class"):
					ref["class"] = thing.im_class.__name__
					if not ref.hasAttr("method"):
						ref["class"] = thing.__name__
	elif type(thing) is types.FunctionType:
		for ref in refs:
			if not ref.hasAttr("module"):
				ref["module"] = inspect.getmodule(thing).__name__
	elif type(thing) is types.ClassType:
		for ref in refs:
			if not ref.hasAttr("module"):
				ref["module"] = inspect.getmodule(thing).__name__
				if not ref.hasAttr("class"):
					ref["class"] = thing.__name__
	elif type(thing) is types.ModuleType:
		for ref in refs:
			if not ref.hasAttr("module"):
				ref["module"] = thing.__name__
	return node

def cmpName((obj1, name1), (obj2, name2)):
	name1 = name1 or obj1.__name__
	name2 = name2 or obj2.__name__
	return cmp(name1, name2)

def explain(thing, name=None):
	"""
	returns a &xml; representation of the documentation of
	<pyref function="explain" arg="thing">thing</pyref>, which can be a function, method, class or module.
	"""

	t = type(thing)
	if t is types.MethodType:
		(args, varargs, varkw, defaults) = inspect.getargspec(thing.im_func)
		sig = xsc.Frag()
		if name != thing.__name__:
			sig.append(name, " = ")
		sig.append(
			"def ",
			pyref(thing.__name__, module=inspect.getmodule(thing).__name__, class_=thing.im_class.__name__, method=thing.__name__, nolink=1),
			"("
		)
		offset = len(args)
		if defaults is not None:
			offset -= len(defaults)
		for i in xrange(len(args)):
			if i == 0:
				sig.append(self())
			else:
				sig.append(", ")
				name = args[i]
				sig.append(pyref(name, arg=name, nolink=1))
			if i >= offset:
				sig.append("=", repr(defaults[i-offset]))
		if varargs:
			sig.append(", *", pyref(varargs, arg=varargs, nolink=1))
		if varkw:
			sig.append(", **", pyref(varkw, arg=varkw, nolink=1))
		sig.append("):")
		return section(title(sig), getDoc(thing), role="method")
	elif t is types.FunctionType:
		(args, varargs, varkw, defaults) = inspect.getargspec(thing)
		return section(
			title("def ", pyref(name or thing.__name__, module=inspect.getmodule(thing).__name__, function=thing.__name__, nolink=1), "(", xsc.Frag(args).withSep(", "), "):"),
			getDoc(thing),
			role="function"
		)
	elif t is types.ClassType:
		bases = xsc.Frag()
		if len(thing.__bases__):
			for baseclass in thing.__bases__:
				ref = pyref(baseclass.__name__, module=baseclass.__module__, class_=baseclass.__name__)
				if thing.__module__ != baseclass.__module__:
					ref.insert(0, baseclass.__module__, ".")
				bases.append(ref)
			bases = bases.withSep(", ")
			bases.insert(0, "(")
			bases.append(")")
		node = section(
			title("class ", pyref(name or thing.__name__, module=thing.__module__, class_=thing.__name__, nolink=1), bases, ":"),
			getDoc(thing),
			role="class"
		)
		methods = []
		for varname in thing.__dict__.keys():
			obj = getattr(thing, varname)
			if type(obj) is types.MethodType:
				methods.append((obj, varname))
		if len(methods):
			methods.sort(cmpName)
			node.append([explain(*m) for m in methods])
		return node
	elif t is types.ModuleType:
		if hasattr(thing, "__all__"):
			moduletype = "Package"
		else:
			moduletype = "Module"
		node = section(
			title(moduletype, " ", pyref(name or thing.__name__, module=thing.__name__, nolink=1)),
			getDoc(thing)
		)

		functions = []
		classes = []
		for (name, obj) in thing.__dict__.items():
			if inspect.isfunction(obj):
				functions.append((obj, name))
			elif inspect.isclass(obj):
				classes.append((obj, name))
		if len(classes):
			classes.sort(cmpName)
			node.append(
				section(
					title("Classes"),
					[explain(*c) for c in classes],
					role="classes"
				)
			)
		if len(functions):
			functions.sort(cmpName)
			node.append(
				section(
					title("Functions"),
					[explain(*f) for f in functions],
					role="functions"
				)
			)
		return node

	return xsc.Null

namespace = xsc.Namespace("doc", "http://www.livinglogic.de/DTDs/Doc.dtd", vars())
