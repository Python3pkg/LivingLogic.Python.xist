# -*- coding: utf-8 -*-

# Copyright 2007-2008 by LivingLogic AG, Bayreuth/Germany.
# Copyright 2007-2008 by Walter Dörwald
#
# All Rights Reserved
#
# See __init__.py for the license


"""
Python Codec for XML decoding
"""


import codecs

from _xml_codec import detectencoding as _detectencoding, fixencoding as _fixencoding


def decode(input, errors="strict", encoding=None):
	if encoding is None:
		encoding = _detectencoding(input, True)
	if encoding == "xml":
		raise ValueError("xml not allowed as encoding name")
	(input, consumed) = codecs.getdecoder(encoding)(input, errors)
	return (_fixencoding(input, unicode(encoding), True), consumed)


def encode(input, errors="strict", encoding=None):
	consumed = len(input)
	if encoding is None:
		encoding = _detectencoding(input, True)
	else:
		input = _fixencoding(input, unicode(encoding), True)
	if encoding == "xml":
		raise ValueError("xml not allowed as encoding name")
	info = codecs.lookup(encoding)
	return (info.encode(input, errors)[0], consumed)


class IncrementalDecoder(codecs.IncrementalDecoder):
	def __init__(self, errors="strict", encoding=None):
		self.decoder = None
		self.encoding = encoding
		codecs.IncrementalDecoder.__init__(self, errors)
		self._errors = errors # Store ``errors`` somewhere else, because we have to hide it in a property
		self.buffer = ""
		self.headerfixed = False

	def iterdecode(self, input):
		for part in input:
			result = self.decode(part, False)
			if result:
				yield result
		result = self.decode("", True)
		if result:
			yield result

	def decode(self, input, final=False):
		# We're doing basically the same as a ``BufferedIncrementalDecoder``,
		# but since  the buffer is only relevant until the encoding has been detected
		# (in which case the buffer of the underlying codec might kick in),
		# we're implementing buffering ourselves to avoid some overhead.
		if self.decoder is None:
			input = self.buffer + input
			self.encoding = _detectencoding(input, final)
			if self.encoding is None:
				self.buffer = input # retry the complete input on the next call
				return u"" # no encoding determined yet, so no output
			if self.encoding == "xml":
				raise ValueError("xml not allowed as encoding name")
			self.buffer = "" # isn't needed any more, as the decoder might keep its own buffer
			self.decoder = codecs.getincrementaldecoder(self.encoding)(self._errors)
		if self.headerfixed:
			return self.decoder.decode(input, final)
		# If we haven't fixed the header yet, the content of ``self.buffer`` is a ``unicode`` object
		output = self.buffer + self.decoder.decode(input, final)
		newoutput = _fixencoding(output, unicode(self.encoding), final)
		if newoutput is None:
			self.buffer = output # retry fixing the declaration (but keep the decoded stuff)
			return u""
		self.headerfixed = True
		return newoutput

	def reset(self):
		codecs.IncrementalDecoder.reset(self)
		self.decoder = None
		self.buffer = ""
		self.headerfixed = False

	def _geterrors(self):
		return self._errors

	def _seterrors(self, errors):
		# Setting ``errors`` must be done on the real decoder too
		if self.decoder is not None:
			self.decoder.errors = errors
		self._errors = errors
	errors = property(_geterrors, _seterrors)


class IncrementalEncoder(codecs.IncrementalEncoder):
	def __init__(self, errors="strict", encoding=None):
		self.encoder = None
		self.encoding = encoding
		codecs.IncrementalEncoder.__init__(self, errors)
		self._errors = errors # Store ``errors`` somewhere else, because we have to hide it in a property
		self.buffer = u""

	def iterencode(self, input):
		for part in input:
			result = self.encode(part, False)
			if result:
				yield result
		result = self.encode(u"", True)
		if result:
			yield result

	def encode(self, input, final=False):
		if self.encoder is None:
			input = self.buffer + input
			if self.encoding is not None:
				# Replace encoding in the declaration with the specified one
				newinput = _fixencoding(input, unicode(self.encoding), final)
				if newinput is None: # declaration not complete => Retry next time
					self.buffer = input
					return ""
				input = newinput
			else:
				# Use encoding from the XML declaration
				self.encoding = _detectencoding(input, final)
			if self.encoding is not None:
				if self.encoding == "xml":
					raise ValueError("xml not allowed as encoding name")
				info = codecs.lookup(self.encoding)
				self.encoder = info.incrementalencoder(self._errors)
				self.buffer = u""
			else:
				self.buffer = input
				return ""
		return self.encoder.encode(input, final)

	def reset(self):
		codecs.IncrementalEncoder.reset(self)
		self.encoder = None
		self.buffer = u""

	def _geterrors(self):
		return self._errors

	def _seterrors(self, errors):
		# Setting ``errors ``must be done on the real encoder too
		if self.encoder is not None:
			self.encoder.errors = errors
		self._errors = errors
	errors = property(_geterrors, _seterrors)


class StreamWriter(codecs.StreamWriter):
	def __init__(self, stream, errors="strict", encoding="utf-8", header=False):
		codecs.StreamWriter.__init__(self, stream, errors)
		self.encoder = IncrementalEncoder(errors)
		self._errors = errors

	def encode(self, input, errors='strict'):
		return (self.encoder.encode(input, False), len(input))

	def _geterrors(self):
		return self._errors

	def _seterrors(self, errors):
		# Setting ``errors`` must be done on the encoder too
		if self.encoder is not None:
			self.encoder.errors = errors
		self._errors = errors
	errors = property(_geterrors, _seterrors)


class StreamReader(codecs.StreamReader):
	def __init__(self, stream, errors="strict"):
		codecs.StreamReader.__init__(self, stream, errors)
		self.decoder = IncrementalDecoder(errors)
		self._errors = errors

	def decode(self, input, errors='strict'):
		return (self.decoder.decode(input, False), len(input))

	def _geterrors(self):
		return self._errors

	def _seterrors(self, errors):
		# Setting ``errors`` must be done on the decoder too
		if self.decoder is not None:
			self.decoder.errors = errors
		self._errors = errors
	errors = property(_geterrors, _seterrors)


def search_function(name):
	if name == "xml":
		return codecs.CodecInfo(
			name="xml",
			encode=encode,
			decode=decode,
			incrementalencoder=IncrementalEncoder,
			incrementaldecoder=IncrementalDecoder,
			streamwriter=StreamWriter,
			streamreader=StreamReader,
		)


codecs.register(search_function)