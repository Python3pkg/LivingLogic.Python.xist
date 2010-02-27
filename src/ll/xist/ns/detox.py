# -*- coding: utf-8 -*-

## Copyright 1999-2010 by LivingLogic AG, Bayreuth/Germany
## Copyright 1999-2010 by Walter Dörwald
##
## All Rights Reserved
##
## See ll/__init__.py for the license


'''
This module is an XIST namespace. It provides a simple template language
based on processing instructions embedded in XML or plain text.

The following example is a simple "Hello, World" type template::

	from ll.xist.ns import detox

	template = """
	<?def helloworld(n=10)?>
		<?for i in xrange(n)?>
			Hello, World!
		<?end for?>
	<?end def?>
	"""

	module = detox.xml2mod(template)

	print "".join(module.helloworld())
'''


import sys, os, datetime, types

from ll import misc
from ll.xist import xsc


__docformat__ = "reStructuredText"


class expr(xsc.ProcInst):
	"""
	Embed the value of the expression
	"""


class textexpr(xsc.ProcInst):
	pass


class attrexpr(xsc.ProcInst):
	pass


class code(xsc.ProcInst):
	"""
	Embed the PI data literally in the generated code.

	For example ``<?code foo = 42?>`` will put the statement ``foo = 42`` into
	the generated Python source.
	"""


class if_(xsc.ProcInst):
	"""
	Starts an if block. An if block can contain zero or more :class:`elif_`
	blocks, followed by zero or one :class:`else_` block and must be closed
	with an :class:`endif` PI.

	For example::

		<?code import random?>
		<?code n = random.choice("123?")?>
		<?if n == "1"?>
			One
		<?elif n == "2"?>
			Two
		<?elif n == "3"?>
			Three
		<?else?>
			Something else
		<?end if?>
	"""
	xmlname = "if"


class elif_(xsc.ProcInst):
	"""
	Starts an elif block.
	"""
	xmlname = "elif"


class else_(xsc.ProcInst):
	"""
	Starts an else block.
	"""
	xmlname = "else"


class def_(xsc.ProcInst):
	"""
	Start a function (or method) definition. A function definition must be
	closed with an :class:`end` PI.

	Example::

		<?def persontable(persons)?>
			<table>
				<tr>
					<th>first name</th>
					<th>last name</th>
				</tr>
				<?for person in persons?>
					<tr>
						<td><?textexpr person.firstname?></td>
						<td><?textexpr person.lastname?></td>
					</tr>
				<?end for?>
			</table>
		<?end def?>

	If the generated function contains output (i.e. if there is text content
	or :class:`expr`, :class:`textexpr` or :class:`attrexpr` PIs before the
	matching :class:`end`) the generated function will be a generator function.

	Output outside of a function definition will be ignored.
	"""
	xmlname = "def"


class class_(xsc.ProcInst):
	"""
	Start a class definition. A class definition must be closed with an
	:class:`end` PI.

	Example::

		<?class mylist(list)?>
			<?def output(self)?>
				<ul>
					<?for item in self?>
						<li><?textexpr item?></li>
					<?endfor?>
				</ul>
			<?end def?>
		<?end class?>
	"""
	xmlname = "class"


class for_(xsc.ProcInst):
	"""
	Start a ``for`` loop. A for loop must be closed with an :class:`end` PI.

	For example::

		<ul>
			<?for i in xrange(10)?>
				<li><?expr str(i)?></li>
			<?end for?>
		</ul>
	"""
	xmlname = "for"


class while_(xsc.ProcInst):
	"""
	Start a ``while`` loop. A while loop must be closed with an :class:`end` PI.

	For example::

		<?code i = 0?>
		<ul>
			<?while True?>
				<li><?expr str(i)?><?code i += 1?></li>
				<?code if i > 10: break?>
			<?end while?>
		</ul>
	"""
	xmlname = "while"


class end(xsc.ProcInst):
	"""
	Ends a :class:`while_` or :class:`for` loop or a :class:`if_`, :class:`def_`
	or :class:`class_` block.
	"""


# The name of al available processing instructions
targets = set(value.xmlname for value in vars().itervalues() if isinstance(value, xsc._ProcInst_Meta))


# Used for indenting Python source code
indent = "\t"


def xml2py(source):
	stack = []
	stackoutput = [] # stack containing only True for def and False for class

	lines = [
		"# generated by %s on %s UTC" % (__file__, datetime.datetime.utcnow()),
		"",
		"from ll.misc import xmlescape as __detox_xmlescape__",
		"",
	]

	def endscope(action):
		if not stack:
			raise SyntaxError("can't end %s scope: no active scope" % (action or "unnamed"))
		if action and action != stack[-1][0]:
			raise SyntaxError("can't end %s scope: active scope is: %s %s" % (action, stack[-1][0], stack[-1][1]))
		return stack.pop()

	for (t, s) in misc.tokenizepi(source):
		if t is None:
			# ignore output outside of functions
			if stackoutput and stackoutput[-1]:
				lines.append("%syield %r" % (len(stack)*indent, s))
		elif t == "expr":
			# ignore output outside of functions
			if stackoutput and stackoutput[-1]:
				lines.append("%syield %s" % (len(stack)*indent, s))
		elif t == "textexpr":
			# ignore output outside of functions
			if stackoutput and stackoutput[-1]:
				lines.append("%syield __detox_xmlescape__(%s)" % (len(stack)*indent, s))
		elif t == "attrexpr":
			# ignore output outside of functions
			if stackoutput and stackoutput[-1]:
				lines.append("%syield __detox_xmlescape__(%s)" % (len(stack)*indent, s))
		elif t == "code":
			lines.append("%s%s" % (len(stack)*indent, s))
		elif t == "def":
			lines.append("")
			lines.append("%sdef %s:" % (len(stack)*indent, s))
			stack.append((t, s))
			stackoutput.append(True)
		elif t == "class":
			lines.append("")
			lines.append("%sclass %s:" % (len(stack)*indent, s))
			stack.append((t, s))
			stackoutput.append(False)
		elif t == "for":
			lines.append("%sfor %s:" % (len(stack)*indent, s))
			stack.append((t, s))
		elif t == "while":
			lines.append("%swhile %s:" % (len(stack)*indent, s))
			stack.append((t, s))
		elif t == "if":
			lines.append("%sif %s:" % (len(stack)*indent, s))
			stack.append((t, s))
		elif t == "else":
			lines.append("%selse:" % ((len(stack)-1)*indent))
		elif t == "elif":
			lines.append("%selif %s:" % ((len(stack)-1)*indent, s))
		elif t == "end":
			scope = endscope(s)
			if scope in ("def", "class"):
				stackoutput.pop()
		else: # unknown PI target => treat as text
			# ignore output outside of functions
			if stackoutput and stackoutput[-1]:
				s = "<?%s %s?>" % (t, s)
				lines.append("%syield %r" % (len(stack)*indent, s))
	if stack:
		raise SyntaxError("unclosed scopes remaining: %s" % ", ".join(scope[0] for scope in stack))
	return "\n".join(lines)


def xml2mod(source, name=None, filename="<string>", store=False, loader=None):
	name = name or "ll.xist.ns.detox.sandbox_%x" % (hash(filename) + sys.maxint + 1)
	module = types.ModuleType(name)
	module.__file__ = filename
	if loader is not None:
		module.__loader__ = loader
	if store:
		sys.modules[name] = module
	code = compile(xml2py(source), filename, "exec")
	exec code in module.__dict__
	return module


# The following stuff has been copied from Kids import hook

DETOX_EXT = ".detox"


def enable_import(suffixes=None):
	class DetoxLoader(object):
		def __init__(self, path=None):
			if path and os.path.isdir(path):
				self.path = path
			else:
				raise ImportError

		def find_module(self, fullname):
			path = os.path.join(self.path, fullname.split(".")[-1])
			for ext in [cls.DETOX_EXT] + self.suffixes:
				if os.path.exists(path + ext):
					self.filename = path + ext
					return self
			return None

		def load_module(self, fullname):
			try:
				return sys.modules[fullname]
			except KeyError:
				return xml2mod(open(self.filename, "r").read(), name=fullname, filename=self.filename, store=True, loader=self)

	DetoxLoader.suffixes = suffixes or []
	sys.path_hooks.append(DetoxLoader)
	sys.path_importer_cache.clear()
