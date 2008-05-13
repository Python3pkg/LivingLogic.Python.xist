# -*- coding: utf-8 -*-

## Copyright 2008 by LivingLogic AG, Bayreuth/Germany
## Copyright 2008 by Walter Dörwald
##
## All Rights Reserved
##
## See ll/__init__.py for the license


from __future__ import division

import re, StringIO

import spark


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
		return "%s at %d (line %d, col %d)" % (self.tag, self.starttag+1, line, col)


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
	def __init__(self, input):
		Error.__init__(self)
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
	Exception that is raised when a string constant is not terminated.
	"""
	def __str__(self):
		return self.format("Unterminated string")


class BlockError(Error):
	"""
	Exception that is raised when an illegal block structure is detected (e.g.
	an ``endif`` without a previous ``if``).
	"""

	def __init__(self, message):
		Error.__init__(self)
		self.message = message

	def __str__(self):
		return self.format(self.message)


class UnknownFunctionError(Error):
	"""
	Exception that is raised the function to be executed by the ``callfunc0``,
	``callfunc1`` or ``callfunc2`` opcodes is unknown to the renderer.
	"""

	def __init__(self, funcname):
		Error.__init__(self)
		self.funcname = funcname

	def __str__(self):
		return self.format("function %r unknown" % self.funcname)


class UnknownMethodError(Error):
	"""
	Exception that is raised the method to be executed by the ``callmeth0``,
	``callmeth1``, ``callmeth2``  or ``callmeth3`` opcodes is unknown to the
	renderer.
	"""

	def __init__(self, methname):
		Error.__init__(self)
		self.methname = methname

	def __str__(self):
		return self.format("method %r unknown" % self.methname)


class UnknownOpcodeError(Error):
	"""
	Exception that is raised when an unknown opcode is encountered.
	"""

	def __init__(self, opcode):
		Error.__init__(self)
		self.opcode = opcode

	def __str__(self):
		return self.format("opcode %r unknown" % self.opcode)


class OutOfRegistersError(Error):
	"""
	Exception that is raised when there are no more free registers
	(can't happen)
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
	specification (for the source or targets of the opcode) in the attributes
	:attr:`r1`, :attr:`r2`, :attr:`r3`, :attr:`r4` and :attr:`r5`. Furthermore
	if the opcode requires an additional argument (like a variable name or a
	string value) this will be stored in the :attr:`arg` attribute.

	The following types of opcodes are available:

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
		a dictionary :attr:`r3` will be used as the the key. The result will be
		stored in register :attr:`r1`.

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
		and store ``True`` in the register :attr:`r1` if one of them is true
		(``False`` otherwise).

	``"and"``:
		Check the truth value of two object in registers :attr:`r2` and :attr:`r3`
		and store ``True`` in the register :attr:`r1` if both of them are true
		(``False`` otherwise).

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
		v = ["<", self.__class__.__name__, " code=", self.code]
		for attrname in ("r1", "r2", "r3", "r4", "r5", "arg"):
			attr = getattr(self, attrname)
			if attr is not None:
				v.append(" %s=%r" % (attrname, attr))
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
		elif self.code == "callmeth0":
			return "r%r = r%r.%s()" % (self.r1, self.r2, self.arg)
		elif self.code == "callmeth1":
			return "r%r = r%r.%s(r%r)" % (self.r1, self.r2, self.arg, self.r3)
		elif self.code == "callmeth2":
			return "r%r = r%r.%s(r%r, r%r)" % (self.r1, self.r2, self.arg, self.r3, self.r4)
		elif self.code == "callmeth3":
			return "r%r = r%r.%s(r%r, r%r, r%r)" % (self.r1, self.r2, self.arg, self.r3, self.r4, self.r5)
		else:
			raise UnknownOpcodeError(self.code)


class Template(object):
	def __init__(self):
		self.source = None
		self.opcodes = None

	@classmethod
	def fromsrc(cls, source, startdelim="<?", enddelim="?>"):
		self = cls()
		self.source = source
		self.opcodes = list(cls._compile(source, startdelim, enddelim))
		return self

	@classmethod
	def frombin(cls, bin):
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

		def _readstr(term):
			i = 0
			while True:
				c = stream.read(1)
				if c.isdigit():
					i = 10*i+int(c)
				elif c == term:
					break
				elif c.lower() == term:
					return None
				else:
					raise ValueError("invalid terminator, expected %r, got %r" % (term, c))
			s = stream.read(i)
			if len(s) != i:
				raise ValueError("short read")
			return s

		def _readspec():
			c = stream.read(1)
			if c == u"-":
				return None
			elif c.isdigit():
				return int(c)
			else:
				raise ValueError("invalid register spec %r" % c)

		def _readcr():
			c = stream.read(1)
			if c != u"\n":
				raise ValueError("invalid linefeed %r" % c)

		self = cls()
		if isinstance(bin, str):
			bin = bin.decode("utf-8")
		stream = StringIO.StringIO(bin)
		header = stream.readline()
		header = header.rstrip()
		if header != "l4":
			raise ValueError("invalid header, expected 'l4', got %r" % header)
		version = stream.readline()
		version = version.rstrip()
		if version != "1":
			raise ValueError("invalid version, expected 1 got, %r" % version)
		self.source = _readstr("s")
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
			code = _readstr(u"c")
			arg = _readstr(u"a")
			locspec = stream.read(1)
			if locspec == u"^":
				if location is None:
					raise ValueError("no previous location")
			elif locspec == u"*":
				location = Location(self.source, _readstr("t"), _readint("<"), _readint(">"), _readint("["), _readint("]"))
			else:
				raise ValueError("invalid location spec %r" % locspec)
			_readcr()
			count -= 1
			self.opcodes.append(Opcode(code, r1, r2, r3, r4, r5, arg, location))
		return self

	def assrc(self):
		return self.source

	def asbin(self):
		def _writeint(term, number):
			stream.write(unicode(number))
			stream.write(term)

		def _writestr(term, string):
			if string:
				stream.write(str(len(string)))
			if string is None:
				term = term.upper()
			stream.write(term)
			stream.write(string)

		stream = StringIO.StringIO()
		stream.write(u"l4\n1\n")
		_writestr(u"s", self.source)
		stream.write(u"\n")
		_writeint(u"#", len(self.opcodes))
		stream.write(u"\n")
		lastlocation = None
		for opcode in self:
			stream.write(unicode(opcode.r1) if opcode.r1 is not None else u"-")
			stream.write(unicode(opcode.r2) if opcode.r2 is not None else u"-")
			stream.write(unicode(opcode.r3) if opcode.r3 is not None else u"-")
			stream.write(unicode(opcode.r4) if opcode.r4 is not None else u"-")
			stream.write(unicode(opcode.r5) if opcode.r5 is not None else u"-")
			_writestr(u"c", opcode.code)
			_writestr(u"a", opcode.arg)
			if opcode.location is not lastlocation:
				lastlocation = opcode.location
				stream.write(u"*")
				_writestr(u"t", lastlocation.type)
				_writeint(u"<", lastlocation.starttag)
				_writeint(u">", lastlocation.endtag)
				_writeint(u"[", lastlocation.startcode)
				_writeint(u"]", lastlocation.endcode)
			else:
				stream.write(u"^")
			stream.write(u"\n")
		return stream.getvalue().encode("utf-8")

	def __iter__(self):
		return iter(self.opcodes)

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

	@classmethod
	def _tokenize(cls, source, startdelim, enddelim):
		pattern = u"%s(print|code|for|if|elif|else|end)(\s*(.*?)\s*)?%s" % (re.escape(startdelim), re.escape(enddelim))
		pos = 0
		for match in re.finditer(pattern, source):
			if match.start() != pos:
				yield Location(source, None, pos, match.start(), pos, match.start())
			yield Location(source, source[match.start(1):match.end(1)], match.start(), match.end(), match.start(3), match.end(3))
			pos = match.end()
		end = len(source)
		if pos != end:
			yield Location(source, None, pos, end, pos, end)

	@classmethod
	def _compile(cls, string, startdelim, enddelim):
		# This stack stores for each nested for/foritem/if/elif/else the following information:
		# 1) Which construct we're in (i.e. "if" or "for")
		# For ifs:
		# 2) How many if's or elif's we have seen (this is used for simulating elif's via nested if's, for each additional elif, we have one more endif to add)
		# 3) Whether we've already seen the else
		stack = []
		for location in cls._tokenize(string, startdelim, enddelim):
			try:
				if location.type is None:
					yield Opcode(None, location=location)
				elif location.type == "print":
					for (r, op) in parseexpr(location):
						yield op
					yield Opcode("print", r1=r, location=location)
				elif location.type == "code":
					for (r, op) in parsestmt(location):
						yield op
				elif location.type == "if":
					for (r, op) in parseexpr(location):
						yield op
					yield Opcode("if", r1=r, location=location)
					stack.append(("if", 1, False))
				elif location.type == "elif":
					if not stack or stack[-1][0] != "if":
						raise BlockError("elif doesn't match any if")
					elif stack[-1][2]:
						raise BlockError("else already seen in elif")
					yield Opcode("else", location=location)
					for (r, op) in parseexpr(location):
						yield op
					yield Opcode("if", r1=r, location=location)
					stack[-1] = ("if", stack[-1][1]+1, False)
				elif location.type == "else":
					if not stack or stack[-1][0] != "if":
						raise BlockError("else doesn't match any if")
					elif stack[-1][2]:
						raise BlockError("duplicate else")
					yield Opcode("else", location=location)
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
							yield Opcode("endif", location=location)
					else: # last[0] == "for":
						yield Opcode("endfor", location=location)
				elif location.type == "for":
					for (r, op) in parsefor(location):
						yield op
					stack.append(("for",))
				else: # Can't happen
					raise ValueError("unknown tag %r" % location.type)
			except Error, exc:
				exc.decorate(location)
				raise
			except Exception, exc:
				raise
				raise Error(exc).decorate(location)
		if stack:
			raise BlockError("unclosed blocks")

	def __str__(self):
		return "\n".join(self.format())

	def __unicode__(self):
		return u"\n".join(self.format())


###
### Helper functions for register allocation
###

def allocreg(registers, location):
	try:
		return registers.pop()
	except KeyError:
		raise OutOfRegistersError()


def freereg(registers, register):
	registers.add(register)


###
### Tokens and nodes for the AST
###

class Token(object):
	def __init__(self, type):
		self.type = type

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.type)

	def __str__(self):
		return self.type


class AST(object):
	pass


class Const(AST):
	"""
	Common baseclass for all constants (used for type testing in constant folding)
	"""


class None_(Const):
	type = "none"

	def __repr__(self):
		return "%s()" % self.__class__.__name__

	def compile(self, registers, location):
		r = allocreg(registers, location)
		yield (r, Opcode("loadnone", r1=r, location=location))


class True_(Const):
	type = "true"
	value = True

	def __repr__(self):
		return "%s()" % self.__class__.__name__

	def compile(self, registers, location):
		r = allocreg(registers, location)
		yield (r, Opcode("loadtrue", r1=r, location=location))


class False_(Const):
	type = "false"
	value = False

	def __repr__(self):
		return "%s()" % self.__class__.__name__

	def compile(self, registers, location):
		r = allocreg(registers, location)
		yield (r, Opcode("loadfalse", r1=r, location=location))



class Value(Const):
	def __init__(self, value):
		self.value = value

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.value)

	def compile(self, registers, location):
		r = allocreg(registers, location)
		yield (r, Opcode("load%s" % self.type, r1=r, arg=self.value, location=location))


class Int(Value):
	type = "int"


class Float(Value):
	type = "float"


class Str(Value):
	type = "str"


class Name(AST):
	type = "name"

	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.name)

	def compile(self, registers, location):
		r = allocreg(registers, location)
		yield (r, Opcode("loadvar", r1=r, arg=self.name, location=location))


class For(AST):
	def __init__(self, iter, cont):
		self.iter = iter
		self.cont = cont

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.iter, self.cont)

	def compile(self, registers, location):
		for (rc, op) in self.cont.compile(registers, location):
			yield (rc, op)
		ri = allocreg(registers, location)
		yield (rc, Opcode("for", r1=ri, r2=rc, location=location))
		if isinstance(self.iter, list):
			for (i, iter) in enumerate(self.iter):
				rii = allocreg(registers, location)
				yield (rii, Opcode("loadint", r1=rii, arg=str(i), location=location))
				yield (rii, Opcode("getitem", r1=rii, r2=ri, r3=rii, location=location))
				yield (rii, Opcode("storevar", r1=rii, arg=iter.name, location=location))
				freereg(registers, rii)
		else:
			yield (ri, Opcode("storevar", r1=ri, arg=self.iter.name, location=location))
		freereg(registers, ri)
		freereg(registers, rc)


class GetAttr(AST):
	def __init__(self, obj, attr):
		self.obj = obj
		self.attr = attr

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.obj, self.attr)

	def compile(self, registers, location):
		for (r, op) in self.obj.compile(registers, location):
			yield (r, op)
		yield (r, Opcode("getattr", r1=r, r2=r, arg=self.attr.name, location=location))


class GetItem(AST):
	def __init__(self, obj, key):
		self.obj = obj
		self.key = key

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.obj, self.key)

	def compile(self, registers, location):
		for (r1, op) in self.obj.compile(registers, location):
			yield (r1, op)
		for (r2, op) in self.key.compile(registers, location):
			yield (r2, op)
		yield (r1, Opcode("getitem", r1=r1, r2=r1, r3=r2, location=location))
		freereg(registers, r2)


class GetSlice12(AST):
	def __init__(self, obj, index1, index2):
		self.obj = obj
		self.index1 = index1
		self.index2 = index2

	def __repr__(self):
		return "%s(%r, %r, %r)" % (self.__class__.__name__, self.obj, self.index1, self.index2)

	def compile(self, registers, location):
		for (r1, op) in self.obj.compile(registers, location):
			yield (r1, op)
		for (r2, op) in self.index1.compile(registers, location):
			yield (r2, op)
		for (r3, op) in self.index2.compile(registers, location):
			yield (r3, op)
		yield (r1, Opcode("getslice12", r1=r1, r2=r1, r3=r2, r4=r3, location=location))
		freereg(registers, r2)
		freereg(registers, r3)


class GetSlice1(AST):
	def __init__(self, obj, index1):
		self.obj = obj
		self.index1 = index1

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.obj, self.index1)

	def compile(self, registers, location):
		for (r1, op) in self.obj.compile(registers, location):
			yield (r1, op)
		for (r2, op) in self.index1.compile(registers, location):
			yield (r2, op)
		yield (r1, Opcode("getslice1", r1=r1, r2=r1, r3=r2, location=location))
		freereg(registers, r2)


class GetSlice2(AST):
	def __init__(self, obj, index2):
		self.obj = obj
		self.index2 = index2

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.obj, self.index2)

	def compile(self, registers, location):
		for (r1, op) in self.obj.compile(registers, location):
			yield (r1, op)
		for (r2, op) in self.index2.compile(registers, location):
			yield (r2, op)
		yield (r1, Opcode("getslice2", r1=r1, r2=r1, r3=r2, location=location))
		freereg(registers, r2)


class GetSlice(AST):
	def __init__(self, obj):
		self.obj = obj

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.obj)

	def compile(self, registers, location):
		for (r1, op) in self.obj.compile(registers, location):
			yield (r1, op)
		yield (r1, Opcode("getslice", r1=r1, r2=r1, location=location))


class Unary(AST):
	opcode = None

	def __init__(self, obj):
		self.obj = obj

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.obj)

	def compile(self, registers, location):
		for (r, op) in self.obj.compile(registers, location):
			yield (r, op)
		yield (r, Opcode(self.opcode, r1=r, r2=r, location=location))


class Not(Unary):
	opcode = "not"


class Neg(Unary):
	opcode = "neg"


class Binary(AST):
	opcode = None

	def __init__(self, obj1, obj2):
		self.obj1 = obj1
		self.obj2 = obj2

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.obj1, self.obj2)

	def compile(self, registers, location):
		for (r1, op) in self.obj1.compile(registers, location):
			yield (r1, op)
		for (r2, op) in self.obj2.compile(registers, location):
			yield (r2, op)
		yield (r1, Opcode(self.opcode, r1=r1, r2=r1, r3=r2, location=location))
		freereg(registers, r2)


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

	def __init__(self, name, value):
		self.name = name
		self.value = value

	def __repr__(self):
		return "%s(%r, %r)" % (self.__class__.__name__, self.name, self.value)

	def compile(self, registers, location):
		for (r, op) in self.value.compile(registers, location):
			yield (r, op)
		yield (r, Opcode(self.opcode, r1=r, arg=self.name.name, location=location))
		freereg(registers, r)


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


class CallFunc(AST):
	def __init__(self, name, args):
		self.name = name
		self.args = args

	def __repr__(self):
		if self.args:
			return "%s(%r, %s)" % (self.__class__.__name__, self.name, repr(self.args)[1:-1])
		else:
			return "%s(%r)" % (self.__class__.__name__, self.name)

	def compile(self, registers, location):
		if len(self.args) == 0:
			r = allocreg(registers, location)
			yield (r, Opcode("callfunc0", r1=r, arg=self.name.name, location=location))
		elif len(self.args) == 1:
			for (r0, op) in self.args[0].compile(registers, location):
				yield (r0, op)
			yield (r0, Opcode("callfunc1", r1=r0, r2=r0, arg=self.name.name, location=location))
		elif len(self.args) == 2:
			for (r0, op) in self.args[0].compile(registers, location):
				yield (r0, op)
			for (r1, op) in self.args[1].compile(registers, location):
				yield (r1, op)
			(r0, arg0) = self.args[0].compile(registers, location)
			(r1, arg1) = self.args[1].compile(registers, location)
			yield (r0, Opcode("callfunc2", r1=r0, r2=r0, r3=r1, arg=self.name.name, location=location))
			freereg(registers, r1)
		else:
			raise ValueError("%d arguments not supported" % len(self.args))


class CallMeth(AST):
	def __init__(self, name, obj, args):
		self.name = name
		self.obj = obj
		self.args = args

	def __repr__(self):
		if self.args:
			return "%s(%r, %r, %s)" % (self.__class__.__name__, self.name, self.obj, repr(self.args)[1:-1])
		else:
			return "%s(%r, %r)" % (self.__class__.__name__, self.name, self.obj)

	def compile(self, registers, location):
		if len(self.args) == 0:
			for (r, op) in self.obj.compile(registers, location):
				yield (r, op)
			yield (r, Opcode("callmeth0", r1=r, r2=r, arg=self.name.name, location=location))
		elif len(self.args) == 1:
			for (r, op) in self.obj.compile(registers, location):
				yield (r, op)
			for (r0, op) in self.args[0].compile(registers, location):
				yield (r0, op)
			yield (r, Opcode("callmeth1", r1=r, r2=r, r3=r0, arg=self.name.name, location=location))
			freereg(registers, r0)
		elif len(self.args) == 2:
			for (r, op) in self.obj.compile(registers, location):
				yield (r, op)
			for (r0, op) in self.args[0].compile(registers, location):
				yield (r0, op)
			for (r1, op) in self.args[1].compile(registers, location):
				yield (r1, op)
			yield (r, Opcode("callmeth2", r1=r, r2=r, r3=r0, r4=r1, arg=self.name.name, location=location))
			freereg(registers, r0)
			freereg(registers, r1)
		elif len(self.args) == 3:
			for (r, op) in self.obj.compile(registers, location):
				yield (r, op)
			for (r0, op) in self.args[0].compile(registers, location):
				yield (r0, op)
			for (r1, op) in self.args[1].compile(registers, location):
				yield (r1, op)
			for (r2, op) in self.args[2].compile(registers, location):
				yield (r2, op)
			yield (r, Opcode("callmeth3", r1=r, r2=r, r3=r0, r4=r1, r5=r2, arg=self.name.name, location=location))
			freereg(registers, r0)
			freereg(registers, r1)
			freereg(registers, r2)
		else:
			raise ValueError("%d arguments not supported" % len(self.args))


###
### Tokenizer
###

class Scanner(spark.GenericScanner):
	def __init__(self):
		spark.GenericScanner.__init__(self, re.UNICODE, "normal")
		self.collectstr = []

	def tokenize(self, location):
		self.rv = []
		try:
			spark.GenericScanner.tokenize(self, location.code)
			if self.mode != "normal":
				raise UnterminatedStringError()
		except Error, exc:
			exc.decorate(location)
			raise
		except Exception, exc:
			raise
			raise Error(exc).decorate(location)
		return self.rv

	@spark.token("in|not|or|and|\\(|\\)|\\[|\\]|\\.|,|==|\\!=|=|\\+=|\\-=|\\*=|/=|//=|%=|%|:|\\+|-|\\*|/|//", "normal")
	def token(self, s):
		self.rv.append(Token(s))

	@spark.token("None", "normal")
	def none(self, s):
		self.rv.append(None_())

	@spark.token("True", "normal")
	def true(self, s):
		self.rv.append(True_())

	@spark.token("False", "normal")
	def false(self, s):
		self.rv.append(False_())

	@spark.token("[a-zA-Z_][\\w]*", "normal")
	def name(self, s):
		self.rv.append(Name(s))

	# We don't have negatve numbers, this is handled by constant folding in the AST for unary minus
	@spark.token("\\d+\\.\\d*([eE][+-]?\\d+)?", "normal")
	@spark.token("\\d+(\\.\\d*)?[eE][+-]?\\d+", "normal")
	def float(self, s):
		self.rv.append(Float(float(s)))

	@spark.token("0[xX][\\da-fA-F]+", "normal")
	def hexint(self, s):
		self.rv.append(Int(int(s[2:], 16)))

	@spark.token("0[oO][0-7]+", "normal")
	def octint(self, s):
		self.rv.append(Int(int(s[2:], 8)))

	@spark.token("0[bB][01]+", "normal")
	def binint(self, s):
		self.rv.append(Int(int(s[2:], 2)))

	@spark.token("\\d+", "normal")
	def int(self, s):
		self.rv.append(Int(int(s)))

	@spark.token("'", "normal")
	def beginstr1(self, s):
		self.mode = "str1"

	@spark.token('"', "normal")
	def beginstr2(self, s):
		self.mode = "str2"

	@spark.token("'", "str1")
	@spark.token('"', "str2")
	def endstr(self, s):
		self.rv.append(Str("".join(self.collectstr)))
		self.collectstr = []
		self.mode = "normal"

	@spark.token("\\s+", "normal")
	def whitespace(self, s):
		pass

	@spark.token("\\\\\\\\", "str1", "str2")
	def escapedbackslash(self, s):
		self.collectstr.append("\\")

	@spark.token("\\\\'", "str1", "str2")
	def escapedapos(self, s):
		self.collectstr.append("'")

	@spark.token('\\\\"', "str1", "str2")
	def escapedquot(self, s):
		self.collectstr.append('"')

	@spark.token("\\\\a", "str1", "str2")
	def escapedbell(self, s):
		self.collectstr.append("\a")

	@spark.token("\\\\b", "str1", "str2")
	def escapedbackspace(self, s):
		self.collectstr.append("\b")

	@spark.token("\\\\f", "str1", "str2")
	def escapedformfeed(self, s):
		self.collectstr.append("\f")

	@spark.token("\\\\n", "str1", "str2")
	def escapedlinefeed(self, s):
		self.collectstr.append("\n")

	@spark.token("\\\\r", "str1", "str2")
	def escapedcarriagereturn(self, s):
		self.collectstr.append("\r")

	@spark.token("\\\\t", "str1", "str2")
	def escapedtab(self, s):
		self.collectstr.append("\t")

	@spark.token("\\\\v", "str1", "str2")
	def escapedverticaltab(self, s):
		self.collectstr.append("\v")

	@spark.token("\\\\e", "str1", "str2")
	def escapedescape(self, s):
		self.collectstr.append("\x1b")

	@spark.token("\\\\x[0-9a-fA-F]{2}", "str1", "str2")
	def escaped8bitchar(self, s):
		self.collectstr.append(unichr(int(s[2:], 16)))

	@spark.token("\\\\u[0-9a-fA-F]{4}", "str1", "str2")
	def escaped16bitchar(self, s):
		self.collectstr.append(unichr(int(s[2:], 16)))

	@spark.token(".", "str1", "str2")
	def text(self, s):
		self.collectstr.append(s)

	def error(self, s, pos):
		raise LexicalError(s)

	@spark.token("(.|\\n)+")
	def default(self, s):
		raise LexicalError(s)


###
### Parsers for different types of code
###

class ExprParser(spark.GenericParser):
	def __init__(self, start="expr0"):
		spark.GenericParser.__init__(self, start)
		self.scanner = Scanner()

	def compile(self, location):
		try:
			ast = self.parse(self.scanner.tokenize(location))
			registers = set(xrange(10))
			return ast.compile(registers, location) # return a generator-iterator
		except Error, exc:
			exc.decorate(location)
			raise
		except Exception, exc:
			raise
			raise Error(exc).decorate(location)

	def typestring(self, token):
		return token.type

	def error(self, token):
		raise SyntaxError(token)

	def makeconst(self, value):
		if value is None:
			return None_()
		elif value is True:
			return True_()
		elif value is False:
			return False_()
		elif isinstance(value, int):
			return Int(value)
		elif isinstance(value, float):
			return Float(value)
		elif isinstance(value, basestring):
			return Str(value)
		else:
			raise TypeError("can't convert %r" % value)

	# To implement operator precedence, each expression rule has the precedence in its name. The highest precedence is 11 for atomic expressions.
	# Each expression can have only expressions as parts, which have the some or a higher precedence with two exceptions:
	#    1) Expressions where there's no ambiguity, like the index for a getitem/getslice or function/method arguments;
	#    2) Brackets, which can be used to boost the precedence of an expression to the level of an atomic expression.

	@spark.rule('expr11 ::= none')
	def expr_none(self, (none,)):
		return none

	@spark.rule('expr11 ::= true')
	def expr_true(self, (true,)):
		return true

	@spark.rule('expr11 ::= false')
	def expr_false(self, (false,)):
		return false

	@spark.rule('expr11 ::= str')
	def expr_str(self, (value,)):
		return value

	@spark.rule('expr11 ::= int')
	def expr_int(self, (value,)):
		return value

	@spark.rule('expr11 ::= float')
	def expr_float(self, (value,)):
		return value

	@spark.rule('expr11 ::= name')
	def expr_name(self, (name,)):
		return name

	@spark.rule('expr11 ::= ( expr0 )')
	def expr_bracket(self, (_0, expr, _1)):
		return expr

	@spark.rule('expr10 ::= name ( )')
	def expr_callfunc0(self, (name, _0, _1)):
		return CallFunc(name, [])

	@spark.rule('expr10 ::= name ( expr0 )')
	def expr_callfunc1(self, (name, _0, arg0, _1)):
		return CallFunc(name, [arg0])

	@spark.rule('expr10 ::= name ( expr0 , expr0 )')
	def expr_callfunc2(self, (name, _0, arg0, _1, arg1, _2)):
		return CallFunc(name, [arg0, arg1])

	@spark.rule('expr9 ::= expr9 [ expr0 ]')
	def expr_getitem(self, (expr, _0, key, _1)):
		if isinstance(expr, Const) and isinstance(key, Const): # Constant folding
			return self.makeconst(expr.value[key.value])
		return GetItem(expr, key)

	@spark.rule('expr9 ::= expr9 [ expr0 : expr0 ]')
	def expr_getslice12(self, (expr, _0, index1, _1, index2, _2)):
		if isinstance(expr, Const) and isinstance(index1, Const) and isinstance(index2, Const): # Constant folding
			return self.makeconst(expr.value[index1.value:index1.value])
		return GetSlice12(expr, index1, index2)

	@spark.rule('expr9 ::= expr9 [ expr0 : ]')
	def expr_getslice1(self, (expr, _0, index1, _1, _2)):
		if isinstance(expr, Const) and isinstance(index1, Const): # Constant folding
			return self.makeconst(expr.value[index1.value:])
		return GetSlice1(expr, index1)

	@spark.rule('expr9 ::= expr9 [ : expr0 ]')
	def expr_getslice2(self, (expr, _0, _1, index2, _2)):
		if isinstance(expr, Const) and isinstance(index2, Const): # Constant folding
			return self.makeconst(expr.value[:index2.value])
		return GetSlice2(expr, index2)

	@spark.rule('expr9 ::= expr9 [ : ]')
	def expr_getslice(self, (expr, _0, _1, _2)):
		if isinstance(expr, Const): # Constant folding
			return self.makeconst(expr.value[:])
		return GetSlice(expr)

	@spark.rule('expr8 ::= expr8 . name')
	def expr_getattr(self, (expr, _0, name)):
		return GetAttr(expr, name)

	@spark.rule('expr8 ::= expr8 . name ( )')
	def expr_callmeth0(self, (expr, _0, name, _1, _2)):
		return CallMeth(name, expr, [])

	@spark.rule('expr8 ::= expr8 . name ( expr0 )')
	def expr_callmeth1(self, (expr, _0, name, _1, arg1, _2)):
		return CallMeth(name, expr, [arg1])

	@spark.rule('expr8 ::= expr8 . name ( expr0 , expr0 )')
	def expr_callmeth2(self, (expr, _0, name, _1, arg1, _2, arg2, _3)):
		return CallMeth(name, expr, [arg1, arg2])

	@spark.rule('expr8 ::= expr8 . name ( expr0 , expr0 , expr0 )')
	def expr_callmeth3(self, (expr, _0, name, _1, arg1, _2, arg2, _3, arg3, _4)):
		return CallMeth(name, expr, [arg1, arg2, arg3])

	@spark.rule('expr7 ::= - expr7')
	def expr_neg(self, (_0, expr)):
		if isinstance(expr, Const): # Constant folding
			return self.makeconst(-expr.value)
		return Neg(expr)

	@spark.rule('expr6 ::= expr6 * expr6')
	def expr_mul(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value * obj2.value)
		return Mul(obj1, obj2)

	@spark.rule('expr6 ::= expr6 // expr6')
	def expr_floordiv(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value // obj2.value)
		return FloorDiv(obj1, obj2)

	@spark.rule('expr6 ::= expr6 / expr6')
	def expr_truediv(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value / obj2.value)
		return TrueDiv(obj1, obj2)

	@spark.rule('expr6 ::= expr6 % expr6')
	def expr_mod(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value % obj2.value)
		return Mod(obj1, obj2)

	@spark.rule('expr5 ::= expr5 + expr5')
	def expr_add(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value + obj2.value)
		return Add(obj1, obj2)

	@spark.rule('expr5 ::= expr5 - expr5')
	def expr_sub(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value - obj2.value)
		return Sub(obj1, obj2)

	@spark.rule('expr4 ::= expr4 == expr4')
	def expr_equal(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value == obj2.value)
		return Equal(obj1, obj2)

	@spark.rule('expr4 ::= expr4 != expr4')
	def expr_notequal(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(obj1.value != obj2.value)
		return NotEqual(obj1, obj2)

	@spark.rule('expr3 ::= expr3 in expr3')
	def expr_contains(self, (obj, _0, container)):
		if isinstance(obj, Const) and isinstance(container, Const): # Constant folding
			return self.makeconst(obj.value in container.value)
		return Contains(obj, container)

	@spark.rule('expr3 ::= expr3 not in expr3')
	def expr_notcontains(self, (obj, _0, _1, container)):
		if isinstance(obj, Const) and isinstance(container, Const): # Constant folding
			return self.makeconst(obj.value not in container.value)
		return NotContains(obj, container)

	@spark.rule('expr2 ::= not expr2')
	def expr_not(self, (_0, expr)):
		if isinstance(expr1, Const): # Constant folding
			return self.makeconst(not expr.value)
		return Not(expr)

	@spark.rule('expr1 ::= expr1 and expr1')
	def expr_and(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(bool(obj1.value and obj2.value))
		return And(obj1, obj2)

	@spark.rule('expr0 ::= expr0 or expr0')
	def expr_or(self, (obj1, _0, obj2)):
		if isinstance(obj1, Const) and isinstance(obj2, Const): # Constant folding
			return self.makeconst(bool(obj1.value or obj2.value))
		return Or(obj1, obj2)

	# This rule makes operators of different precedences interoperable, by allowing an expression to "drop" its precedence.
	@spark.rule('expr10 ::= expr11')
	@spark.rule('expr9 ::= expr10')
	@spark.rule('expr8 ::= expr9')
	@spark.rule('expr7 ::= expr8')
	@spark.rule('expr6 ::= expr7')
	@spark.rule('expr5 ::= expr6')
	@spark.rule('expr4 ::= expr5')
	@spark.rule('expr3 ::= expr4')
	@spark.rule('expr2 ::= expr3')
	@spark.rule('expr1 ::= expr2')
	@spark.rule('expr0 ::= expr1')
	def expr_dropprio(self, (expr, )):
		return expr


class ForParser(ExprParser):
	def __init__(self, start="for"):
		ExprParser.__init__(self, start)

	@spark.rule('for ::= name in expr0')
	def for0(self, (iter, _0, cont)):
		return For(iter, cont)

	@spark.rule('for ::= ( name , ) in expr0')
	def for1(self, (_0, iter, _1, _2, _3, cont)):
		return For([iter], cont)

	@spark.rule('for ::= ( name , name ) in expr0')
	def for2a(self, (_0, iter1, _1, iter2, _2, _3, cont)):
		return For([iter1, iter2], cont)

	@spark.rule('for ::= ( name , name , ) in expr0')
	def for2b(self, (_0, iter1, _1, iter2, _2, _3, _4, cont)):
		return For([iter1, iter2], cont)


class StmtParser(ExprParser):
	def __init__(self, start="stmt"):
		ExprParser.__init__(self, start)

	@spark.rule('stmt ::= name = expr0')
	def stmt_assign(self, (name, _0, value)):
		return StoreVar(name, value)

	@spark.rule('stmt ::= name += expr0')
	def stmt_iadd(self, (name, _0, value)):
		return AddVar(name, value)

	@spark.rule('stmt ::= name -= expr0')
	def stmt_isub(self, (name, _0, value)):
		return SubVar(name, value)

	@spark.rule('stmt ::= name *= expr0')
	def stmt_imul(self, (name, _0, value)):
		return MulVar(name, value)

	@spark.rule('stmt ::= name /= expr0')
	def stmt_itruediv(self, (name, _0, value)):
		return TrueDivVar(name, value)

	@spark.rule('stmt ::= name //= expr0')
	def stmt_ifloordiv(self, (name, _0, value)):
		return FloorDivVar(name, value)

	@spark.rule('stmt ::= name %= expr0')
	def stmt_imod(self, (name, _0, value)):
		return ModVar(name, value)


parseexpr = ExprParser().compile
parsestmt = StmtParser().compile
parsefor = ForParser().compile
