# -*- coding: utf-8 -*-

## Copyright 2009-2013 by LivingLogic AG, Bayreuth/Germany
## Copyright 2009-2013 by Walter Dörwald
##
## All Rights Reserved
##
## See ll/xist/__init__.py for the license


"""
:mod:`ll.ul4c` provides templating for XML/HTML as well as any other text-based
format. A template defines placeholders for data output and basic logic (like
loops and conditional blocks), that define how the final rendered output will
look.

:mod:`ll.ul4c` compiles a template to an internal format, which makes it
possible to implement template renderers in multiple programming languages.
"""


__docformat__ = "reStructuredText"


import re, types, datetime, urllib.parse as urlparse, json, collections, locale, itertools, random, datetime, unicodedata

import antlr3

from ll import color, misc


# Regular expression used for splitting dates in isoformat
datesplitter = re.compile("[-T:.]")


def register(name):
	from ll import ul4on
	def registration(cls):
		ul4on.register("de.livinglogic.ul4." + name)(cls)
		cls.type = name
		return cls
	return registration


class Object:
	fields = {}

	def __getitem__(self, key):
		if key in self.fields:
			return getattr(self, key)
		raise KeyError(key)


###
### Location information
###

@register("location")
class Location(Object):
	"""
	A :class:`Location` object contains information about the location of a
	template tag.
	"""
	__slots__ = ("source", "type", "starttag", "endtag", "startcode", "endcode")
	fields = {"source", "type", "starttag", "endtag", "startcode", "endcode", "tag", "code"}

	def __init__(self, source=None, type=None, starttag=None, endtag=None, startcode=None, endcode=None):
		"""
		Create a new :class:`Location` object. The arguments have the following
		meaning:

			:var:`source`
				The complete source string

			:var:`type`
				The tag type (i.e. ``"for"``, ``"if"``, etc. or ``None`` for
				literal text)

			:var:`starttag`
				The start position of the start delimiter.

			:var:`endtag`
				The end position of the end delimiter.

			:var:`startcode`
				The start position of the tag code.

			:var:`endcode`
				The end position of the tag code.
		"""
		self.source = source
		self.type = type
		self.starttag = starttag
		self.endtag = endtag
		self.startcode = startcode
		self.endcode = endcode

	@property
	def code(self):
		return self.source[self.startcode:self.endcode]

	@property
	def tag(self):
		return self.source[self.starttag:self.endtag]

	def __repr__(self):
		return "<{}.{} {} at {:#x}>".format(self.__class__.__module__, self.__class__.__name__, self, id(self))

	def pos(self):
		lastlinefeed = self.source.rfind("\n", 0, self.starttag)
		if lastlinefeed >= 0:
			return (self.source.count("\n", 0, self.starttag)+1, self.starttag-lastlinefeed)
		else:
			return (1, self.starttag + 1)

	def __str__(self):
		(line, col) = self.pos()
		return "{!r} at {}:{} (line {}, col {})".format(self.tag, self.starttag, self.endtag, line, col)

	def ul4ondump(self, encoder):
		encoder.dump(self.source)
		encoder.dump(self.type)
		encoder.dump(self.starttag)
		encoder.dump(self.endtag)
		encoder.dump(self.startcode)
		encoder.dump(self.endcode)

	def ul4onload(self, decoder):
		self.source = decoder.load()
		self.type = decoder.load()
		self.starttag = decoder.load()
		self.endtag = decoder.load()
		self.startcode = decoder.load()
		self.endcode = decoder.load()


###
### Exceptions
###

class Error(Exception):
	"""
	Exception class that wraps another exception and provides a location.
	"""
	def __init__(self, location):
		self.location = location

	def __repr__(self):
		return "<{}.{} in {} at {:#x}>".format(self.__class__.__module__, self.__class__.__name__, self.location, id(self))

	def __str__(self):
		return "in {}".format(self.location)


class BlockError(Exception):
	"""
	Exception that is raised by the compiler when an illegal block structure is
	detected (e.g. an ``<?end if?>`` without a previous ``<?if?>``).
	"""

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return self.message


###
### Exceptions used by the interpreted code for flow control
###

class BreakException(Exception):
	pass


class ContinueException(Exception):
	pass


class ReturnException(Exception):
	def __init__(self, value):
		self.value = value


###
### Various versions of undefined objects
###

class Undefined(object):
	def __bool__(self):
		return False

	def __iter__(self):
		raise TypeError("{!r} doesn't support iteration".format(self))

	def __len__(self):
		raise AttributeError("{!r} has no len()".format(self))

	def __getattr__(self, key):
		raise AttributeError("{!r} has no attribute {!r}".format(self, key))

	def __getitem__(self, key):
		raise TypeError("{!r} doesn't support indexing (key={!r})".format(self, key))


class UndefinedKey(Undefined):
	def __init__(self, key):
		self.__key = key

	def __repr__(self):
		return "undefined object for key {!r}".format(self.__key)


class UndefinedVariable(Undefined):
	def __init__(self, name):
		self.__name = name

	def __repr__(self):
		return "undefined variable {!r}".format(self.__name)


class UndefinedIndex(Undefined):
	def __init__(self, index):
		self.__index = index

	def __repr__(self):
		return "undefined object at index {!r}".format(self.__index)


###
### Compiler stuff: Tokens and nodes for the AST
###

class AST(Object):
	"""
	Base class for all syntax tree nodes.
	"""
	# used in :meth:`format` to decide if we need brackets around an operator
	precedence = None
	associative = True

	# Set of attributes available via :meth:`getitem`.
	fields = {"type"}

	# "Global" functions and methods. Functions in ``functions`` will be exposed to UL4 code
	functions = {}
	methods = {}

	def __getitem__(self, key):
		if key in self.fields:
			return getattr(self, key)
		raise KeyError(key)

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		p.text(repr(self))

	def _formatop(self, op):
		bracket = False
		if op.precedence < self.precedence:
			bracket = True
		elif op.precedence == self.precedence and (not isinstance(op, self.__class__) or not self.associative):
			bracket = True
		if bracket:
			yield "("
		yield from op._str(0, True)
		if bracket:
			yield ")"

	@misc.notimplemented
	def _str(self, indent, keepws):
		"""
		Format :var:`self` (with the indentation level :var:`indent`).

		This is used by :meth:`__str__.
		"""

	@misc.notimplemented
	def eval(self, keepws, vars):
		"""
		This evaluates the node.

		This is a generator, which yields the text output of the node. If the
		node returns a value (as most nodes do), this is done as the value of a
		:exc:`StopIteration` exception.
		"""

	@classmethod
	def makefunction(cls, f):
		name = f.__name__
		if name.startswith("_"):
			name = name[1:]
		cls.functions[name] = f
		return f

	@classmethod
	def makemethod(cls, f):
		name = f.__name__
		if name.startswith("_"):
			name = name[1:]
		cls.methods[name] = f
		return f


class Tag(AST):
	"""
	Base class for all syntax tree nodes that are the top level node in a
	template tag.
	"""
	# Set of attributes available via :meth:`getitem`.
	fields = AST.fields.union({"location"})

	def __init__(self, location=None):
		self.location = location

	def ul4ondump(self, encoder):
		encoder.dump(self.location)

	def ul4onload(self, decoder):
		self.location = decoder.load()


@register("text")
class Text(Tag):
	"""
	AST node for literal text.
	"""

	def text(self, keepws):
		# If ``keepws`` is true, we output the literal text from the location info.
		# Otherwise we have to strip linefeeds and indentation
		text = self.location.code
		if not keepws:
			text = "".join(line.lstrip() for line in text.splitlines())
		return text

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.location.code!r} at {1:#x}>".format(self, id(self))

	def _str(self, indent, keepws):
		text = self.text(keepws)
		if text:
			yield indent*"\t"
			yield "text {!r}\n".format(text)

	def eval(self, keepws, vars):
		yield self.text(keepws)


@register("const")
class Const(AST):
	"""
	Load a constant
	"""
	precedence = 11
	fields = AST.fields.union({"value"})

	def __init__(self, value=None):
		self.value = value

	def _str(self, indent, keepws):
		yield _repr(self.value)

	def eval(self, keepws, vars):
		yield from ()
		return self.value

	def ul4ondump(self, encoder):
		encoder.dump(self.value)

	def ul4onload(self, decoder):
		self.value = decoder.load()

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.value!r} at {1:#x}>".format(self, id(self))


@register("list")
class List(AST):
	"""
	AST nodes for loading a list object.
	"""

	precedence = 11
	fields = AST.fields.union({"items"})

	def __init__(self, *items):
		self.items = list(items)

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.items!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				for (i, item) in enumerate(self.items):
					if i:
						p.breakable()
					else:
						p.breakable("")
					p.pretty(item)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield "["
		for (i, item) in enumerate(self.items):
			if i:
				yield ", "
			yield from item._str(indent, keepws)
		yield "]"

	def eval(self, keepws, vars):
		result = []
		for item in self.items:
			item = (yield from item.eval(keepws, vars))
			result.append(item)
		return result

	def ul4ondump(self, encoder):
		encoder.dump(self.items)

	def ul4onload(self, decoder):
		self.items = decoder.load()


@register("listcomp")
class ListComp(AST):
	"""
	AST node for list comprehension.
	"""

	precedence = 11
	fields = AST.fields.union({"item", "varname", "container", "condition"})


	def __init__(self, item=None, varname=None, container=None, condition=None):
		super().__init__()
		self.item = item
		self.varname = varname
		self.container = container
		self.condition = condition

	def __repr__(self):
		s = "<{0.__class__.__module__}.{0.__class__.__qualname__} item={0.item!r} varname={0.varname!r} container={0.container!r}".format(self)
		if self.condition is not None:
			s += " condition={0.condition!r}".format(self)
		return s + " at {:#x}>".format(id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("{0.__class__.__module__}.{0.__class__.__qualname__}(...)".format(self))
		else:
			with p.group(4, "{0.__class__.__module__}.{0.__class__.__qualname__}(".format(self), ")"):
				p.breakable("")
				p.text("item=")
				p.pretty(self.item)
				p.text(",")
				p.breakable()
				p.text("varname=")
				p.pretty(self.varname)
				p.text(",")
				p.breakable()
				p.text("container=")
				p.pretty(self.container)
				if self.condition is not None:
					p.text(",")
					p.breakable()
					p.text("condition=")
					p.pretty(self.condition)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield "["
		yield from self.item._str(indent, keepws)
		yield " for "
		yield _formatnestednameul4(self.varname)
		yield " in "
		yield from self.container._str(indent, keepws)
		if self.condition is not None:
			yield " if "
			yield from self.condition._str(indent, keepws)
		yield "]"

	def eval(self, keepws, vars):
		container = (yield from self.container.eval(keepws, vars))
		vars = collections.ChainMap({}, vars) # Don't let loop variables leak into the surrounding scope
		result = []
		for item in container:
			_unpackvar(vars, self.varname, item)
			if self.condition is None or (yield from self.condition.eval(keepws, vars)):
				item = (yield from self.item.eval(keepws, vars))
				result.append(item)
		return result

	def ul4ondump(self, encoder):
		encoder.dump(self.item)
		encoder.dump(self.varname)
		encoder.dump(self.container)
		encoder.dump(self.condition)

	def ul4onload(self, decoder):
		self.item = decoder.load()
		self.varname = decoder.load()
		self.container = decoder.load()
		self.condition = decoder.load()


@register("dict")
class Dict(AST):
	"""
	AST node for loading a dict object.
	"""

	precedence = 11
	fields = AST.fields.union({"items"})

	def __init__(self, *items):
		self.items = list(items)

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.items!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				for item in self.items:
					p.breakable()
					if len(item) == 2:
						p.pretty(item[0])
						p.text("=")
						p.pretty(item[1])
					else:
						p.text("**")
						p.pretty(item)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield "{"
		for (i, item) in enumerate(self.items):
			if i:
				yield ", "
			if len(item) == 2:
				yield from item[0]._str(indent, keepws)
				yield ": "
				yield from item[1]._str(indent, keepws)
			else:
				yield "**"
				yield from item[0]._str(indent, keepws)
		yield "}"

	def eval(self, keepws, vars):
		result = {}
		for item in self.items:
			if len(item) == 1:
				item = (yield from item[0].eval(keepws, vars))
				result.update(item)
			else:
				key = (yield from item[0].eval(keepws, vars))
				value = (yield from item[1].eval(keepws, vars))
				result[key] = value
		return result

	def ul4ondump(self, encoder):
		encoder.dump(self.items)

	def ul4onload(self, decoder):
		self.items = [tuple(item) for item in decoder.load()]


@register("dictcomp")
class DictComp(AST):
	"""
	AST node for dictionary comprehension.
	"""

	precedence = 11
	fields = AST.fields.union({"key", "value", "varname", "container", "condition"})

	def __init__(self, key=None, value=None, varname=None, container=None, condition=None):
		self.key = key
		self.value = value
		self.varname = varname
		self.container = container
		self.condition = condition

	def __repr__(self):
		s = "<{0.__class__.__module__}.{0.__class__.__qualname__} key={0.key!r} value={0.value!r} varname={0.varname!r} container={0.container!r}".format(self)
		if self.condition is not None:
			s += " {0.condition!r}".format(self)
		return s + " at {:#x}>".format(id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("key=")
				p.pretty(self.key)
				p.breakable()
				p.text("value=")
				p.pretty(self.value)
				p.breakable()
				p.text("varname=")
				p.pretty(self.varname)
				p.breakable()
				p.text("container=")
				p.pretty(self.container)
				if self.condition is not None:
					p.breakable()
					p.text("condition=")
					p.pretty(self.condition)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield "{"
		yield from self.key._str(indent, keepws)
		yield " : "
		yield from self.value._str(indent, keepws)
		yield " for "
		yield _formatnestednameul4(self.varname)
		yield " in "
		yield from self.container._str(indent, keepws)
		if self.condition is not None:
			yield " if "
			yield from self.condition._str(indent, keepws)
		yield "]"

	def eval(self, keepws, vars):
		container = (yield from self.container.eval(keepws, vars))
		vars = collections.ChainMap({}, vars) # Don't let loop variables leak into the surrounding scope
		result = {}
		for item in container:
			_unpackvar(vars, self.varname, item)
			if self.condition is None or (yield from self.condition.eval(keepws, vars)):
				key = (yield from self.key.eval(keepws, vars))
				value = (yield from self.value.eval(keepws, vars))
				result[key] = value
		return result

	def ul4ondump(self, encoder):
		encoder.dump(self.key)
		encoder.dump(self.value)
		encoder.dump(self.varname)
		encoder.dump(self.container)
		encoder.dump(self.condition)

	def ul4onload(self, decoder):
		self.key = decoder.load()
		self.value = decoder.load()
		self.varname = decoder.load()
		self.container = decoder.load()
		self.condition = decoder.load()


@register("genexpr")
class GenExpr(AST):
	"""
	AST node for a generator expression.
	"""

	precedence = 11
	fields = AST.fields.union({"item", "varname", "container", "condition"})

	def __init__(self, item=None, varname=None, container=None, condition=None):
		self.item = item
		self.varname = varname
		self.container = container
		self.condition = condition

	def __repr__(self):
		s = "<{0.__class__.__module__}.{0.__class__.__qualname__} item={0.item!r} varname={0.varname!r} container={0.container!r}".format(self)
		if self.condition is not None:
			s += " condition={0.condition!r}".format(self)
		return s + " at {:#x}>".format(id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("item=")
				p.pretty(self.item)
				p.breakable()
				p.text("varname=")
				p.pretty(self.varname)
				p.breakable()
				p.text("container=")
				p.pretty(self.container)
				if self.condition is not None:
					p.breakable()
					p.text("condition=")
					p.pretty(self.condition)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield "("
		yield from self.item._str(indent, keepws)
		yield " for "
		yield _formatnestednameul4(self.varname)
		yield " in "
		yield from self.container._str(indent, keepws)
		if self.condition is not None:
			yield " if "
			yield from self.condition._str(indent, keepws)
		yield ")"

	def eval(self, keepws, vars):
		container = (yield from self.container.eval(keepws, vars))
		vars = collections.ChainMap({}, vars) # Don't let loop variables leak into the surrounding scope
		def result():
			for item in container:
				_unpackvar(vars, self.varname, item)
				if self.condition is None or (yield from self.condition.eval(keepws, vars)):
					item = (yield from self.item.eval(keepws, vars))
					yield item
		return result()

	def ul4ondump(self, encoder):
		encoder.dump(self.item)
		encoder.dump(self.varname)
		encoder.dump(self.container)
		encoder.dump(self.condition)

	def ul4onload(self, decoder):
		self.item = decoder.load()
		self.varname = decoder.load()
		self.container = decoder.load()
		self.condition = decoder.load()


@register("var")
class Var(AST):
	"""
	AST nodes for loading a variable.
	"""

	precedence = 11
	fields = AST.fields.union({"name"})

	def __init__(self, name=None):
		self.name = name

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.name!r} at {1:#x}>".format(self, id(self))

	def _str(self, indent, keepws):
		yield self.name

	def eval(self, keepws, vars):
		yield from ()
		try:
			return vars[self.name]
		except KeyError:
			try:
				return self.functions[self.name]
			except KeyError:
				return UndefinedVariable(self.name)

	def ul4ondump(self, encoder):
		encoder.dump(self.name)

	def ul4onload(self, decoder):
		self.name = decoder.load()


class Block(Tag):
	"""
	Base class for all AST nodes that are blocks.

	A block contains a sequence of tags that are executed sequencially.
	A block may execute its content zero (e.g. an ``<?if?>`` block) or more times
	(e.g. a ``<?for?>`` block).
	"""

	fields = Tag.fields.union({"endlocation", "content"})

	def __init__(self, location=None):
		super().__init__(location)
		self.endlocation = None
		self.content = []

	def append(self, item):
		self.content.append(item)

	def _str(self, indent, keepws):
		if self.content:
			for node in self.content:
				yield from node._str(indent, keepws)
		else:
			yield indent*"\t"
			yield "pass\n"

	def eval(self, keepws, vars):
		for node in self.content:
			yield from node.eval(keepws, vars)

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.endlocation)
		encoder.dump(self.content)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.endlocation = decoder.load()
		self.content = decoder.load()


@register("ieie")
class IfElIfElse(Block):
	"""
	AST node for an conditional block.

	The content of the :class:`IfElIfElse` block is one :class:`If` block
	followed by zero or more :class:`ElIf` blocks followed by zero or one
	:class:`Else` block.
	"""
	def __init__(self, location=None, condition=None):
		super().__init__(location)
		if condition is not None:
			self.newblock(If(location, condition))

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {1} at {2:#x}>".format(self, repr(self.content)[1:-1], id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def append(self, item):
		self.content[-1].append(item)

	def newblock(self, block):
		if self.content:
			self.content[-1].endlocation = block.location
		self.content.append(block)

	def eval(self, keepws, vars):
		for node in self.content:
			if isinstance(node, Else) or (yield from node.condition.eval(keepws, vars)):
				yield from node.eval(keepws, vars)
				break


@register("if")
class If(Block):
	"""
	AST node for an ``<?if?>`` block.
	"""

	fields = Block.fields.union({"condition"})

	def __init__(self, location=None, condition=None):
		super().__init__(location)
		self.condition = condition

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} condition={0.condition!r} {1} at {2:#x}>".format(self, " ..." if self.content else "", id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("condition=")
				p.pretty(self.condition)
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "if "
		yield from self.condition._str(indent, keepws)
		yield ":\n"
		yield from super()._str(indent+1, keepws)

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.condition)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.condition = decoder.load()


@register("elif")
class ElIf(Block):
	"""
	AST node for an ``<?elif?>`` block.
	"""

	fields = Block.fields.union({"condition"})

	def __init__(self, location=None, condition=None):
		super().__init__(location)
		self.condition = condition

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} condition={0.condition!r} {1} at {2:#x}>".format(self, " ..." if self.content else "", id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("condition=")
				p.pretty(self.condition)
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "elif "
		yield from self.condition._str(indent, keepws)
		yield ":\n"
		yield from super()._str(indent+1, keepws)

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.condition)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.condition = decoder.load()


@register("else")
class Else(Block):
	"""
	AST node for an ``<?else?>`` block.
	"""

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} condition={0.condition!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "else:\n"
		yield from super()._str(indent+1, keepws)


@register("for")
class For(Block):
	"""
	AST node for a ``<?for?>`` loop variable.
	"""

	fields = Block.fields.union({"varname", "container"})

	def __init__(self, location=None, varname=None, container=None):
		super().__init__(location)
		self.varname = varname
		self.container = container

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} varname={0.varname!r} container={0.container!r} {1} at {2:#x}>".format(self, " ..." if self.content else "", id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("varname=")
				p.pretty(self.varname)
				p.breakable()
				p.text("container=")
				p.pretty(self.container)
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.varname)
		encoder.dump(self.container)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.varname = decoder.load()
		self.container = decoder.load()

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "for "
		yield _formatnestednameul4(self.varname)
		yield " in "
		yield from self.container._str(indent, keepws)
		yield ":\n"
		yield from super()._str(indent+1, keepws)

	def eval(self, keepws, vars):
		container = (yield from self.container.eval(keepws, vars))
		vars = collections.ChainMap({}, vars) # Don't let loop variables leak into the surrounding scope
		for item in container:
			_unpackvar(vars, self.varname, item)
			try:
				yield from super().eval(keepws, vars)
			except BreakException:
				break
			except ContinueException:
				pass


@register("break")
class Break(Tag):
	"""
	AST node for a ``<?break?>`` inside a ``<?for?>`` block.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "break\n"

	def eval(self, keepws, vars):
		yield from ()
		raise BreakException()


@register("continue")
class Continue(Tag):
	"""
	AST node for a ``<?continue?>`` inside a ``<?for?>`` block.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "continue\n"

	def eval(self, keepws, vars):
		yield from ()
		raise ContinueException()


@register("getattr")
class GetAttr(AST):
	"""
	AST node for getting an attribute from an object.

	The object is loaded from the AST node :var:`obj` and the attribute name
	is stored in the string :var:`attrname`.
	"""
	precedence = 9
	associative = False
	fields = AST.fields.union({"obj", "attrname"})

	def __init__(self, obj=None, attrname=None):
		self.obj = obj
		self.attrname = attrname

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} obj={0.obj!r}, attrname={0.attrname!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("obj=")
				p.pretty(self.obj)
				p.breakable()
				p.text("attrname=")
				p.pretty(self.attrname)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj)
		yield "."
		yield self.attrname

	def eval(self, keepws, vars):
		obj = (yield from self.obj.eval(keepws, vars))
		try:
			return obj[self.attrname]
		except KeyError:
			return UndefinedKey(self.attrname)

	def ul4ondump(self, encoder):
		encoder.dump(self.obj)
		encoder.dump(self.attrname)

	def ul4onload(self, decoder):
		self.obj = decoder.load()
		self.attrname = decoder.load()


@register("getslice")
class GetSlice(AST):
	"""
	AST node for getting a slice from a list or string object.

	The object is loaded from the AST node :var:`obj` and the start and stop
	indices from the AST node :var:`index1` and :var:`index2`. :var:`index1`
	and :var:`index2` may also be :const:`None` (for missing slice indices,
	which default to the 0 for the start index and the length of the sequence
	for the end index).
	"""

	precedence = 8
	associative = False
	fields = AST.fields.union({"obj", "index1", "index2"})

	def __init__(self, obj=None, index1=None, index2=None):
		self.obj = obj
		self.index1 = index1
		self.index2 = index2

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} obj={0.obj!r} index1={0.index1!r} index2={0.index2!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("obj=")
				p.pretty(self.obj)
				p.breakable()
				p.text("index1=")
				p.pretty(self.index1)
				p.breakable()
				p.text("index2=")
				p.pretty(self.index2)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj)
		yield "["
		if self.index1 is not None:
			yield from self.index1._str(indent, keepws)
		yield ":"
		if self.index2 is not None:
			yield from self.index2._str(indent, keepws)
		yield "]"

	def eval(self, keepws, vars):
		obj = (yield from self.obj.eval(keepws, vars))
		if self.index1 is not None:
			index1 = (yield from self.index1.eval(keepws, vars))
			if self.index2 is not None:
				index2 = (yield from self.index2.eval(keepws, vars))
				return obj[index1:index2]
			else:
				return obj[index1:]
		else:
			if self.index2 is not None:
				index2 = (yield from self.index2.eval(keepws, vars))
				return obj[:index2]
			else:
				return obj[:]

	def ul4ondump(self, encoder):
		encoder.dump(self.obj)
		encoder.dump(self.index1)
		encoder.dump(self.index2)

	def ul4onload(self, decoder):
		self.obj = decoder.load()
		self.index1 = decoder.load()
		self.index2 = decoder.load()


class Unary(AST):
	"""
	Base class for all AST nodes implementing unary operators.
	"""

	fields = AST.fields.union({"obj"})

	def __init__(self, obj=None):
		self.obj = obj

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.obj!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.pretty(self.obj)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		encoder.dump(self.obj)

	def ul4onload(self, decoder):
		self.obj = decoder.load()


@register("not")
class Not(Unary):
	"""
	AST node for the unary ``not`` operator.
	"""

	precedence = 2

	def _str(self, indent, keepws):
		yield "not "
		yield from self._formatop(self.obj)

	def eval(self, keepws, vars):
		return not (yield from self.obj.eval(keepws, vars))


@register("neg")
class Neg(Unary):
	"""
	AST node for the unary negation (i.e. "-") operator.
	"""

	precedence = 7

	def _str(self, indent, keepws):
		yield "-"
		yield from self._formatop(self.obj)

	def eval(self, keepws, vars):
		return -(yield from self.obj.eval(keepws, vars))


class UnaryTag(Tag):
	fields = Tag.fields.union({"obj"})

	def __init__(self, location=None, obj=None):
		super().__init__(location)
		self.obj = obj

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.obj!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.pretty(self.obj)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.obj)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.obj = decoder.load()


@register("print")
class Print(UnaryTag):
	"""
	AST node for a ``<?print?>`` tag.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "print "
		yield from self.obj._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		yield _str((yield from self.obj.eval(keepws, vars)))


@register("printx")
class PrintX(UnaryTag):
	"""
	AST node for a ``<?printx?>`` tag.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "printx "
		yield from self.obj._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		yield _xmlescape((yield from self.obj.eval(keepws, vars)))


@register("return")
class Return(UnaryTag):
	"""
	AST node for a ``<?return?>`` tag.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "return "
		yield from self.obj._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.obj.eval(keepws, vars))
		raise ReturnException(value)


class Binary(AST):
	"""
	Base class for all AST nodes implementing binary operators.
	"""

	fields = AST.fields.union({"obj1", "obj2"})

	def __init__(self, obj1=None, obj2=None):
		self.obj1 = obj1
		self.obj2 = obj2

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} {0.obj1!r} {0.obj2!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.pretty(self.obj1)
				p.breakable()
				p.pretty(self.obj2)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		encoder.dump(self.obj1)
		encoder.dump(self.obj2)

	def ul4onload(self, decoder):
		self.obj1 = decoder.load()
		self.obj2 = decoder.load()


@register("getitem")
class GetItem(Binary):
	"""
	AST node for subscripting operator.

	The object (which must be a list, string or dict) is loaded from the AST
	node :var:`obj1` and the index/key is loaded from the AST node :var:`obj2`.
	"""

	precedence = 9
	associative = False

	@classmethod
	def evaluate(cls, obj1, obj2):
		return obj1[obj2]

	def _str(self, indent, keepws):
		yield from self.obj1._str(indent, keepws)
		yield "["
		yield from self.obj2._str(indent, keepws)
		yield "]"

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		try:
			return obj1[obj2]
		except KeyError:
			return UndefinedKey(obj2)
		except IndexError:
			return UndefinedIndex(obj2)


@register("eq")
class EQ(Binary):
	"""
	AST node for the binary ``==`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " == "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 == obj2


@register("ne")
class NE(Binary):
	"""
	AST node for the binary ``!=`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " 1= "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 != obj2


@register("lt")
class LT(Binary):
	"""
	AST node for the binary ``<`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " < "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 < obj2


@register("le")
class LE(Binary):
	"""
	AST node for the binary ``<=`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " <= "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 <= obj2


@register("gt")
class GT(Binary):
	"""
	AST node for the binary ``>`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " > "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 > obj2


@register("ge")
class GE(Binary):
	"""
	AST node for the binary ``>=`` comparison operator.
	"""

	precedence = 4
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " >= "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 >= obj2


@register("contains")
class Contains(Binary):
	"""
	AST node for the binary containment testing operator.

	The item/key object is loaded from the AST node :var:`obj1` and the container
	object (which must be a list, string or dict) is loaded from the AST node
	:var:`obj2`.
	"""

	precedence = 3
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " in "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 in obj2


@register("notcontains")
class NotContains(Binary):
	"""
	AST node for the inverted containment testing operator.

	The item/key object is loaded from the AST node :var:`obj1` and the container
	object (which must be a list, string or dict) is loaded from the AST node
	:var:`obj2`.
	"""

	precedence = 3
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " not in "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 not in obj2


@register("add")
class Add(Binary):
	"""
	AST node for the binary addition operator.
	"""

	precedence = 5

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "+"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 + obj2


@register("sub")
class Sub(Binary):
	"""
	AST node for the binary substraction operator.
	"""

	precedence = 5
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "-"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 - obj2


@register("mul")
class Mul(Binary):
	"""
	AST node for the binary multiplication operator.
	"""

	precedence = 6

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "*"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 * obj2


@register("floordiv")
class FloorDiv(Binary):
	"""
	AST node for the binary truncating division operator.
	"""

	precedence = 6
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "//"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 // obj2


@register("truediv")
class TrueDiv(Binary):
	"""
	AST node for the binary true division operator.
	"""

	precedence = 6
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "/"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 / obj2


@register("and")
class And(Binary):
	"""
	AST node for the binary ``and`` operator.
	"""

	precedence = 1

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " and "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		if not obj1:
			return obj1
		return (yield from self.obj2.eval(keepws, vars))



@register("or")
class Or(Binary):
	"""
	AST node for the binary ``or`` operator.
	"""

	precedence = 0

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield " or "
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		if obj1:
			return obj1
		return (yield from self.obj2.eval(keepws, vars))


@register("mod")
class Mod(Binary):
	"""
	AST node for the binary modulo operator.
	"""

	precedence = 6
	associative = False

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj1)
		yield "%"
		yield from self._formatop(self.obj2)

	def eval(self, keepws, vars):
		obj1 = (yield from self.obj1.eval(keepws, vars))
		obj2 = (yield from self.obj2.eval(keepws, vars))
		return obj1 % obj2


class ChangeVar(Tag):
	"""
	Baseclass for all AST nodes that store or modify a variable.

	The variable name is stored in the string :var:`varname` and the value that
	will be stored or be used to modify the stored value is loaded from the
	AST node :var:`value`.
	"""

	fields = Tag.fields.union({"varname", "value"})

	def __init__(self, location=None, varname=None, value=None):
		super().__init__(location)
		self.varname = varname
		self.value = value

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} varname={0.varname!r} value={0.value!r} at {1:#x}>".format(self, id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("varname=")
				p.pretty(self.obj1)
				p.text("value=")
				p.breakable()
				p.pretty(self.obj2)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		super().ul4ondump(encoder)
		encoder.dump(self.varname)
		encoder.dump(self.value)

	def ul4onload(self, decoder):
		super().ul4onload(decoder)
		self.varname = decoder.load()
		self.value = decoder.load()


@register("storevar")
class StoreVar(ChangeVar):
	"""
	AST node that stores a value into a variable.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " = "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		_unpackvar(vars, self.varname, value)


@register("addvar")
class AddVar(ChangeVar):
	"""
	AST node that adds a value to a variable (i.e. the ``+=`` operator).
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " += "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] += value


@register("subvar")
class SubVar(ChangeVar):
	"""
	AST node that substracts a value from a variable (i.e. the ``-=`` operator).
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " -= "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] -= value


@register("mulvar")
class MulVar(ChangeVar):
	"""
	AST node that multiplies a variable by a value (i.e. the ``*=`` operator).
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " *= "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] *= value


@register("floordivvar")
class FloorDivVar(ChangeVar):
	"""
	AST node that divides a variable by a value (truncating to an integer value;
	i.e. the ``//=`` operator).
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " //= "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] //= value


@register("truedivvar")
class TrueDivVar(ChangeVar):
	"""
	AST node that divides a variable by a value (i.e. the ``/=`` operator).
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " /= "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] /= value


@register("modvar")
class ModVar(ChangeVar):
	"""
	AST node for the ``%=`` operator.
	"""

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield _formatnestednameul4(self.varname)
		yield " %= "
		yield from self.value._str(indent, keepws)
		yield "\n"

	def eval(self, keepws, vars):
		value = (yield from self.value.eval(keepws, vars))
		vars[self.varname] %= value


@register("callfunc")
class CallFunc(AST):
	"""
	AST node for calling an function.

	The object to be called is stored in the attribute :var:`obj`. The list of
	positional arguments is loaded from the list of AST nodes :var:`args`.
	Keyword arguments are in :var:`kwargs`. `var`:remargs` is the AST node
	for the ``*`` argument (and may by ``None`` if there is no ``*`` argument).
	`var`:remkwargs` is the AST node for the ``**`` argument (and may by ``None``
	if there is no ``**`` argument)
	"""

	precedence = 10
	associative = False
	fields = AST.fields.union({"obj", "args", "kwargs", "remargs", "remkwargs"})

	def __init__(self, obj=None):
		self.obj = obj
		self.args = []
		self.kwargs = []
		self.remargs = None
		self.remkwargs = None

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} obj={0.obj!r}{1}{2}{3}{4} at {5:#x}>".format(
			self,
			"".join(" {!r}".format(arg) for arg in self.args),
			"".join(" {}={!r}".format(argname, argvalue) for (argname, argvalue) in self.kwargs),
			" *{!r}".format(self.remargs) if self.remargs is not None else "",
			" **{!r}".format(self.remkwargs) if self.remargs is not None else "",
			id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("obj=")
				p.pretty(self.obj)
				for arg in self.args:
					p.breakable()
					p.pretty(arg)
				for (argname, arg) in self.kwargs:
					p.breakable()
					p.text("{}=".format(argname))
					p.pretty(arg)
				if self.remargs is not None:
					p.breakable()
					p.text("*")
					p.pretty(self.remargs)
				if self.remkwargs is not None:
					p.breakable()
					p.text("**")
					p.pretty(self.remkwargs)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield from self.obj._str(indent, keepws)
		yield "("
		first = True
		for arg in self.args:
			if first:
				first = False
			else:
				yield ", "
			yield from arg._str(indent, keepws)
		for (argname, argvalue) in self.kwargs:
			if first:
				first = False
			else:
				yield ", "
			yield argname
			yield "="
			yield from argvalue._str(indent, keepws)
		if self.remargs is not None:
			if first:
				first = False
			else:
				yield ", "
			yield "*"
			yield from self.remargs._str(indent, keepws)
		if self.remkwargs is not None:
			if first:
				first = False
			else:
				yield ", "
			yield "**"
			yield from self.remkwargs._str(indent, keepws)
		yield ")"

	def eval(self, keepws, vars):
		obj = (yield from self.obj.eval(keepws, vars))
		args = []
		for arg in self.args:
			arg = (yield from arg.eval(keepws, vars))
			args.append(arg)
		kwargs = {}
		for (argname, arg) in self.kwargs:
			kwargs[argname] = (yield from arg.eval(keepws, vars))
		if self.remargs is not None:
			args.extend((yield from self.remargs.eval(keepws, vars)))
		if self.remkwargs is not None:
			kwargs.update((yield from self.remkwargs.eval(keepws, vars)))
		result = obj(*args, **kwargs)
		if isinstance(result, types.GeneratorType):
			return (yield from result)
		else:
			return result

	def ul4ondump(self, encoder):
		encoder.dump(self.obj)
		encoder.dump(self.args)
		encoder.dump(self.kwargs)
		encoder.dump(self.remargs)
		encoder.dump(self.remkwargs)

	def ul4onload(self, decoder):
		self.obj = decoder.load()
		self.args = decoder.load()
		self.kwargs = [tuple(arg) for arg in decoder.load()]
		self.remargs = decoder.load()
		self.remkwargs = decoder.load()


@register("callmeth")
class CallMeth(AST):
	"""
	AST node for calling a method.

	The method name is stored in the string :var:`methname`. The object for which
	the method will be called is loaded from the AST node :var:`obj` and the list
	of arguments is loaded from the list of AST nodes :var:`args`. Keyword
	arguments are in :var:`kwargs`. `var`:remargs` is the AST node for the ``*``
	argument (and may by ``None`` if there is no ``*`` argument).
	`var`:remkwargs` is the AST node for the ``**`` argument (and may by ``None``
	if there is no ``**`` argument)
	"""

	precedence = 9
	associative = False
	fields = AST.fields.union({"obj", "methname", "args", "kwargs", "remargs", "remkwargs"})

	def __init__(self, obj=None, methname=None):
		self.obj = obj
		self.methname = methname
		self.args = []
		self.kwargs = []
		self.remargs = None
		self.remkwargs = None

	def __repr__(self):
		return "<{0.__class__.__module__}.{0.__class__.__qualname__} methname={0.methname!r} obj={0.obj!r}{1}{2}{3}{4} at {5:#x}>".format(
			self,
			"".join(" {!r}".format(arg) for arg in self.args),
			"".join(" {}={!r}".format(argname, argvalue) for (argname, argvalue) in self.kwargs),
			" *{!r}".format(self.remargs) if self.remargs is not None else "",
			" **{!r}".format(self.remkwargs) if self.remargs is not None else "",
			id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("methname=")
				p.pretty(self.methname)
				p.breakable()
				p.text("obj=")
				p.pretty(self.obj)
				for arg in self.args:
					p.breakable()
					p.pretty(arg)
				for (argname, arg) in self.kwargs:
					p.breakable()
					p.text("{}=".format(argname))
					p.pretty(arg)
				if self.remargs is not None:
					p.breakable()
					p.text("*")
					p.pretty(self.remargs)
				if self.remkwargs is not None:
					p.breakable()
					p.text("**")
					p.pretty(self.remkwargs)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def _str(self, indent, keepws):
		yield from self._formatop(self.obj)
		yield ".("
		first = True
		for arg in self.args:
			if first:
				first = False
			else:
				yield ", "
			yield from arg._str(indent, keepws)
		for (argname, argvalue) in self.kwargs:
			if first:
				first = False
			else:
				yield ", "
			yield argname
			yield "="
			yield from argvalue._str(indent, keepws)
		if self.remargs is not None:
			if first:
				first = False
			else:
				yield ", "
			yield "*"
			yield from self.remargs._str(indent, keepws)
		if self.remkwargs is not None:
			if first:
				first = False
			else:
				yield ", "
			yield "**"
			yield from self.remkwargs._str(indent, keepws)
		yield ")"

	def eval(self, keepws, vars):
		obj = (yield from self.obj.eval(keepws, vars))
		args = []
		for arg in self.args:
			arg = (yield from arg.eval(keepws, vars))
			args.append(arg)
		kwargs = {}
		for (argname, arg) in self.kwargs:
			kwargs[argname] = (yield from arg.eval(keepws, vars))
		if self.remargs is not None:
			args.extend((yield from self.remargs.eval(keepws, vars)))
		if self.remkwargs is not None:
			kwargs.update((yield from self.remkwargs.eval(keepws, vars)))
		result = self.methods[self.methname](obj, *args, **kwargs)
		if isinstance(result, types.GeneratorType):
			return (yield from result)
		else:
			return result

	def ul4ondump(self, encoder):
		encoder.dump(self.methname)
		encoder.dump(self.obj)
		encoder.dump(self.args)
		encoder.dump(self.kwargs)
		encoder.dump(self.remargs)
		encoder.dump(self.remkwargs)

	def ul4onload(self, decoder):
		self.methname = decoder.load()
		self.obj = decoder.load()
		self.args = decoder.load()
		self.kwargs = [tuple(arg) for arg in decoder.load()]
		self.remargs = decoder.load()
		self.remkwargs = decoder.load()


@register("template")
class Template(Block):
	"""
	A template object is normally created by passing the template source to the
	constructor. It can also be loaded from the compiled format via the class
	methods :meth:`load` (from a stream) or :meth:`loads` (from a string).

	The compiled format can be generated with the methods :meth:`dump` (which
	dumps the format to a stream) or :meth:`dumps` (which returns a string with
	the compiled format).

	Rendering the template can be done with the methods :meth:`render` (which
	is a generator) or :meth:`renders` (which returns a string).

	A :class:`Template` object is itself an AST node. Evaluating it will store
	the template object under its name in the local variables.

	A :class:`Template` can also be called as a function (returning the result
	of the first ``<?return?>`` tag encountered. In this case all output of the
	template will be ignored.
	"""
	fields = Block.fields.union({"source", "name", "keepws", "startdelim", "enddelim", "endlocation"})

	version = "24"

	def __init__(self, source=None, name=None, keepws=True, startdelim="<?", enddelim="?>"):
		"""
		Create a :class:`Template` object. If :var:`source` is ``None``, the
		:class:`Template` remains uninitialized, otherwise :var:`source` will be
		compiled (using :var:`startdelim` and :var:`enddelim` as the tag
		delimiters). :var:`name` is the name of the template. It will be used in
		exception messages and should be a valid Python identifier. If
		:var:`keepws` is false linefeeds and indentation will be ignored in the
		literal text in templates (i.e. the text between the tags). However
		trailing whitespace at the end of the line will be honored regardless of
		the value of :var:`keepws`. Output will always be ignored when calling
		a template as a function.
		"""
		# ``location``/``endlocation`` will remain ``None`` for a top level template
		# For a subtemplate/subfunction ``location`` will be set to the location of the ``<?template?>`` tag
		# in :meth:`_compile` and ``endlocation`` will be the location of the ``<?end template?>`` tag
		super().__init__(None)
		self.keepws = keepws
		self.startdelim = startdelim
		self.enddelim = enddelim
		self.name = name
		self.source = None

		# If we have source code compile it
		if source is not None:
			self._compile(source, name, startdelim, enddelim)

	def __repr__(self):
		s = "<{0.__class__.__module__}.{0.__class__.__qualname__} name={0.name!r} keepws={0.keepws!r}".format(self)
		if self.startdelim != "<?":
			s += " startdelim={0.startdelim!r}".format(self)
		if self.enddelim != "?>":
			s += " enddelim={0.enddelim!r}".format(self)
		if self.content:
			s + " ..."
		return s + " at {:#x}>".format(id(self))

	def _str(self, indent, keepws):
		yield indent*"\t"
		yield "def "
		yield self.name if self.name is not None else "unnamed"
		yield ":\n"
		indent += 1
		yield from super()._str(indent, keepws)

	def __str__(self):
		return "".join(self._str(0, self.keepws))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("name=")
				p.pretty(self.name)
				p.breakable()
				p.text("keepws=")
				p.pretty(self.keepws)
				if self.startdelim != "<?":
					p.breakable()
					p.text("startdelim=")
					p.pretty(self.startdelim)
				if self.enddelim != "?>":
					p.breakable()
					p.text("enddelim=")
					p.pretty(self.enddelim)
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))

	def ul4ondump(self, encoder):
		encoder.dump(self.version)
		encoder.dump(self.source)
		encoder.dump(self.name)
		encoder.dump(self.keepws)
		encoder.dump(self.startdelim)
		encoder.dump(self.enddelim)
		encoder.dump(self.location)
		encoder.dump(self.endlocation)
		encoder.dump(self.content)

	def ul4onload(self, decoder):
		version = decoder.load()
		if version != self.version:
			raise ValueError("invalid version, expected {!r}, got {!r}".format(self.version, version))
		self.source = decoder.load()
		self.name = decoder.load()
		self.keepws = decoder.load()
		self.startdelim = decoder.load()
		self.enddelim = decoder.load()
		self.location = decoder.load()
		self.endlocation = decoder.load()
		self.content = decoder.load()

	@classmethod
	def loads(cls, data):
		"""
		The class method :meth:`loads` loads the template/function from string
		:var:`data`. :var:`data` must contain the template/function in compiled
		UL4ON format.
		"""
		from ll import ul4on
		return ul4on.loads(data)

	@classmethod
	def load(cls, stream):
		"""
		The class method :meth:`load` loads the template/function from the stream
		:var:`stream`. The stream must contain the template/function in compiled
		UL4ON format.
		"""
		from ll import ul4on
		return ul4on.load(stream)

	def dump(self, stream):
		"""
		:meth:`dump` dumps the template/function in compiled UL4ON format to the
		stream :var:`stream`.
		"""
		from ll import ul4on
		ul4on.dump(self, stream)

	def dumps(self):
		"""
		:meth:`dumps` returns the template/function in compiled UL4ON format
		(as a string).
		"""
		from ll import ul4on
		return ul4on.dumps(self)

	def render(self, **vars):
		"""
		Render the template iteratively (i.e. this is a generator).
		:var:`vars` contains the top level variables available to the
		template code.
		"""
		yield from super().eval(self.keepws, vars) # Bypass ``self.eval()`` which simply stores the object as a local variable

	def renders(self, **vars):
		"""
		Render the template as a string. :var:`vars` contains the top level
		variables available to the template code.
		"""
		return "".join(self.render(**vars))

	def __call__(self, **vars):
		"""
		Call the template as a function and return the resulting value.
		:var:`vars` contains the top level variables available to the template code.
		"""
		try:
			for output in super().eval(self.keepws, vars): # Bypass ``self.eval()`` which simply stores the object as a local variable
				pass # Ignore all output
		except ReturnException as ex:
			return ex.value

	def jssource(self):
		"""
		Return the template as the source code of a Javascript function.
		"""
		return "ul4.Template.loads({})".format(_asjson(self.dumps()))

	def javasource(self):
		"""
		Return the template as Java source code.
		"""
		return "com.livinglogic.ul4.InterpretedTemplate.loads({})".format(misc.javaexpr(self.dumps()))

	def _tokenize(self, source, startdelim, enddelim):
		"""
		Tokenize the template/function source code :var:`source` into tags and
		non-tag text. :var:`startdelim` and :var:`enddelim` are used as the tag
		delimiters.

		This is a generator which produces :class:`Location` objects for each tag
		or non-tag text. It will be called by :meth:`_compile` internally.
		"""
		pattern = "{}(printx|print|code|for|if|elif|else|end|break|continue|def|return|note)(\s*((.|\\n)*?)\s*)?{}".format(re.escape(startdelim), re.escape(enddelim))
		pos = 0
		for match in re.finditer(pattern, source):
			if match.start() != pos:
				yield Location(source, None, pos, match.start(), pos, match.start())
			type = source[match.start(1):match.end(1)]
			if type != "note":
				yield Location(source, type, match.start(), match.end(), match.start(3), match.end(3))
			pos = match.end()
		end = len(source)
		if pos != end:
			yield Location(source, None, pos, end, pos, end)

	def _parser(self, location, error):
		from ll import UL4Lexer, UL4Parser
		source = location.code
		if not source:
			raise ValueError(error)
		stream = antlr3.ANTLRStringStream(source)
		lexer = UL4Lexer.UL4Lexer(stream)
		lexer.location = location
		tokens = antlr3.CommonTokenStream(lexer)
		parser = UL4Parser.UL4Parser(tokens)
		parser.location = location
		return parser

	def _compile(self, source, name, startdelim, enddelim):
		"""
		Compile the template source code :var:`source` into an AST.
		:var:`startdelim` and :var:`enddelim` are used as the tag delimiters.
		"""
		self.name = name
		self.startdelim = startdelim
		self.enddelim = enddelim

		# This stack stores the nested for/if/elif/else/def blocks
		stack = [self]

		self.source = source

		if source is None:
			return

		def parseexpr(location):
			return self._parser(location, "expression required").expression()

		def parsestmt(location):
			return self._parser(location, "statement required").statement()

		def parsefor(location):
			return self._parser(location, "loop expression required").for_()

		for location in self._tokenize(source, startdelim, enddelim):
			try:
				if location.type is None:
					stack[-1].append(Text(location))
				elif location.type == "print":
					stack[-1].append(Print(location, parseexpr(location)))
				elif location.type == "printx":
					stack[-1].append(PrintX(location, parseexpr(location)))
				elif location.type == "code":
					stack[-1].append(parsestmt(location))
				elif location.type == "if":
					block = IfElIfElse(location, parseexpr(location))
					stack[-1].append(block)
					stack.append(block)
				elif location.type == "elif":
					if not isinstance(stack[-1], IfElIfElse):
						raise BlockError("elif doesn't match and if")
					elif isinstance(stack[-1].content[-1], Else):
						raise BlockError("else already seen in if")
					stack[-1].newblock(ElIf(location, parseexpr(location)))
				elif location.type == "else":
					if not isinstance(stack[-1], IfElIfElse):
						raise BlockError("else doesn't match any if")
					elif isinstance(stack[-1].content[-1], Else):
						raise BlockError("else already seen in if")
					stack[-1].newblock(Else(location))
				elif location.type == "end":
					if len(stack) <= 1:
						raise BlockError("not in any block")
					code = location.code
					if code:
						if code == "if":
							if not isinstance(stack[-1], IfElIfElse):
								raise BlockError("endif doesn't match any if")
						elif code == "for":
							if not isinstance(stack[-1], For):
								raise BlockError("endfor doesn't match any for")
						elif code == "def":
							if not isinstance(stack[-1], Template):
								raise BlockError("enddef doesn't match any def")
						else:
							raise BlockError("illegal end value {!r}".format(code))
					last = stack.pop()
					# Set ``endlocation`` of block
					last.endlocation = location
					if isinstance(last, IfElIfElse):
						last.content[-1].endlocation = location
				elif location.type == "for":
					block = parsefor(location)
					stack[-1].append(block)
					stack.append(block)
				elif location.type == "break":
					for block in reversed(stack):
						if isinstance(block, For):
							break
						elif isinstance(block, Template):
							raise BlockError("break outside of for loop")
					stack[-1].append(Break(location))
				elif location.type == "continue":
					for block in reversed(stack):
						if isinstance(block, For):
							break
						elif isinstance(block, Template):
							raise BlockError("continue outside of for loop")
					stack[-1].append(Continue(location))
				elif location.type == "def":
					block = Template(None, location.code, self.keepws, self.startdelim, self.enddelim)
					block.location = location # Set start ``location`` of sub template
					block.source = self.source # The source of the top level template (so that the offsets in :class:`Location` are correct)
					stack[-1].append(block)
					stack.append(block)
				elif location.type == "return":
					stack[-1].append(Return(location, parseexpr(location)))
				else: # Can't happen
					raise ValueError("unknown tag {!r}".format(location.type))
			except Exception as exc:
				raise Error(location) from exc
		if len(stack) > 1:
			raise Error(stack[-1].location) from BlockError("block unclosed")

	def eval(self, keepws, vars):
		yield from ()
		vars[self.name] = TemplateClosure(self, vars)


###
### Functions & methods
###

@AST.makefunction
def _print(*values):
	for (i, value) in enumerate(values):
		if i:
			yield " "
		yield _str(value)


@AST.makefunction
def _printx(*values):
	for (i, value) in enumerate(values):
		if i:
			yield " "
		yield _xmlescape(value)


@AST.makefunction
def _str(obj=""):
	if obj is None:
		return ""
	elif isinstance(obj, Undefined):
		return ""
	else:
		return str(obj)


@AST.makefunction
def _repr(obj):
	if isinstance(obj, str):
		return repr(obj)
	elif isinstance(obj, datetime.datetime):
		s = str(obj.isoformat())
		if s.endswith("T00:00:00"):
			s = s[:-9]
		return "@({})".format(s)
	elif isinstance(obj, datetime.date):
		return "@({})".format(obj.isoformat())
	elif isinstance(obj, datetime.timedelta):
		return repr(obj).partition(".")[-1]
	elif isinstance(obj, color.Color):
		if obj[3] == 0xff:
			s = "#{:02x}{:02x}{:02x}".format(obj[0], obj[1], obj[2])
			if s[1]==s[2] and s[3]==s[4] and s[5]==s[6]:
				return "#{}{}{}".format(s[1], s[3], s[5])
			return s
		else:
			s = "#{:02x}{:02x}{:02x}{:02x}".format(*obj)
			if s[1]==s[2] and s[3]==s[4] and s[5]==s[6] and s[7]==s[8]:
				return "#{}{}{}{}".format(s[1], s[3], s[5], s[7])
			return s
	elif isinstance(obj, collections.Sequence):
		return "[{}]".format(", ".join(_repr(item) for item in obj))
	elif isinstance(obj, collections.Mapping):
		return "{{{}}}".format(", ".join("{}: {}".format(_repr(key), _repr(value)) for (key, value) in obj.items()))
	else:
		return repr(obj)


@AST.makefunction
def _now():
	return datetime.datetime.now()


@AST.makefunction
def _utcnow():
	return datetime.datetime.utcnow()


@AST.makefunction
def _date(year, month, day, hour=0, minute=0, second=0, microsecond=0):
	return datetime.datetime(year, month, day, hour, minute, second, microsecond)


@AST.makefunction
def _timedelta(days=0, seconds=0, microseconds=0):
	return datetime.timedelta(days, seconds, microseconds)


@AST.makefunction
def _monthdelta(months=0):
	return misc.monthdelta(months)


@AST.makefunction
def _random():
	return random.random()


@AST.makefunction
def _xmlescape(obj):
	if obj is None:
		return ""
	elif isinstance(obj, Undefined):
		return ""
	else:
		return misc.xmlescape(str(obj))


@AST.makefunction
def _csv(obj):
	if obj is None:
		return ""
	elif isinstance(obj, Undefined):
		return ""
	elif not isinstance(obj, str):
		obj = _repr(obj)
	if any(c in obj for c in ',"\n'):
		return '"{}"'.format(obj.replace('"', '""'))
	return obj


@AST.makefunction
def _asjson(obj):
	if obj is None:
		return "null"
	elif isinstance(obj, Undefined):
		return "{}.undefined"
	if isinstance(obj, (bool, int, float, str)):
		return json.dumps(obj)
	elif isinstance(obj, datetime.datetime):
		return "new Date({}, {}, {}, {}, {}, {}, {})".format(obj.year, obj.month-1, obj.day, obj.hour, obj.minute, obj.second, obj.microsecond//1000)
	elif isinstance(obj, datetime.date):
		return "new Date({}, {}, {})".format(obj.year, obj.month-1, obj.day)
	elif isinstance(obj, datetime.timedelta):
		return "ul4.TimeDelta.create({}, {}, {})".format(obj.days, obj.seconds, obj.microseconds)
	elif isinstance(obj, misc.monthdelta):
		return "ul4.MonthDelta.create({})".format(obj.months)
	elif isinstance(obj, color.Color):
		return "ul4.Color.create({}, {}, {}, {})".format(*obj)
	elif isinstance(obj, collections.Mapping):
		return "{{{}}}".format(", ".join("{}: {}".format(_asjson(key), _asjson(value)) for (key, value) in obj.items()))
	elif isinstance(obj, collections.Sequence):
		return "[{}]".format(", ".join(_asjson(item) for item in obj))
	elif isinstance(obj, Template):
		return obj.jssource()
	else:
		raise TypeError("can't handle object of type {}".format(type(obj)))


@AST.makefunction
def _fromjson(string):
	from ll import ul4on
	return json.loads(string)


@AST.makefunction
def _asul4on(obj):
	from ll import ul4on
	return ul4on.dumps(obj)


@AST.makefunction
def _fromul4on(string):
	from ll import ul4on
	return ul4on.loads(string)


@AST.makefunction
def _int(obj=0, base=None):
	if base is None:
		return int(obj)
	else:
		return int(obj, base)


@AST.makefunction
def _float(obj=0.0):
	return float(obj)


@AST.makefunction
def _bool(obj=False):
	return bool(obj)


@AST.makefunction
def _len(sequence):
	return len(sequence)


@AST.makefunction
def _abs(number):
	return abs(number)


@AST.makefunction
def _any(iterable):
	return any(iterable)


@AST.makefunction
def _all(iterable):
	return all(iterable)


@AST.makefunction
def _enumerate(iterable, start=0):
	yield from ()
	return enumerate(iterable, start)


@AST.makefunction
def _enumfl(iterable, start=0):
	yield from ()
	def result(iterable):
		lastitem = None
		first = True
		i = start
		it = iter(iterable)
		try:
			item = next(it)
		except StopIteration:
			return
		while True:
			try:
				(lastitem, item) = (item, next(it))
			except StopIteration:
				yield (i, first, True, item) # Items haven't been swapped yet
				return
			else:
				yield (i, first, False, lastitem)
				first = False
			i += 1
	return result(iterable)


@AST.makefunction
def _isfirstlast(iterable):
	yield from ()
	def result(iterable):
		lastitem = None
		first = True
		it = iter(iterable)
		try:
			item = next(it)
		except StopIteration:
			return
		while True:
			try:
				(lastitem, item) = (item, next(it))
			except StopIteration:
				yield (first, True, item) # Items haven't been swapped yet
				return
			else:
				yield (first, False, lastitem)
				first = False
	return result(iterable)


@AST.makefunction
def _isfirst(iterable):
	yield from ()
	def result(iterable):
		first = True
		for item in iterable:
			yield (first, item)
			first = False
	return result(iterable)


@AST.makefunction
def _islast(iterable):
	yield from ()
	def result(iterable):
		lastitem = None
		it = iter(iterable)
		try:
			item = next(it)
		except StopIteration:
			return
		while True:
			try:
				(lastitem, item) = (item, next(it))
			except StopIteration:
				yield (True, item) # Items haven't been swapped yet
				return
			else:
				yield (False, lastitem)
	return result(iterable)


@AST.makefunction
def _isundefined(obj):
	return isinstance(obj, Undefined)


@AST.makefunction
def _isdefined(obj):
	return not isinstance(obj, Undefined)


@AST.makefunction
def _isnone(obj):
	return obj is None


@AST.makefunction
def _isstr(obj):
	return isinstance(obj, str)


@AST.makefunction
def _isint(obj):
	return isinstance(obj, int) and not isinstance(obj, bool)


@AST.makefunction
def _isfloat(obj):
	return isinstance(obj, float)


@AST.makefunction
def _isbool(obj):
	return isinstance(obj, bool)


@AST.makefunction
def _isdate(obj):
	return isinstance(obj, (datetime.datetime, datetime.date))


@AST.makefunction
def _istimedelta(obj):
	return isinstance(obj, datetime.timedelta)


@AST.makefunction
def _ismonthdelta(obj):
	return isinstance(obj, misc.monthdelta)


@AST.makefunction
def _islist(obj):
	return isinstance(obj, collections.Sequence) and not isinstance(obj, str) and not isinstance(obj, color.Color)


@AST.makefunction
def _isdict(obj):
	return isinstance(obj, collections.Mapping) and not isinstance(obj, Template)


@AST.makefunction
def _iscolor(obj):
	return isinstance(obj, color.Color)


@AST.makefunction
def _istemplate(obj):
	return isinstance(obj, (Template, TemplateClosure))


@AST.makefunction
def _isfunction(obj):
	return callable(obj)


@AST.makefunction
def _chr(i):
	return chr(i)


@AST.makefunction
def _ord(c):
	return ord(c)


@AST.makefunction
def _hex(number):
	return hex(number)


@AST.makefunction
def _oct(number):
	return oct(number)


@AST.makefunction
def _bin(number):
	return bin(number)


@AST.makefunction
def _min(*args):
	return min(*args)


@AST.makefunction
def _max(*args):
	return max(*args)


@AST.makefunction
def _sorted(iterable):
	return sorted(iterable)


@AST.makefunction
def _range(*args):
	return range(*args)


@AST.makefunction
def _type(obj):
	if obj is None:
		return "none"
	elif isinstance(obj, Undefined):
		return "undefined"
	elif isinstance(obj, str):
		return "str"
	elif isinstance(obj, bool):
		return "bool"
	elif isinstance(obj, int):
		return "int"
	elif isinstance(obj, float):
		return "float"
	elif isinstance(obj, (datetime.datetime, datetime.date)):
		return "date"
	elif isinstance(obj, datetime.timedelta):
		return "timedelta"
	elif isinstance(obj, misc.monthdelta):
		return "monthdelta"
	elif isinstance(obj, color.Color):
		return "color"
	elif isinstance(obj, (Template, TemplateClosure)):
		return "template"
	elif isinstance(obj, collections.Mapping):
		return "dict"
	elif isinstance(obj, color.Color):
		return "color"
	elif isinstance(obj, collections.Sequence):
		return "list"
	elif callable(obj):
		return "function"
	return None


@AST.makefunction
def _reversed(sequence):
	yield from ()
	return reversed(sequence)


@AST.makefunction
def _randrange(*args):
	return random.randrange(*args)


@AST.makefunction
def _randchoice(sequence):
	return random.choice(sequence)


@AST.makefunction
def _format(obj, fmt, lang=None):
	if isinstance(obj, (datetime.date, datetime.time, datetime.timedelta)):
		if lang is None:
			lang = "en"
		oldlocale = locale.getlocale()
		try:
			for candidate in (locale.normalize(lang), locale.normalize("en"), ""):
				try:
					locale.setlocale(locale.LC_ALL, candidate)
					return format(obj, fmt)
				except locale.Error:
					if not candidate:
						return format(obj, fmt)
		finally:
			try:
				locale.setlocale(locale.LC_ALL, oldlocale)
			except locale.Error:
				pass
	else:
		return format(obj, fmt)


@AST.makefunction
def _zip(*iterables):
	return zip(*iterables)


@AST.makefunction
def _urlquote(string):
	return urlparse.quote_plus(string)


@AST.makefunction
def _urlunquote(string):
	return urlparse.unquote_plus(string)


@AST.makefunction
def _rgb(r, g, b, a=1.0):
	return color.Color.fromrgb(r, g, b, a)


@AST.makefunction
def _hls(h, l, s, a=1.0):
	return color.Color.fromhls(h, l, s, a)


@AST.makefunction
def _hsv(h, s, v, a=1.0):
	return color.Color.fromhsv(h, s, v, a)


@AST.makemethod
def _split(obj, sep=None, count=None):
	return obj.split(sep, count if count is not None else -1)


@AST.makemethod
def _rsplit(obj, sep=None, count=None):
	return obj.rsplit(sep, count if count is not None else -1)


@AST.makemethod
def _strip(obj, chars=None):
	return obj.strip(chars)


@AST.makemethod
def _lstrip(obj, chars=None):
	return obj.lstrip(chars)


@AST.makemethod
def _rstrip(obj, chars=None):
	return obj.rstrip(chars)


@AST.makemethod
def _find(obj, sub, start=None, end=None):
	if isinstance(obj, str):
		return obj.find(sub, start, end)
	else:
		try:
			if end is None:
				if start is None:
					return obj.index(sub)
				return obj.index(sub, start)
			return obj.index(sub, start, end)
		except ValueError:
			return -1


@AST.makemethod
def _rfind(obj, sub, start=None, end=None):
	if isinstance(obj, str):
		return obj.rfind(sub, start, end)
	else:
		for i in reversed(range(*slice(start, end).indices(len(obj)))):
			if obj[i] == sub:
				return i
		return -1


@AST.makemethod
def _startswith(obj, prefix):
	return obj.startswith(prefix)


@AST.makemethod
def _endswith(obj, suffix):
	return obj.endswith(suffix)


@AST.makemethod
def _upper(obj):
	return obj.upper()


@AST.makemethod
def _lower(obj):
	return obj.lower()


@AST.makemethod
def _capitalize(obj):
	return obj.capitalize()


@AST.makemethod
def _replace(obj, old, new, count=None):
	if count is None:
		return obj.replace(old, new)
	else:
		return obj.replace(old, new, count)


@AST.makemethod
def _r(obj):
	return obj.r()


@AST.makemethod
def _g(obj):
	return obj.g()


@AST.makemethod
def _b(obj):
	return obj.b()


@AST.makemethod
def _a(obj):
	return obj.a()


@AST.makemethod
def _hls(obj):
	return obj.hls()


@AST.makemethod
def _hlsa(obj):
	return obj.hlsa()


@AST.makemethod
def _hsv(obj):
	return obj.hsv()


@AST.makemethod
def _hsva(obj):
	return obj.hsva()


@AST.makemethod
def _lum(obj):
	return obj.lum()


@AST.makemethod
def _weekday(obj):
	return obj.weekday()


@AST.makemethod
def _week(obj, firstweekday=None):
	if firstweekday is None:
		firstweekday = 0
	else:
		firstweekday %= 7
	jan1 = obj.__class__(obj.year, 1, 1)
	yearday = (obj - jan1).days+7
	jan1weekday = jan1.weekday()
	while jan1weekday != firstweekday:
		yearday -= 1
		jan1weekday += 1
		if jan1weekday == 7:
			jan1weekday = 0
	return yearday//7


@AST.makemethod
def _items(obj):
	yield from ()
	return obj.items()


@AST.makemethod
def _values(obj):
	yield from ()
	return obj.values()


@AST.makemethod
def _join(obj, iterable):
	return obj.join(iterable)


@AST.makemethod
def _render(obj, **vars):
	yield from obj.render(**vars)


@AST.makemethod
def _renders(obj, **vars):
	return obj.renders(**vars)


@AST.makemethod
def _mimeformat(obj):
	weekdayname = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
	monthname = (None, "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
	return "{1}, {0.day:02d} {2:3} {0.year:4} {0.hour:02}:{0.minute:02}:{0.second:02} GMT".format(obj, weekdayname[obj.weekday()], monthname[obj.month])


@AST.makemethod
def _isoformat(obj):
	result = obj.isoformat()
	suffix = "T00:00:00"
	if result.endswith(suffix):
		return result[:-len(suffix)]
	return result


@AST.makemethod
def _yearday(obj):
	return (obj - obj.__class__(obj.year, 1, 1)).days+1


@AST.makemethod
def _get(obj, key, default=None):
	return obj.get(key, default)


@AST.makemethod
def _withlum(obj, lum):
	return obj.withlum(lum)


@AST.makemethod
def _witha(obj, a):
	return obj.witha(a)


@AST.makemethod
def _day(obj):
	return obj.day


@AST.makemethod
def _month(obj):
	return obj.month


@AST.makemethod
def _year(obj):
	return obj.year


@AST.makemethod
def _hour(obj):
	return obj.hour


@AST.makemethod
def _minute(obj):
	return obj.minute


@AST.makemethod
def _second(obj):
	return obj.second


@AST.makemethod
def _microsecond(obj):
	return obj.microsecond


@AST.makemethod
def _days(obj):
	return obj.days


@AST.makemethod
def _seconds(obj):
	return obj.seconds


@AST.makemethod
def _microseconds(obj):
	return obj.microseconds


@AST.makemethod
def _months(obj):
	return obj.months


class TemplateClosure(Object):
	fields = {"location", "endlocation", "name", "source", "startdelim", "enddelim", "content"}

	def __init__(self, template, vars):
		self.template = template
		# Freeze variables of the currently running templates/functions
		self.vars = vars.copy()

	def render(self, **vars):
		return self.template.render(**collections.ChainMap(vars, self.vars))

	def renders(self, **vars):
		return self.template.renders(**collections.ChainMap(vars, self.vars))

	def __call__(self, **vars):
		return self.template(**collections.ChainMap(vars, self.vars))

	def __getattr__(self, name):
		return getattr(self.template, name)

	def __repr__(self):
		s = "<{0.__class__.__module__}.{0.__class__.__qualname__} name={0.name!r} keepws={0.keepws!r}".format(self)
		if self.startdelim != "<?":
			s += " startdelim={0.startdelim!r}".format(self)
		if self.enddelim != "?>":
			s += " enddelim={0.enddelim!r}".format(self)
		if self.content:
			s + " ..."
		return s + " at {:#x}>".format(id(self))

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text("<{0.__class__.__module__}.{0.__class__.__qualname__} ... at {1:#x}>".format(self, id(self)))
		else:
			with p.group(4, "<{0.__class__.__module__}.{0.__class__.__qualname__}".format(self), ">"):
				p.breakable()
				p.text("name=")
				p.pretty(self.name)
				p.breakable()
				p.text("keepws=")
				p.pretty(self.keepws)
				if self.startdelim != "<?":
					p.breakable()
					p.text("startdelim=")
					p.pretty(self.startdelim)
				if self.enddelim != "?>":
					p.breakable()
					p.text("enddelim=")
					p.pretty(self.enddelim)
				for node in self.content:
					p.breakable()
					p.pretty(node)
				p.breakable()
				p.text("at {:#x}".format(id(self)))


###
### Helper classes/functions used at runtime
###

def _makedict(*items):
	result = {}
	for item in items:
		if len(item) == 1:
			result.update(item[0])
		else:
			result[item[0]] = item[1]
	return result


def _formatnestednameul4(name):
	if isinstance(name, str):
		return name
	elif len(name) == 1:
		return "({},)".format(_formatnestednameul4(name[0]))
	else:
		return "({})".format(", ".join(_formatnestednameul4(name) for name in name))


def _unpackvar(vars, name, value):
	if isinstance(name, str):
		vars[name] = value
	else:
		if len(name) > len(value):
			raise TypeError("too many values to unpack (expected {})".format(len(name)))
		elif len(name) < len(value):
			raise TypeError("need more than {} value{} to unpack)".format(len(values), "ss" if len(values) != 1 else ""))
		for (name, value) in zip(name, value):
			_unpackvar(vars, name, value)
