# -*- coding: utf-8 -*-

## Copyright 2008 by LivingLogic AG, Bayreuth/Germany
## Copyright 2008 by Walter Dörwald
##
## All Rights Reserved
##
## See ll/__init__.py for the license


from __future__ import division

"""
:mod:`ll.ul4c` provides templating for XML/HTML as well as any other text-based
format. A template defines placeholders for data output and basic logic (like
loops and conditional blocks), that define how the final rendered output will
look.

:mod:`ll.ul4c` compiles a template to a bytecode format, which makes it possible
to implement renderers for these templates in multiple programming languages.
"""

__docformat__ = "reStructuredText"


import marshal, re, StringIO

from ll import spark


###
### Location information
###

class Location(object):
	"""
	A :class:`Location` object contains information about the location of a
	template tag.
	"""
	__slots__ = ("source", "type", "starttag", "endtag", "startcode", "endcode")

	def __init__(self, source, type, starttag, endtag, startcode, endcode):
		"""
		Create a new :class:`Location` object. The arguments have the following
		meaning:

		:var:`source`
			The complete source string

		:var:`type`
			The tag type (i.e. ``"for"``, ``"if"``, etc.)

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

	def __str__(self):
		lastlinefeed = self.source.rfind("\n", 0, self.starttag)
		if lastlinefeed >= 0:
			line = self.source.count("\n", 0, self.starttag)+1
			col = self.starttag - lastlinefeed
		else:
			line = 1
			col = self.starttag + 1
		return "%r at %d (line %d, col %d)" % (self.tag, self.starttag+1, line, col)


###
### Exceptions
###

class Error(Exception):
	"""
	base class of all exceptions.
	"""
	def __init__(self, exception=None):
		self.location = None
		self.exception = exception

	def __str__(self):
		return self.format(str(self.exception) if self.exception is not None else "error")

	def decorate(self, location):
		self.location = location
		return self

	def format(self, message):
		if self.exception is not None:
			name = self.exception.__class__.__name__
			module = self.exception.__class__.__module__
			if module != "exceptions":
				name = "%s.%s" % (module, name)
			if self.location is not None:
				return "%s in %s: %s" % (name, self.location, message)
			else:
				return "%s: %s" % (name, message)
		else:
			if self.location is not None:
				return "in %s: %s" % (self.location, message)
			else:
				return message


class LexicalError(Error):
	def __init__(self, start, end, input):
		Error.__init__(self)
		self.start = start
		self.end = end
		self.input = input

	def __str__(self):
		return self.format("Unmatched input %r" % self.input)


class SyntaxError(Error):
	def __init__(self, token):
		Error.__init__(self)
		self.token = token

	def __str__(self):
		return self.format("Lexical error near %r" % str(self.token))


class UnterminatedStringError(Error):
	"""
	Exception that is raised by the parser when a string constant is not
	terminated.
	"""
	def __str__(self):
		return self.format("Unterminated string")


class BlockError(Error):
	"""
	Exception that is raised by the compiler when an illegal block structure is
	detected (e.g. an ``endif`` without a previous ``if``).
	"""

	def __init__(self, message):
		Error.__init__(self)
		self.message = message

	def __str__(self):
		return self.format(self.message)


class UnknownFunctionError(Error):
	"""
	Exception that is raised by the renderer if the function to be executed by
	the ``callfunc0``, ``callfunc1``, ``callfunc2`` or ``callfunc3`` opcodes is
	unknown.
	"""

	def __init__(self, funcname):
		Error.__init__(self)
		self.funcname = funcname

	def __str__(self):
		return self.format("function %r unknown" % self.funcname)


class UnknownMethodError(Error):
	"""
	Exception that is raised by the renderer if the method to be executed by the
	``callmeth0``, ``callmeth1``, ``callmeth2``  or ``callmeth3`` opcodes is
	unknown.
	"""

	def __init__(self, methname):
		Error.__init__(self)
		self.methname = methname

	def __str__(self):
		return self.format("method %r unknown" % self.methname)


class UnknownOpcodeError(Error):
	"""
	Exception that is raised when an unknown opcode is encountered by the renderer.
	"""

	def __init__(self, opcode):
		Error.__init__(self)
		self.opcode = opcode

	def __str__(self):
		return self.format("opcode %r unknown" % self.opcode)


class OutOfRegistersError(Error):
	"""
	Exception that is raised by the compiler when there are no more free
	registers. This might happen with very complex expressions in tag code.
	"""

	def __str__(self):
		return self.format("out of registers")


###
### opcode class
###

class Opcode(object):
	"""
	An :class:`Opcode` stores an opcode. The type of opcode is stored in the
	:attr:`code` attribute. Furthermore each opcode has up to five register
	specifications (for the source or targets of the operation) in the attributes
	:attr:`r1`, :attr:`r2`, :attr:`r3`, :attr:`r4` and :attr:`r5`. If the opcode
	requires an additional argument (like a variable name or the value of a
	constant) this will be stored in the :attr:`arg` attribute.

	The following opcodes are available:

	:const:`None`:
		Print text. The text is available from ``location.code``.

	``"print"``:
		Print the content of register :attr:`r1`. (If the object in the register
      is not a string, it will be converted to a string first.)

	``"loadnone"``:
		Load the constant :const:`None`.

	``"loadfalse"``:
		Load the constant :const:`False`.

	``"loadtrue"``:
		Load the constant :const:`True`.

	``"loadstr"``:
		Load the string :attr:`arg` into the register :attr:`r1`.

	``"loadint"``:
		Load the integer value :attr:`arg` into the register :attr:`r1`.

	``"loadfloat"``:
		Load the float value :attr:`arg` into the register :attr:`r1`.

	``"loadvar"``:
		Load the variable named :attr:`arg` into the register :attr:`r1`.

	``"storevar"``:
		Store the content of register :attr:`r1` in the variable named :attr:`arg`.

	``"addvar"``:
		Add the content of register :attr:`r1` to the variable named :attr:`arg`.

	``"for"``:
		Start a loop over the object in the register :attr:`r2` and store the
		object from each loop iteration in the register :attr:`r1`.

	``"endfor"``:
		Ends the innermost running ``for`` loop.

	``"if"``:
		Starts a conditional block. If the objects in the register :attr:`r1` is
		true the block will be executed. The "block" consists of all opcodes after
		the ``if`` upto the matching ``else`` or ``endif`` opcode.

	``"else"``:
		Start the else branch of the previous ``if``.

	``"endif"``:
		End a conditional block.

	``"getattr"``:
		Get the attribute named :attr:`arg` from the object in register :attr:`r2`
		and store it in register :attr:`r1`.

	``"getitem"``:
		Get an item from the object in register :attr:`r2`. If this object is a
		list the object in register :attr:`r3` will be used as the index. If it is
		a dictionary :attr:`r3` will be used as the key. The result will be stored
		in register :attr:`r1`.

	``"getslice12"``:
		Get an slice from the object in register :attr:`r2`. The object in
		register :attr:`r3` (which must be an ``int`` or :const:`None`) specifies
		the start index, If this object in register :attr:`r4` specifies the end
		index. The result will be stored in register :attr:`r1`.

	``"getslice1"``:
		Similar to ``getslice12`` except that the end index is always the length
		of the object.

	``"getslice2"``:
		Similar to ``getslice12`` except that the start index is always 0 and the
		end index is in register :attr:`r3`.

	``"getslice"``:
		Similar to ``getslice12`` except that the start index is always 0 and the
		end index alywas the length of the object.

	``"not"``:
		Invert the truth value of the object in register :attr:`r2` and stores the
		resulting bool in the register :attr:`r1`.

	``"equals"``:
		Compare the objects in register :attr:`r2` and :attr:`r3` and store
		``True`` in the register :attr:`r1` if they are equal, ``False`` otherwise.

	``"notequals"``:
		Compare the objects in register :attr:`r2` and :attr:`r3` and store
		``False`` in the register :attr:`r1` if they are equal, ``True`` otherwise.

	``"contains"``:
		Test whether the object in register :attr:`r3` contains the object in
		register :attr:`r2` (either as a key if it's a dictionary or as an item
		if it's a list or as a substring if it's a string) and store ``True`` into
		the register :attr:`r1` if it does, ``False`` otherwise.

	``"notcontains"``:
		Test whether the object in register :attr:`r3` contains the object in
		register :attr:`r2` (either as a key if it's a dictionary or as an item
		if it's a list or as a substring if it's a string) and store ``False`` into
		the register :attr:`r1` if it does, ``True`` otherwise.

	``"or"``:
		Check the truth value of two object in registers :attr:`r2` and :attr:`r3`
		and store :attr:`r2` in the register :attr:`r1` if it is true, :attr:`r3`
		otherwise).

	``"and"``:
		Check the truth value of two object in registers :attr:`r2` and :attr:`r3`
		and store :attr:`r3` in the register :attr:`r1` if :attr:`r2` is true,
		:attr:`r3` otherwise).

	``"mod"``:
		Does a modulo operation: Calculates :attr:`r2` modulo :attr:`r3` and stores
		the result in the register :attr:`r1`.

	``"callfunc0"``:
		Call the function named :attr:`arg` without any arguments and store the
		return value in register :attr:`r1`.

	``"callfunc1"``:
		Call the function named :attr:`arg` with the content of register :attr:`r2`
		as an argument and store the return value in register :attr:`r1`.

	``"callfunc2"``:
		Call the function named :attr:`arg` with the contents of register
		:attr:`r2` and :attr:`r3` as the two arguments and store the return value
		in register :attr:`r1`.

	``"callfunc3"``:
		Call the function named :attr:`arg` with the contents of register
		:attr:`r2`, :attr:`r3` and :attr:`r4` as the three arguments and store
		the return value in register :attr:`r1`.

	``"callmeth0"``:
		Call the method named :attr:`arg` on the object in register :attr:`r2`
		and store the return value in register :attr:`r1`.

	``"callmeth1"``:
		Call the method named :attr:`arg` on the object in register :attr:`r2`
		using the object in register :attr:`r3` as to only argument and store the
		return value in register :attr:`r1`.

	``"callmeth2"``:
		Call the method named :attr:`arg` on the object in register :attr:`r2`
		using the objects in register :attr:`r3` and :attr:`r4` as arguments and
		store the return value in register :attr:`r1`.

	``"callmeth3"``:
		Call the method named :attr:`arg` on the object in register :attr:`r2`
		using the objects in register :attr:`r3`, :attr:`r4` and :attr:`r5` as
		arguments and store the return value in register :attr:`r1`.

	``"render"``:
		Render the template whose name is in the attribute :attr:`arg`. The
		content of register :attr:`r1` will be passed as the data object to the
		template.
	"""
	__slots__ = ("code", "r1", "r2", "r3", "r4", "r5", "arg", "location", "jump")

	def __init__(self, code, r1=None, r2=None, r3=None, r4=None, r5=None, arg=None, location=None):
		self.code = code
		self.r1 = r1
		self.r2 = r2
		self.r3 = r3
		self.r4 = r4
		self.r5 = r5
		self.arg = arg
		self.location = location
		self.jump = None

	def __repr__(self):
		v = ["<", self.__class__.__name__, " code=%r" % self.code]
		for attrname in ("r1", "r2", "r3", "r4", "r5", "arg"):
			attr = getattr(self, attrname)
			if attr is not None:
				v.append(" %s=%r" % (attrname, attr))
		if self.code is None:
			v.append(" text=%r" % self.location.code)
		v.append(" at 0x%x>" % id(self))
		return "".join(v)

	def __str__(self):
		if self.code is None:
			return "print %r" % self.location.code
		elif self.code == "print":
			return "print r%r" % self.r1
		elif self.code == "loadnone":
			return "r%r = None" % self.r1
		elif self.code == "loadfalse":
			return "r%r = False" % self.r1
		elif self.code == "loadtrue":
			return "r%r = True" % self.r1
		elif self.code == "loadstr":
			return "r%r = %r" % (self.r1, self.arg)
		elif self.code == "loadint":
			return "r%r = %s" % (self.r1, self.arg)
		elif self.code == "loadfloat":
			return "r%r = %s" % (self.r1, self.arg)
		elif self.code == "loadvar":
			return "r%r = vars[%r]" % (self.r1, self.arg)
		elif self.code == "storevar":
			return "vars[%r] = r%r" % (self.arg, self.r1)
		elif self.code == "addvar":
			return "vars[%r] += r%r" % (self.arg, self.r1)
		elif self.code == "subvar":
			return "vars[%r] -= r%r" % (self.arg, self.r1)
		elif self.code == "mulvar":
			return "vars[%r] *= r%r" % (self.arg, self.r1)
		elif self.code == "truedivvar":
			return "vars[%r] /= r%r" % (self.arg, self.r1)
		elif self.code == "floordivvar":
			return "vars[%r] //= r%r" % (self.arg, self.r1)
		elif self.code == "modvar":
			return "vars[%r] %%= r%r" % (self.arg, self.r1)
		elif self.code == "delvar":
			return "del vars[%r]" % self.arg
		elif self.code == "for":
			return "for r%r in r%r" % (self.r1, self.r2)
		elif self.code == "endfor":
			return "endfor"
		elif self.code == "if":
			return "if r%r" % self.r1
		elif self.code == "else":
			return "else"
		elif self.code == "endif":
			return "endif"
		elif self.code == "getattr":
			return "r%r = getattr(r%r, %r)" % (self.r1, self.r2, self.arg)
		elif self.code == "getitem":
			return "r%r = r%r[r%r]" % (self.r1, self.r2, self.r3)
		elif self.code == "getslice":
			return "r%r = r%r[:]" % (self.r1, self.r2)
		elif self.code == "getslice1":
			return "r%r = r%r[r%r:]" % (self.r1, self.r2, self.r3)
		elif self.code == "getslice2":
			return "r%r = r%r[:r%r]" % (self.r1, self.r2, self.r4)
		elif self.code == "getslice12":
			return "r%r = r%r[r%r:r%r]" % (self.r1, self.r2, self.r3, self.r4)
		elif self.code == "not":
			return "r%r = not r%r" % (self.r1, self.r2)
		elif self.code == "equals":
			return "r%r = r%r == r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "notequals":
			return "r%r = r%r != r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "contains":
			return "r%r = r%r in r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "notcontains":
			return "r%r = r%r not in r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "add":
			return "r%r = r%r + r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "sub":
			return "r%r = r%r - r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "mul":
			return "r%r = r%r * r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "floordiv":
			return "r%r = r%r // r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "trueiv":
			return "r%r = r%r / r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "and":
			return "r%r = r%r and r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "or":
			return "r%r = r%r or r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "mod":
			return "r%r = r%r %% r%r" % (self.r1, self.r2, self.r3)
		elif self.code == "callfunc0":
			return "r%r = %s()" % (self.r1, self.arg)
		elif self.code == "callfunc1":
			return "r%r = %s(r%r)" % (self.r1, self.arg, self.r2)
		elif self.code == "callfunc2":
			return "r%r = %s(r%r, r%r)" % (self.r1, self.arg, self.r2, self.r3)
		elif self.code == "callfunc3":
			return "r%r = %s(r%r, r%r, r%r)" % (self.r1, self.arg, self.r2, self.r3, self.r4)
		elif self.code == "callmeth0":
			return "r%r = r%r.%s()" % (self.r1, self.r2, self.arg)
		elif self.code == "callmeth1":
			return "r%r = r%r.%s(r%r)" % (self.r1, self.r2, self.arg, self.r3)
		elif self.code == "callmeth2":
			return "r%r = r%r.%s(r%r, r%r)" % (self.r1, self.r2, self.arg, self.r3, self.r4)
		elif self.code == "callmeth3":
			return "r%r = r%r.%s(r%r, r%r, r%r)" % (self.r1, self.r2, self.arg, self.r3, self.r4, self.r5)
		elif self.code == "render":
			return "render %s(r%r)" % (self.arg, self.r1)
		else:
			raise UnknownOpcodeError(self.code)


class Template(object):
	def __init__(self):
		self.startdelim = None
		self.enddelim = None
		self.source = None
		self.opcodes = None
		# The following is used for converting the opcodes back to executable Python code
		self._pythonfunction = None

	@classmethod
	def loads(cls, data):
		def _readint(term):
			i = 0
			while True:
				c = stream.read(1)
				if c.isdigit():
					i = 10*i+int(c)
				elif c == term:
					return i
				else:
					raise ValueError("invalid terminator, expected %r, got %r" % (term, c))

		def _readstr(term1, term0):
			i = 0
			while True:
				c = stream.read(1)
				if c.isdigit():
					i = 10*i+int(c)
				elif c == term1:
					break
				elif c == term0:
					return None
				else:
					raise ValueError("invalid terminator, expected %r or %r, got %r" % (term1, term0, c))
			s = stream.read(i)
			if len(s) != i:
				raise ValueError("short read")
			return s

		def _readspec():
			c = stream.read(1)
			if c == "-":
				return None
			elif c.isdigit():
				return int(c)
			else:
				raise ValueError("invalid register spec %r" % c)

		def _readcr():
			c = stream.read(1)
			if c != "\n":
				raise ValueError("invalid linefeed %r" % c)

		self = cls()
		stream = StringIO.StringIO(data)
		header = stream.readline()
		header = header.rstrip()
		if header != "ul4":
			raise ValueError("invalid header, expected 'ul4', got %r" % header)
		version = stream.readline()
		version = version.rstrip()
		if version != "1":
			raise ValueError("invalid version, expected 1 got, %r" % version)
		self.startdelim = _readstr(u"<", u"[")
		_readcr()
		self.enddelim = _readstr(u">", u"]")
		_readcr()
		self.source = _readstr("'", '"')
		self.opcodes = []
		_readcr()
		count = _readint(u"#")
		_readcr()
		location = None
		while count:
			r1 = _readspec()
			r2 = _readspec()
			r3 = _readspec()
			r4 = _readspec()
			r5 = _readspec()
			code = _readstr(":", ".")
			arg = _readstr(";", ",")
			locspec = stream.read(1)
			if locspec == u"^":
				if location is None:
					raise ValueError("no previous location")
			elif locspec == u"*":
				location = Location(self.source, _readstr("=", "-"), _readint("("), _readint(")"), _readint("{"), _readint("}"))
			else:
				raise ValueError("invalid location spec %r" % locspec)
			_readcr()
			count -= 1
			self.opcodes.append(Opcode(code, r1, r2, r3, r4, r5, arg, location))
		return self

	@classmethod
	def load(cls, stream):
		return cls.loads(stream.read())

	def iterdump(self):
		def _writeint(term, number):
			yield unicode(number)
			yield term

		def _writestr(term1, term0, string):
			if string:
				yield str(len(string))
			if string is None:
				yield term0
			else:
				yield term1
				yield string

		yield "ul4\n1\n"
		for p in _writestr("<", "[", self.startdelim): yield p
		yield "\n"
		for p in _writestr(">", "]", self.enddelim): yield p
		yield "\n"
		for p in _writestr("'", '"', self.source): yield p
		yield "\n"
		for p in _writeint("#", len(self.opcodes)): yield p
		yield "\n"
		lastlocation = None
		for opcode in self.opcodes:
			yield str(opcode.r1) if opcode.r1 is not None else u"-"
			yield str(opcode.r2) if opcode.r2 is not None else u"-"
			yield str(opcode.r3) if opcode.r3 is not None else u"-"
			yield str(opcode.r4) if opcode.r4 is not None else u"-"
			yield str(opcode.r5) if opcode.r5 is not None else u"-"
			for p in _writestr(":", ".", opcode.code): yield p
			for p in _writestr(";", ",", opcode.arg): yield p
			if opcode.location is not lastlocation:
				lastlocation = opcode.location
				yield u"*"
				for p in _writestr("=", "-", lastlocation.type): yield p
				for p in _writeint("(", lastlocation.starttag): yield p
				for p in _writeint(")", lastlocation.endtag): yield p
				for p in _writeint("{", lastlocation.startcode): yield p
				for p in _writeint("}", lastlocation.endcode): yield p
			else:
				yield "^"
			yield "\n"

	def dump(self, stream):
		for part in self.iterdump():
			stream.write(part)

	def dumps(self):
		return ''.join(self.iterdump())

	def pythonsource(self, function=None):
		indent = 0
		output = []

		def _code(code):
			output.append("%s%s" % ("\t"*indent, code))

		if function is not None:
			_code("def %s(data, templates={}):" % function)
			indent += 1
		_code("import sys, marshal")
		_code("from ll.misc import xmlescape")
		_code("from ll import ul4c")
		_code("variables = dict(data=data)")
		_code("source = %r" % self.source)
		locations = tuple((oc.location.type, oc.location.starttag, oc.location.endtag, oc.location.startcode, oc.location.endcode) for oc in self.opcodes)
		locations = marshal.dumps(locations)
		_code("locations = marshal.loads(%r)" % locations)
		_code("".join("reg%d = " % i for i in xrange(10)) + "None")

		_code("try:")
		indent += 1
		_code("startline = sys._getframe().f_lineno+1") # The source line of the first opcode
		try:
			lastopcode = None
			for opcode in self.opcodes:
				# The following code ensures that each opcode outputs exactly one source code line
				# This makes it possible in case of an error to find out which opcode produced the error
				if opcode.code is None:
					_code("yield %r" % opcode.location.code)
				elif opcode.code == "loadstr":
					_code("reg%d = %r" % (opcode.r1, opcode.arg))
				elif opcode.code == "loadint":
					_code("reg%d = %s" % (opcode.r1, opcode.arg))
				elif opcode.code == "loadfloat":
					_code("reg%d = %s" % (opcode.r1, opcode.arg))
				elif opcode.code == "loadnone":
					_code("reg%d = None" % opcode.r1)
				elif opcode.code == "loadfalse":
					_code("reg%d = False" % opcode.r1)
				elif opcode.code == "loadtrue":
					_code("reg%d = True" % opcode.r1)
				elif opcode.code == "loadvar":
					_code("reg%d = variables[%r]" % (opcode.r1, opcode.arg))
				elif opcode.code == "storevar":
					_code("variables[%r] = reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "addvar":
					_code("variables[%r] += reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "subvar":
					_code("variables[%r] -= reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "mulvar":
					_code("variables[%r] *= reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "truedivvar":
					_code("variables[%r] /= reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "floordivvar":
					_code("variables[%r] //= reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "modvar":
					_code("variables[%r] %%= reg%d" % (opcode.arg, opcode.r1))
				elif opcode.code == "delvar":
					_code("del variables[%r]" % opcode.arg)
				elif opcode.code == "getattr":
					_code("reg%d = reg%d[%r]" % (opcode.r1, opcode.r2, opcode.arg))
				elif opcode.code == "getitem":
					_code("reg%d = reg%d[reg%d]" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "getslice12":
					_code("reg%d = reg%d[reg%d:reg%d]" % (opcode.r1, opcode.r2, opcode.r3, opcode.r4))
				elif opcode.code == "getslice1":
					_code("reg%d = reg%d[reg%d:]" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "getslice2":
					_code("reg%d = reg%d[:reg%d]" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "getslice":
					_code("reg%d = reg%d[:]" % (opcode.r1, opcode.r2))
				elif opcode.code == "print":
					_code("if reg%d is not None: yield unicode(reg%d)" % (opcode.r1, opcode.r1))
				elif opcode.code == "for":
					_code("for reg%d in reg%d:" % (opcode.r1, opcode.r2))
					indent += 1
				elif opcode.code == "endfor":
					# we don't have to check for empty loops here, as a ``<?for?>`` tag always generates at least one ``storevar`` opcode inside the loop
					indent -= 1
					_code("# end for")
				elif opcode.code == "not":
					_code("reg%d = not reg%d" % (opcode.r1, opcode.r2))
				elif opcode.code == "neg":
					_code("reg%d = -reg%d" % (opcode.r1, opcode.r2))
				elif opcode.code == "contains":
					_code("reg%d = reg%d in reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "notcontains":
					_code("reg%d = reg%d not in reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "equals":
					_code("reg%d = reg%d == reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "notequals":
					_code("reg%d = reg%d != reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "add":
					_code("reg%d = reg%d + reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "sub":
					_code("reg%d = reg%d - reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "mul":
					_code("reg%d = reg%d * reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "floordiv":
					_code("reg%d = reg%d // reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "truediv":
					_code("reg%d = reg%d / reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "and":
					_code("reg%d = reg%d and reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "or":
					_code("reg%d = reg%d or reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "mod":
					_code("reg%d = reg%d %% reg%d" % (opcode.r1, opcode.r2, opcode.r3))
				elif opcode.code == "callfunc0":
					raise UnknownFunctionError(opcode.arg)
				elif opcode.code == "callfunc1":
					if opcode.arg == "xmlescape":
						_code("reg%d = xmlescape(unicode(reg%d)) if reg%d is not None else u''" % (opcode.r1, opcode.r2, opcode.r2))
					elif opcode.arg == "str":
						_code("reg%d = unicode(reg%d) if reg%d is not None else u''" % (opcode.r1, opcode.r2, opcode.r2))
					elif opcode.arg == "int":
						_code("reg%d = int(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "bool":
						_code("reg%d = bool(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "len":
						_code("reg%d = len(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "enumerate":
						_code("reg%d = enumerate(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "isnone":
						_code("reg%d = reg%d is None" % (opcode.r1, opcode.r2))
					elif opcode.arg == "isstr":
						_code("reg%d = isinstance(reg%d, basestring)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "isint":
						_code("reg%d = isinstance(reg%d, (int, long)) and not isinstance(reg%d, bool)" % (opcode.r1, opcode.r2, opcode.r2))
					elif opcode.arg == "isfloat":
						_code("reg%d = isinstance(reg%d, float)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "isbool":
						_code("reg%d = isinstance(reg%d, bool)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "islist":
						_code("reg%d = isinstance(reg%d, (list, tuple))" % (opcode.r1, opcode.r2))
					elif opcode.arg == "isdict":
						_code("reg%d = isinstance(reg%d, dict)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "repr":
						_code("reg%d = unicode(repr(reg%d))" % (opcode.r1, opcode.r2))
					elif opcode.arg == "chr":
						_code("reg%d = unichr(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "ord":
						_code("reg%d = ord(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "hex":
						_code("reg%d = hex(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "oct":
						_code('reg%d = ul4c._oct(reg%d)' % (opcode.r1, opcode.r2))
					elif opcode.arg == "bin":
						_code('reg%d = ul4c._bin(reg%d)' % (opcode.r1, opcode.r2))
					elif opcode.arg == "sorted":
						_code("reg%d = sorted(reg%d)" % (opcode.r1, opcode.r2))
					elif opcode.arg == "range":
						_code("reg%d = xrange(reg%d)" % (opcode.r1, opcode.r2))
					else:
						raise UnknownFunctionError(opcode.arg)
				elif opcode.code == "callfunc2":
					if opcode.arg == "range":
						_code("reg%d = xrange(reg%d, reg%d)" % (opcode.r1, opcode.r2, opcode.r3))
					else:
						raise UnknownFunctionError(opcode.arg)
				elif opcode.code == "callfunc3":
					if opcode.arg == "range":
						_code("reg%d = xrange(reg%d, reg%d, reg%d)" % (opcode.r1, opcode.r2, opcode.r3, opcode.r4))
					else:
						raise UnknownFunctionError(opcode.arg)
				elif opcode.code == "callmeth0":
					if opcode.arg in ("split", "rsplit", "strip", "lstrip", "rstrip", "upper", "lower"):
						_code("reg%d = reg%d.%s()" % (opcode.r1, opcode.r2, opcode.arg))
					elif opcode.arg == "items":
						_code("reg%d = reg%d.iteritems()" % (opcode.r1, opcode.r2))
					else:
						raise UnknownMethodError(opcode.arg)
				elif opcode.code == "callmeth1":
					if opcode.arg in ("split", "rsplit", "strip", "lstrip", "rstrip", "startswith", "endswith", "find"):
						_code("reg%d = reg%d.%s(reg%d)" % (opcode.r1, opcode.r2, opcode.arg, opcode.r3))
					else:
						raise UnknownMethodError(opcode.arg)
				elif opcode.code == "callmeth2":
					if opcode.arg in ("split", "rsplit", "find"):
						_code("reg%d = reg%d.%s(reg%d, reg%d)" % (opcode.r1, opcode.r2, opcode.arg, opcode.r3, opcode.r4))
					else:
						raise UnknownMethodError(opcode.arg)
				elif opcode.code == "callmeth3":
					if opcode.arg == "find":
						_code("reg%d = reg%d.%s(reg%d, reg%d, reg%d)" % (opcode.r1, opcode.r2, opcode.arg, opcode.r3, opcode.r4, opcode.r5))
					else:
						raise UnknownMethodError(opcode.arg)
				elif opcode.code == "if":
					_code("if reg%d:" % opcode.r1)
					indent += 1
				elif opcode.code == "else":
					if lastopcode == "if":
						output[-1] += " pass"
					indent -= 1
					_code("else:")
					indent += 1
				elif opcode.code == "endif":
					if lastopcode in ("if", "else"):
						output[-1] += " pass"
					indent -= 1
					_code("# end if")
				elif opcode.code == "render":
					_code("for chunk in templates[%r](reg%d, templates): yield chunk" % (opcode.arg, opcode.r1))
				else:
					raise UnknownOpcodeError(opcode.code)
				lastopcode = opcode.code
		except Error, exc:
			exc.decorate(opcode.location)
			raise
		except Exception, exc:
			raise Error(exc).decorate(opcode.location)
		indent -= 1
		buildloc = "ul4c.Location(source, *locations[sys.exc_info()[2].tb_lineno-startline])"
		_code("except ul4c.Error, exc:")
		indent += 1
		_code("exc.decorate(%s)" % buildloc)
		_code("raise")
		indent -= 1
		_code("except Exception, exc:")
		indent += 1
		_code("raise ul4c.Error(exc).decorate(%s)" % buildloc)
		return "\n".join(output)

	def pythonfunction(self):
		if self._pythonfunction is None:
			code = self.pythonsource("render")
			ns = {}
			exec code.encode("utf-8") in ns
			self._pythonfunction = ns["render"]
		return self._pythonfunction

	def __call__(self, data=None, templates={}):
		return self.pythonfunction()(data, templates)

	def render(self, data=None, templates={}):
		return self.pythonfunction()(data, templates)

	def renders(self, data=None, templates={}):
		return "".join(self.render(data, templates))

	def format(self, indent="\t"):
		"""
		Format the list of opcodes. This is a generator yielding lines to be output
		(but without trailing newlines). :var:`indent` can be used to specify how
		to indent block (defaulting to ``"\\t"``).
		"""
		i = 0
		for opcode in self:
			if opcode.code in ("else", "endif", "endfor"):
				i -= 1
			if opcode.code in ("endif", "endfor"):
				yield "%s}" % (i*indent)
			elif opcode.code in ("for", "if"):
				yield "%s%s {" % (i*indent, opcode)
			elif opcode.code == "else":
				yield "%s} else {" % (i*indent)
			else:
				yield "%s%s" % (i*indent, opcode)
			if opcode.code in ("for", "if", "else"):
				i += 1

	def _tokenize(self, source, startdelim, enddelim):
		pattern = u"%s(print|code|for|if|elif|else|end|render)(\s*((.|\\n)*?)\s*)?%s" % (re.escape(startdelim), re.escape(enddelim))
		pos = 0
		for match in re.finditer(pattern, source):
			if match.start() != pos:
				yield Location(source, None, pos, match.start(), pos, match.start())
			yield Location(source, source[match.start(1):match.end(1)], match.start(), match.end(), match.start(3), match.end(3))
			pos = match.end()
		end = len(source)
		if pos != end:
			yield Location(source, None, pos, end, pos, end)

	def _allocreg(self):
		try:
			return self.registers.pop()
		except KeyError:
			raise OutOfRegistersError()

	def _freereg(self, register):
		self.registers.add(register)

	def opcode(self, name, r1=None, r2=None, r3=None, r4=None, r5=None, arg=None):
		self.opcodes.append(Opcode(name, r1, r2, r3, r4, r5, arg, self.location))

	def _compile(self, source, startdelim, enddelim):
		self.startdelim = startdelim
		self.enddelim = enddelim
		scanner = Scanner()
		parseexpr = ExprParser(scanner).compile
		parsestmt = StmtParser(scanner).compile
		parsefor = ForParser(scanner).compile
		parserender = RenderParser(scanner).compile

		# This stack stores for each nested for/foritem/if/elif/else the following information:
		# 1) Which construct we're in (i.e. "if" or "for")
		# For ifs:
		# 2) How many if's or elif's we have seen (this is used for simulating elif's via nested if's, for each additional elif, we have one more endif to add)
		# 3) Whether we've already seen the else
		stack = []

		self.source = source
		self.opcodes = []

		for location in self._tokenize(source, startdelim, enddelim):
			self.location = location
			try:
				if location.type is None:
					self.opcode(None)
				elif location.type == "print":
					r = parseexpr(self)
					self.opcode("print", r1=r)
				elif location.type == "code":
					parsestmt(self)
				elif location.type == "if":
					r = parseexpr(self)
					self.opcode("if", r1=r)
					stack.append(("if", 1, False))
				elif location.type == "elif":
					if not stack or stack[-1][0] != "if":
						raise BlockError("elif doesn't match any if")
					elif stack[-1][2]:
						raise BlockError("else already seen in elif")
					self.opcode("else")
					r = parseexpr(self)
					self.opcode("if", r1=r)
					stack[-1] = ("if", stack[-1][1]+1, False)
				elif location.type == "else":
					if not stack or stack[-1][0] != "if":
						raise BlockError("else doesn't match any if")
					elif stack[-1][2]:
						raise BlockError("duplicate else")
					self.opcode("else")
					stack[-1] = ("if", stack[-1][1], True)
				elif location.type == "end":
					if not stack:
						raise BlockError("not in any block")
					code = location.code
					if code:
						if code == "if":
							if stack[-1][0] != "if":
								raise BlockError("endif doesn't match any if")
						elif code == "for":
							if stack[-1][0] != "for":
								raise BlockError("endfor doesn't match any for")
						else:
							raise BlockError("illegal end value %r" % code)
					last = stack.pop()
					if last[0] == "if":
						for i in xrange(last[1]):
							self.opcode("endif")
					else: # last[0] == "for":
						self.opcode("endfor")
				elif location.type == "for":
					parsefor(self)
					stack.append(("for",))
				elif location.type == "render":
					parserender(self)
				else: # Can't happen
					raise ValueError("unknown tag %r" % location.type)
			except Error, exc:
				exc.decorate(location)
				raise
			except Exception, exc:
				raise Error(exc).decorate(location)
			finally:
				del self.location
		if stack:
			raise BlockError("unclosed blocks")

	def __str__(self):
		return "\n".join(self.format())

	def __unicode__(self):
		return u"\n".join(self.format())

	def __repr__(self):
		return "<%s.%s object with %d opcodes at 0x%x>" % (self.__class__.__module__, self.__class__.__name__, len(self.opcodes), id(self))


def compile(source, startdelim="<?", enddelim="?>"):
	template = Template()
	template._compile(source, startdelim, enddelim)
	return template

load = Template.load
loads = Template.loads


###
### Tokens and nodes for the AST
###

class Token(object):
	def __init__(self, start, end, type):
		self.start = start
		self.end = end
		self.type = type

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.type)

	def __str__(self):
		return self.type


class AST(object):
	"""
	Baseclass for all syntax tree nodes.
	"""

	def __init__(self, start, end):
		self.start = start
		self.end = end


class Const(AST):
	"""
	Common baseclass for all constants (used for type testing in constant folding)
	"""

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.start, self.end)

	def compile(self, template):
		r = template._allocreg()
		template.opcode("load%s" % self.type, r1=r)
		return r


class None_(Const):
	type = "none"
	value = None


class True_(Const):
	type = "true"
	value = True


class False_(Const):
	type = "false"
	value = False


class Value(Const):
	def __init__(self, start, end, value):
		Const.__init__(self, start, end)
		self.value = value

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.value)

	def compile(self, template):
		r = template._allocreg()
		template.opcode("load%s" % self.type, r1=r, arg=unicode(self.value))
		return r


class Int(Value):
	type = "int"


class Float(Value):
	type = "float"

	def compile(self, template):
		r = template._allocreg()
		template.opcode("load%s" % self.type, r1=r, arg=repr(self.value))
		return r


class Str(Value):
	type = "str"


class Name(AST):
	type = "name"

	def __init__(self, start, end, name):
		AST.__init__(self, start, end)
		self.name = name

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name)

	def compile(self, template):
		r = template._allocreg()
		template.opcode("loadvar", r1=r, arg=self.name)
		return r


class For(AST):
	def __init__(self, start, end, iter, cont):
		AST.__init__(self, start, end)
		self.iter = iter
		self.cont = cont

	def __repr__(self):
		return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.iter, self.cont)

	def compile(self, template):
		rc = self.cont.compile(template)
		ri = template._allocreg()
		template.opcode("for", r1=ri, r2=rc)
		if isinstance(self.iter, list):
			for (i, iter) in enumerate(self.iter):
				rii = template._allocreg()
				template.opcode("loadint", r1=rii, arg=str(i))
				template.opcode("getitem", r1=rii, r2=ri, r3=rii)
				template.opcode("storevar", r1=rii, arg=iter.name)
				template._freereg(rii)
		else:
			template.opcode("storevar", r1=ri, arg=self.iter.name)
		template._freereg(ri)
		template._freereg(rc)


class GetAttr(AST):
	def __init__(self, start, end, obj, attr):
		AST.__init__(self, start, end)
		self.obj = obj
		self.attr = attr

	def __repr__(self):
		return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.obj, self.attr)

	def compile(self, template):
		r = self.obj.compile(template)
		template.opcode("getattr", r1=r, r2=r, arg=self.attr.name)
		return r


class GetSlice12(AST):
	def __init__(self, start, end, obj, index1, index2):
		AST.__init__(self, start, end)
		self.obj = obj
		self.index1 = index1
		self.index2 = index2

	def __repr__(self):
		return "%s(%r, %r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.obj, self.index1, self.index2)

	def compile(self, template):
		r1 = self.obj.compile(template)
		r2 = self.index1.compile(template)
		r3 = self.index2.compile(template)
		template.opcode("getslice12", r1=r1, r2=r1, r3=r2, r4=r3)
		template._freereg(r2)
		template._freereg(r3)
		return r1


class Unary(AST):
	opcode = None

	def __init__(self, start, end, obj):
		AST.__init__(self, start, end)
		self.obj = obj

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.obj)

	def compile(self, template):
		r = self.obj.compile(template)
		template.opcode(self.opcode, r1=r, r2=r)
		return r


class GetSlice(Unary):
	opcode = "getslice"


class Not(Unary):
	opcode = "not"


class Neg(Unary):
	opcode = "neg"


class Binary(AST):
	opcode = None

	def __init__(self, start, end, obj1, obj2):
		AST.__init__(self, start, end)
		self.obj1 = obj1
		self.obj2 = obj2

	def __repr__(self):
		return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.obj1, self.obj2)

	def compile(self, template):
		r1 = self.obj1.compile(template)
		r2 = self.obj2.compile(template)
		template.opcode(self.opcode, r1=r1, r2=r1, r3=r2)
		template._freereg(r2)
		return r1


class GetItem(Binary):
	opcode = "getitem"


class GetSlice1(Binary):
	opcode = "getslice1"


class GetSlice2(Binary):
	opcode = "getslice2"


class Equal(Binary):
	opcode = "equals"


class NotEqual(Binary):
	opcode = "notequals"


class Contains(Binary):
	opcode = "contains"


class NotContains(Binary):
	opcode = "notcontains"


class Add(Binary):
	opcode = "add"


class Sub(Binary):
	opcode = "sub"


class Mul(Binary):
	opcode = "mul"


class FloorDiv(Binary):
	opcode = "floordiv"


class TrueDiv(Binary):
	opcode = "truediv"


class Or(Binary):
	opcode = "or"


class And(Binary):
	opcode = "and"


class Mod(Binary):
	opcode = "mod"


class ChangeVar(AST):
	opcode = None

	def __init__(self, start, end, name, value):
		AST.__init__(self, start, end)
		self.name = name
		self.value = value

	def __repr__(self):
		return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name, self.value)

	def compile(self, template):
		r = self.value.compile(template)
		template.opcode(self.opcode, r1=r, arg=self.name.name)
		template._freereg(r)


class StoreVar(ChangeVar):
	opcode = "storevar"


class AddVar(ChangeVar):
	opcode = "addvar"


class SubVar(ChangeVar):
	opcode = "subvar"


class MulVar(ChangeVar):
	opcode = "mulvar"


class TrueDivVar(ChangeVar):
	opcode = "truedivvar"


class FloorDivVar(ChangeVar):
	opcode = "floordivvar"


class ModVar(ChangeVar):
	opcode = "modvar"


class DelVar(AST):
	def __init__(self, start, end, name):
		AST.__init__(self, start, end)
		self.name = name

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name)

	def compile(self, template):
		template.opcode("delvar", arg=self.name.name)


class CallFunc(AST):
	def __init__(self, start, end, name, args):
		AST.__init__(self, start, end)
		self.name = name
		self.args = args

	def __repr__(self):
		if self.args:
			return "%s(%r, %r, %r, %s)" % (self.__class__.__name__, self.start, self.end, self.name, repr(self.args)[1:-1])
		else:
			return "%s(%r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name)

	def compile(self, template):
		if len(self.args) == 0:
			r = template._allocreg()
			template.opcode("callfunc0", r1=r, arg=self.name.name)
			return r
		elif len(self.args) > 3:
			raise ValueError("%d arguments not supported" % len(self.args))
		else:
			rs = [arg.compile(template) for arg in self.args]
			template.opcode("callfunc%d" % len(self.args), rs[0], *rs, **dict(arg=self.name.name)) # Replace **dict(arg=) with arg= in Python 2.6?
			for i in xrange(1, len(self.args)):
				template._freereg(rs[i])
			return rs[0]


class CallMeth(AST):
	def __init__(self, start, end, name, obj, args):
		AST.__init__(self, start, end)
		self.name = name
		self.obj = obj
		self.args = args

	def __repr__(self):
		if self.args:
			return "%s(%r, %r, %r, %r, %s)" % (self.__class__.__name__, self.start, self.end, self.name, self.obj, repr(self.args)[1:-1])
		else:
			return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name, self.obj)

	def compile(self, template):
		if len(self.args) > 3:
			raise ValueError("%d arguments not supported" % len(self.args))
		ro = self.obj.compile(template)
		rs = [arg.compile(template) for arg in self.args]
		template.opcode("callmeth%d" % len(self.args), r1=ro, r2=ro, *rs, **dict(arg=self.name.name))
		for r in rs:
			template._freereg(r)
		return ro


class Render(AST):
	def __init__(self, start, end, name, value):
		AST.__init__(self, start, end)
		self.name = name
		self.value = value

	def __repr__(self):
		return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.start, self.end, self.name, self.value)

	def compile(self, template):
		r = self.value.compile(template)
		template.opcode("render", r1=r, arg=self.name.name)
		template._freereg(r)


###
### Tokenizer
###

class Scanner(spark.Scanner):
	reflags = re.UNICODE

	def tokenize(self, location):
		self.collectstr = []
		self.rv = []
		self.start = 0
		try:
			spark.Scanner.tokenize(self, location.code)
			if self.mode != "default":
				raise UnterminatedStringError()
		except Error, exc:
			exc.decorate(location)
			raise
		except Exception, exc:
			raise Error(exc).decorate(location)
		return self.rv

	@spark.token("\\(|\\)|\\[|\\]|\\.|,|==|\\!=|=|\\+=|\\-=|\\*=|//=|/=|%=|%|:|\\+|-|\\*|//|/", "default")
	def token(self, start, end, s):
		self.rv.append(Token(start, end, s))

	@spark.token("[a-zA-Z_][\\w]*", "default")
	def name(self, start, end, s):
		if s in ("in", "not", "or", "and", "del"):
			self.rv.append(Token(start, end, s))
		elif s == "None":
			self.rv.append(None_(start, end))
		elif s == "True":
			self.rv.append(True_(start, end))
		elif s == "False":
			self.rv.append(False_(start, end))
		else:
			self.rv.append(Name(start, end, s))

	# We don't have negatve numbers, this is handled by constant folding in the AST for unary minus
	@spark.token("\\d+\\.\\d*([eE][+-]?\\d+)?", "default")
	@spark.token("\\d+(\\.\\d*)?[eE][+-]?\\d+", "default")
	def float(self, start, end, s):
		self.rv.append(Float(start, end, float(s)))

	@spark.token("0[xX][\\da-fA-F]+", "default")
	def hexint(self, start, end, s):
		self.rv.append(Int(start, end, int(s[2:], 16)))

	@spark.token("0[oO][0-7]+", "default")
	def octint(self, start, end, s):
		self.rv.append(Int(start, end, int(s[2:], 8)))

	@spark.token("0[bB][01]+", "default")
	def binint(self, start, end, s):
		self.rv.append(Int(start, end, int(s[2:], 2)))

	@spark.token("\\d+", "default")
	def int(self, start, end, s):
		self.rv.append(Int(start, end, int(s)))

	@spark.token("'", "default")
	def beginstr1(self, start, end, s):
		self.mode = "str1"
		self.start = start

	@spark.token('"', "default")
	def beginstr2(self, start, end, s):
		self.mode = "str2"
		self.start = start

	@spark.token("'", "str1")
	@spark.token('"', "str2")
	def endstr(self, start, end, s):
		self.rv.append(Str(self.start, end, "".join(self.collectstr)))
		self.collectstr = []
		self.mode = "default"

	@spark.token("\\s+", "default")
	def whitespace(self, start, end, s):
		pass

	@spark.token("\\\\\\\\", "str1", "str2")
	def escapedbackslash(self, start, end, s):
		self.collectstr.append("\\")

	@spark.token("\\\\'", "str1", "str2")
	def escapedapos(self, start, end, s):
		self.collectstr.append("'")

	@spark.token('\\\\"', "str1", "str2")
	def escapedquot(self, start, end, s):
		self.collectstr.append('"')

	@spark.token("\\\\a", "str1", "str2")
	def escapedbell(self, start, end, s):
		self.collectstr.append("\a")

	@spark.token("\\\\b", "str1", "str2")
	def escapedbackspace(self, start, end, s):
		self.collectstr.append("\b")

	@spark.token("\\\\f", "str1", "str2")
	def escapedformfeed(self, start, end, s):
		self.collectstr.append("\f")

	@spark.token("\\\\n", "str1", "str2")
	def escapedlinefeed(self, start, end, s):
		self.collectstr.append("\n")

	@spark.token("\\\\r", "str1", "str2")
	def escapedcarriagereturn(self, start, end, s):
		self.collectstr.append("\r")

	@spark.token("\\\\t", "str1", "str2")
	def escapedtab(self, start, end, s):
		self.collectstr.append("\t")

	@spark.token("\\\\v", "str1", "str2")
	def escapedverticaltab(self, start, end, s):
		self.collectstr.append("\v")

	@spark.token("\\\\e", "str1", "str2")
	def escapedescape(self, start, end, s):
		self.collectstr.append("\x1b")

	@spark.token("\\\\x[0-9a-fA-F]{2}", "str1", "str2")
	def escaped8bitchar(self, start, end, s):
		self.collectstr.append(unichr(int(s[2:], 16)))

	@spark.token("\\\\u[0-9a-fA-F]{4}", "str1", "str2")
	def escaped16bitchar(self, start, end, s):
		self.collectstr.append(unichr(int(s[2:], 16)))

	@spark.token(".|\\n", "str1", "str2")
	def text(self, start, end, s):
		self.collectstr.append(s)

	@spark.token("(.|\\n)+", "default", "str1", "str2")
	def default(self, start, end, s):
		raise LexicalError(start, end, s)

	def error(self, start, end, s):
		raise LexicalError(start, end, s)


###
### Parsers for different types of code
###

class ExprParser(spark.Parser):
	emptyerror = "expression required"
	start = "expr0"

	def __init__(self, scanner):
		spark.Parser.__init__(self)
		self.scanner = scanner

	def compile(self, template):
		location = template.location
		if not location.code:
			raise ValueError(self.emptyerror)
		template.registers = set(xrange(10))
		try:
			ast = self.parse(self.scanner.tokenize(location))
			return ast.compile(template)
		except Error, exc:
			exc.decorate(location)
			raise
		except Exception, exc:
			raise Error(exc).decorate(location)
		finally:
			del template.registers

	def typestring(self, token):
		return token.type

	def error(self, token):
		raise SyntaxError(token)

	def makeconst(self, start, end, value):
		if value is None:
			return None_(start, end)
		elif value is True:
			return True_(start, end)
		elif value is False:
			return False_(start, end)
		elif isinstance(value, int):
			return Int(start, end, value)
		elif isinstance(value, float):
			return Float(start, end, value)
		elif isinstance(value, basestring):
			return Str(start, end, value)
		else:
			raise TypeError("can't convert %r" % value)

	# To implement operator precedence, each expression rule has the precedence in its name. The highest precedence is 11 for atomic expressions.
	# Each expression can have only expressions as parts, which have the some or a higher precedence with two exceptions:
	#    1) Expressions where there's no ambiguity, like the index for a getitem/getslice or function/method arguments;
	#    2) Brackets, which can be used to boost the precedence of an expression to the level of an atomic expression.

	@spark.production('expr11 ::= none')
	@spark.production('expr11 ::= true')
	@spark.production('expr11 ::= false')
	@spark.production('expr11 ::= str')
	@spark.production('expr11 ::= int')
	@spark.production('expr11 ::= float')
	@spark.production('expr11 ::= name')
	def expr_atom(self, atom):
		return atom

	@spark.production('expr11 ::= ( expr0 )')
	def expr_bracket(self, _0, expr, _1):
		return expr

	@spark.production('expr10 ::= name ( )')
	def expr_callfunc0(self, name, _0, _1):
		return CallFunc(name.start, _1.end, name, [])

	@spark.production('expr10 ::= name ( expr0 )')
	def expr_callfunc1(self, name, _0, arg0, _1):
		return CallFunc(name.start, _1.end, name, [arg0])

	@spark.production('expr10 ::= name ( expr0 , expr0 )')
	def expr_callfunc2(self, name, _0, arg0, _1, arg1, _2):
		return CallFunc(name.start, _2.end, name, [arg0, arg1])

	@spark.production('expr10 ::= name ( expr0 , expr0 , expr0 )')
	def expr_callfunc3(self, name, _0, arg0, _1, arg1, _2, arg2, _3):
		return CallFunc(name.start, _3.end, name, [arg0, arg1, arg2])

	@spark.production('expr9 ::= expr9 . name')
	def expr_getattr(self, expr, _0, name):
		return GetAttr(expr.start, name.end, expr, name)

	@spark.production('expr9 ::= expr9 . name ( )')
	def expr_callmeth0(self, expr, _0, name, _1, _2):
		return CallMeth(expr.start, _2.end, name, expr, [])

	@spark.production('expr9 ::= expr9 . name ( expr0 )')
	def expr_callmeth1(self, expr, _0, name, _1, arg1, _2):
		return CallMeth(expr.start, _2.end, name, expr, [arg1])

	@spark.production('expr9 ::= expr9 . name ( expr0 , expr0 )')
	def expr_callmeth2(self, expr, _0, name, _1, arg1, _2, arg2, _3):
		return CallMeth(expr.start, _3.end, name, expr, [arg1, arg2])

	@spark.production('expr9 ::= expr9 . name ( expr0 , expr0 , expr0 )')
	def expr_callmeth3(self, expr, _0, name, _1, arg1, _2, arg2, _3, arg3, _4):
		return CallMeth(expr.start, _4.end, name, expr, [arg1, arg2, arg3])

	@spark.production('expr9 ::= expr9 [ expr0 ]')
	def expr_getitem(self, expr, _0, key, _1):
		if isinstance(expr, Const) and isinstance(key, Const): # Constant folding
			return self.makeconst(expr.start, _1.end, expr.value[key.value])
		return GetItem(expr.start, _1.end, expr, key)

	@spark.production('expr8 ::= expr8 [ expr0 : expr0 ]')
	def expr_getslice12(self, expr, _0, index1, _1, index2, _2):
		if isinstance(expr, Const) and isinstance(index1, Const) and isinstance(index2, Const): # Constant folding
			return self.makeconst(expr.start, _2.end, expr.value[index1.value:index1.value])
		return GetSlice12(expr.start, _2.end, expr, index1, index2)

	@spark.production('expr8 ::= expr8 [ expr0 : ]')
	def expr_getslice1(self, expr, _0, index1, _1, _2):
		if isinstance(expr, Const) and isinstance(index1, Const): # Constant folding
			return self.makeconst(expr.start, _2.end, expr.value[index1.value:])
		return GetSlice1(expr.start, _2.end, expr, index1)

	@spark.production('expr8 ::= expr8 [ : expr0 ]')
	def expr_getslice2(self, expr, _0, _1, index2, _2):
		if isinstance(expr, Const) and isinstance(index2, Const): # Constant folding
			return self.makeconst(expr.start, _2.end, expr.value[:index2.value])
		return GetSlice2(expr.start, _2.end, expr, index2)

	@spark.production('expr8 ::= expr8 [ : ]')
	def expr_getslice(self, expr, _0, _1, _2):
		if isinstance(expr, Const): # Constant folding
			return self.makeconst(expr.start, _2.end, expr.value[:])
		return GetSlice(expr.start, _2.end, expr)

	@spark.production('expr7 ::= - expr7')
	def expr_neg(self, _0, expr):
		if isinstance(expr, Const): # Constant folding
			return self.makeconst(_0.start, expr.end, -expr.value)
		return Neg(_0.start, expr.end, expr)

	@spark.production('expr6 ::= expr6 * expr6')
	def expr_mul(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value * obj2.value)
		return Mul(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr6 ::= expr6 // expr6')
	def expr_floordiv(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value // obj2.value)
		return FloorDiv(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr6 ::= expr6 / expr6')
	def expr_truediv(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value / obj2.value)
		return TrueDiv(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr6 ::= expr6 % expr6')
	def expr_mod(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value % obj2.value)
		return Mod(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr5 ::= expr5 + expr5')
	def expr_add(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value + obj2.value)
		return Add(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr5 ::= expr5 - expr5')
	def expr_sub(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value - obj2.value)
		return Sub(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr4 ::= expr4 == expr4')
	def expr_equal(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value == obj2.value)
		return Equal(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr4 ::= expr4 != expr4')
	def expr_notequal(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, obj1.value != obj2.value)
		return NotEqual(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr3 ::= expr3 in expr3')
	def expr_contains(self, obj, _0, container):
		if isinstance(obj, Const) and isinstance(container, Const): # Constant folding
			return self.makeconst(obj.start, container.end, obj.value in container.value)
		return Contains(obj.start, container.end, obj, container)

	@spark.production('expr3 ::= expr3 not in expr3')
	def expr_notcontains(self, obj, _0, _1, container):
		if isinstance(obj, Const) and isinstance(container, Const): # Constant folding
			return self.makeconst(obj.start, container.end, obj.value not in container.value)
		return NotContains(obj.start, container.end, obj, container)

	@spark.production('expr2 ::= not expr2')
	def expr_not(self, _0, expr):
		if isinstance(expr1, Const): # Constant folding
			return self.makeconst(_0.start, expr.end, not expr.value)
		return Not(_0.start, expr.end, expr)

	@spark.production('expr1 ::= expr1 and expr1')
	def expr_and(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, bool(obj1.value and obj2.value))
		return And(obj1.start, obj2.end, obj1, obj2)

	@spark.production('expr0 ::= expr0 or expr0')
	def expr_or(self, obj1, _0, obj2):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.start, obj2.end, bool(obj1.value or obj2.value))
		return Or(obj1.start, obj2.end, obj1, obj2)

	# These rules make operators of different precedences interoperable, by allowing an expression to "drop" its precedence.
	@spark.production('expr10 ::= expr11')
	@spark.production('expr9 ::= expr10')
	@spark.production('expr8 ::= expr9')
	@spark.production('expr7 ::= expr8')
	@spark.production('expr6 ::= expr7')
	@spark.production('expr5 ::= expr6')
	@spark.production('expr4 ::= expr5')
	@spark.production('expr3 ::= expr4')
	@spark.production('expr2 ::= expr3')
	@spark.production('expr1 ::= expr2')
	@spark.production('expr0 ::= expr1')
	def expr_dropprecedence(self, expr):
		return expr


class ForParser(ExprParser):
	emptyerror = "loop expression required"
	start = "for"
	
	@spark.production('for ::= name in expr0')
	def for0(self, iter, _0, cont):
		return For(iter.start, cont.end, iter, cont)

	@spark.production('for ::= ( name , ) in expr0')
	def for1(self, _0, iter, _1, _2, _3, cont):
		return For(_0.start, cont.end, [iter], cont)

	@spark.production('for ::= ( name , name ) in expr0')
	def for2a(self, _0, iter1, _1, iter2, _2, _3, cont):
		return For(_0.start, cont.end, [iter1, iter2], cont)

	@spark.production('for ::= ( name , name , ) in expr0')
	def for2b(self, _0, iter1, _1, iter2, _2, _3, _4, cont):
		return For(_0.start, cont.end, [iter1, iter2], cont)


class StmtParser(ExprParser):
	emptyerror = "statement required"
	start = "stmt"

	@spark.production('stmt ::= name = expr0')
	def stmt_assign(self, name, _0, value):
		return StoreVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name += expr0')
	def stmt_iadd(self, name, _0, value):
		return AddVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name -= expr0')
	def stmt_isub(self, name, _0, value):
		return SubVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name *= expr0')
	def stmt_imul(self, name, _0, value):
		return MulVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name /= expr0')
	def stmt_itruediv(self, name, _0, value):
		return TrueDivVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name //= expr0')
	def stmt_ifloordiv(self, name, _0, value):
		return FloorDivVar(name.start, value.end, name, value)

	@spark.production('stmt ::= name %= expr0')
	def stmt_imod(self, name, _0, value):
		return ModVar(name.start, value.end, name, value)

	@spark.production('stmt ::= del name')
	def stmt_del(self, _0, name):
		return DelVar(_0.start, name.end, name)


class RenderParser(ExprParser):
	emptyerror = "render statement required"
	start = "render"

	@spark.production('render ::= name ( expr0 )')
	def render(self, name, _1, expr, _2):
		return Render(name.start, _2.end, name, expr)


def _oct(value):
	"""
	Helper for the ``oct`` function.
	"""
	if value == 0:
		return "0o0"
	elif value < 0:
		return "-0o" + oct(value)[2:]
	else:
		return "0o" + oct(value)[1:]


def _bin(value):
	"""
	Helper for the ``bin`` function.
	"""
	if value == 0:
		return "0b0"
	if value < 0:
		value = -value
		prefix = "-0b"
	else:
		prefix = "0b"
	v = []
	while value:
		v.append(str(value&1))
		value >>= 1
	return prefix+"".join(v)[::-1]