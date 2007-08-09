#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

## Copyright 1999-2007 by LivingLogic AG, Bayreuth/Germany.
## Copyright 1999-2007 by Walter D�rwald
##
## All Rights Reserved
##
## See xist/__init__.py for the license


"""
<par>Module that helps to create &xist; namespace modules from TLD files
(Java tag library descriptors).
For usage information type:</par>
<prog>
tld2xsc --help
</prog>
"""


import sys, optparse

from ll import url
from ll.xist import xsc, xfind, parsers, converters
from ll.xist.ns import tld


def tld2xsc(inurl, outurl, verbose, xmlname, xmlurl, shareattrs):
	if verbose:
		print "Parsing TLD %s ..." % dtdurl
	node = parsers.parseURL(inurl)

	if verbose:
		print "Converting ..."

	# get and convert the taglib object
	node = xfind.first(node/tld.taglib)
	data = node.asxnd()

	if shareattrs=="dupes":
		data.shareattrs(False)
	elif shareattrs=="all":
		data.shareattrs(True)

	if verbose:
		print "Writing to %s ..." % outurl

	file = outurl.openwrite()
	file.write(data.aspy())
	file.close()


def main():
	p = optparse.OptionParser(usage="usage: %prog [options] inputurl.tld")
	p.add_option("-o", "--output", dest="output", metavar="FILE", help="write output to FILE")
	p.add_option("-v", "--verbose", action="store_true", dest="verbose")
	p.add_option("-p", "--prefix", dest="xmlname", help="the XML prefix for this namespace", default="prefix", metavar="PREFIX")
	p.add_option("-u", "--url", dest="xmlurl", help="the XML namespace name", metavar="URL")
	p.add_option("-s", "--shareattrs", dest="shareattrs", help="Should identical attributes be shared among elements?", choices=("none", "dupes", "all"), default="dupes")
	p.add_option("-m", "--model", dest="model", default="once", help="Add sims information to the namespace", choices=("no", "all", "once"))
	p.add_option("-d", "--defaults", action="store_true", dest="defaults", help="Output default values for attributes")

	(options, args) = p.parse_args()
	if len(args) != 1:
		p.error("incorrect number of arguments")
		return 1
	input = url.URL(args[0])
	if options.output is None:
		output = url.File(input.withExt("py").file)
	else:
		output = url.URL(options.output)
	tld2xsc(input, output, options.verbose, options.xmlname, options.xmlurl, options.shareattrs, options.model, options.defaults)


if __name__ == "__main__":
	sys.exit(main())
