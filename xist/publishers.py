#! /usr/bin/env python

## Copyright 1999-2000 by LivingLogic AG, Bayreuth, Germany.
## Copyright 1999-2000 by Walter D�rwald
##
## See the file LICENSE for licensing details

"""
This module contains classes that may be used as publishing
handler in <methodref module="xist.xsc" class="Node">publish</methodref>.
"""

__version__ = "$Revision$"[11:-2]
# $Source$

import sys, types, array, codecs
import xsc, options, utils

strescapes = {'<': 'lt', '>': 'gt', '&': 'amp', '"': 'quot'}

class Publisher:
	"""
	base class for all publishers.
	"""

	mapsLegal = {}
	mapsIllegal = {}

	def __init__(self, encoding=None, XHTML=None):
		"""
		<par><argref>encoding</argref> specifies the encoding to be used.
		The encoding itself (i.e. calling <code>encode</code> on the
		unicode strings) must be done by <methodref>publish</methodref>
		and not by <methodref class="xsc.Node">publish</methodref>.</par>

		<par>The only exception is in the case of encodings that can't encode
		the full range of unicode characters like <code>us-ascii</code>
		or <code>iso-8859-1</code>. In this case non encodable characters will be replaced
		by characters references (if possible, if not (e.g. in comments or processing
		instructions) an exception will be raised) before they are passed to
		<methodref>publish</methodref>.</par>

		<par>With the parameter <argref>XHTML</argref> you can specify if you want HTML output
		(i.e. elements with a content model EMPTY as <code>&lt;foo&gt;</code>) with
		<code><argref>XHTML</argref>==0</code>, or XHTML output that is compatible with HTML browsers
		(element with an empty content model as <code>&lt;foo /&gt;</code> and others that
		just happen to be empty as <code>&lt;foo&gt;&lt;/foo&gt;</code>) with
		<code><argref>XHTML</argref>==1</code> or just plain XHTML with
		<code><argref>XHTML</argref>==2</code> (all empty elements as <code>&lt;foo/&gt;</code>).
		When you use the default (None) that value of the global variable
		outputXHTML will be used, which defaults to 1, but can be overwritten
		by the environment variable XSC_OUTPUT_XHTML and can of course be
		changed dynamically.</par>
		"""
		if encoding is None:
			encoding = options.outputEncoding
		self.encoding = encoding
		if XHTML is None:
			XHTML = options.outputXHTML
		if XHTML<0 or XHTML>2:
			raise ValueError("XHTML must be 0, 1 or 2")
		self.XHTML = XHTML

	def __call__(self, text):
		"""
		receives the string to be printed.
		overwrite this method
		"""
		pass

	def _encodeLegal(self, text):
		"""
		encodes the text <argref>text</argref> with the encoding <code><self/>.encoding</code>.
		using character references for <code>&amp;lt;</code> etc. and non encodabel characters
		is legal.
		"""
		for c in strescapes.keys():
			text = text.replace(c, u"&" + strescapes[c] + u";")

		try:
			text.encode(self.encoding)
			return text
		except UnicodeError:
			v = []
			for c in text:
				try:
					c.encode(self.encoding)
					v.append(c)
				except UnicodeError:
					v.append(u"&#" + str(ord(c)) + u";")
			return u"".join(v)

	def _encodeIllegal(self, text):
		"""
		encodes the text <argref>text</argref> with the encoding <code><self/>.encoding</code>.
		anything that requires a character reference (e.g. element names) is illegal.
		"""
		for c in strescapes.keys():
			if c in text:
				raise EncodingImpossibleError(self.startloc, self.encoding, text, c)

		try:
			text.encode(self.encoding)
			return text
		except UnicodeError:
			raise EncodingImpossibleError(self.startloc, self.encoding, text, "")

class FilePublisher(Publisher):
	"""
	writes the strings to a file.
	"""
	def __init__(self, file, encoding=None, XHTML=None):
		Publisher.__init__(self, encoding=encoding, XHTML=XHTML)
		(encode, decode, streamReaderClass, streamWriterClass) = codecs.lookup(self.encoding)
		self.file = streamWriterClass(file)

	def __call__(self, text):
		self.file.write(text)

	def tell(self):
		"""
		return the current position.
		"""
		return self.file.tell()

class PrintPublisher(FilePublisher):
	"""
	writes the strings to <code>sys.stdout</code>.
	"""
	def __init__(self, encoding=None, XHTML=None):
		FilePublisher.__init__(self, sys.stdout, encoding=encoding, XHTML=XHTML)

class StringPublisher(Publisher):
	"""
	collects all strings in an array.
	The joined strings are available via
	<methodref>asString</methodref>
	"""

	def __init__(self, XHTML=None):
		Publisher.__init__(self, encoding="utf16", XHTML=XHTML)
		self.texts = []

	def __call__(self, text):
		self.texts.append(text)

	def asString(self):
		"""
		Return the published strings as one long string.
		"""
		return u"".join(self.texts)

class BytePublisher(Publisher):
	"""
	collects all strings in an array.
	The joined strings are available via
	<methodref>asBytes</methodref> as a byte
	string suitable for writing to a file.
	"""

	def __init__(self, encoding=None, XHTML=None):
		Publisher.__init__(self, encoding=encoding, XHTML=XHTML)
		self.texts = []

	def __call__(self, text):
		self.texts.append(text)

	def asBytes(self):
		"""
		Return the published strings as one long byte string.
		"""
		return u"".join(self.texts).encode(self.encoding)

