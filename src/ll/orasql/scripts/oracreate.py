#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright 2005-2011 by LivingLogic AG, Bayreuth/Germany.
## Copyright 2005-2011 by Walter Dörwald
##
## All Rights Reserved
##
## See orasql/__init__.py for the license


"""
Purpose
-------

``oracreate`` prints the DDL of all objects in an Oracle database schema it a
way that can be used to recreate the schema (i.e. objects will be ordered so
that no errors happen for non-existant objects during script execution).
``oracreate`` can also be used to actually recreate the schema.


Options
-------

``oracreate`` supports the following options:

	``connectstring``
		An Oracle connectstring.

	``-v``, ``--verbose`` : ``false``, ``no``, ``0``, ``true``, ``yes`` or ``1``
		Produces output (on stderr) while to datebase is read or written.

	``-c``, ``--color`` : ``yes``, ``no`` or ``auto``
		Should the output (when the ``-v`` option is used) be colored. If ``auto``
		is specified (the default) then the output is colored if stderr is a
		terminal.

	``-s``, ``--seqcopy`` : ``false``, ``no``, ``0``, ``true``, ``yes`` or ``1``
		Outputs ``CREATE SEQUENCE`` statements for the existing sequences that have
		the current value of the sequence as the starting value. (Otherwise the
		sequences will restart with their initial value)

	``-x``, ``--execute`` : connectstring
		When the ``-x`` argument is given the SQL script isn't printed on stdout,
		but executed in the database specfied as the ``-x`` argument.

	``-k``, ``--keepjunk`` : ``false``, ``no``, ``0``, ``true``, ``yes`` or ``1``
		If given, database objects that have ``$`` or ``SYS_EXPORT_SCHEMA_`` in
		their name will be skipped (otherwise these objects will be included).

	``-i``, ``--ignore`` : ``false``, ``no``, ``0``, ``true``, ``yes`` or ``1``
		If given, errors occuring while it database is read or written will be
		ignored.

	``-e``, ``--encoding`` : encoding
		The encoding of the output (if ``-x`` is not given; default is ``utf-8``).


Examples
--------

Print the content of the database schema ``user@db``::

	$ oracreate user/pwd@db >db.sql

Copy the database schema ``user@db`` to ``user2@db2``::

	$ oracreate user/pwd@db -x user2/pwd2@db2 -v
"""


import sys, os, argparse

from ll import misc, astyle, orasql


__docformat__ = "reStructuredText"


s4warning = astyle.Style.fromenv("LL_ORASQL_REPRANSI_WARNING", "red:black")
s4error = astyle.Style.fromenv("LL_ORASQL_REPRANSI_ERROR", "red:black")
s4connectstring = astyle.Style.fromenv("LL_ORASQL_REPRANSI_CONNECTSTRING", "yellow:black")
s4object = astyle.Style.fromenv("LL_ORASQL_REPRANSI_OBJECT", "green:black")


def main(args=None):
	p = argparse.ArgumentParser(description="Print (or execute) the DDL of all objects in an Oracle database schema")
	p.add_argument("connectstring", help="Oracle connect string")
	p.add_argument("-v", "--verbose", dest="verbose", help="Give a progress report? (default %(default)s)", default=False, action=misc.FlagAction)
	p.add_argument("-c", "--color", dest="color", help="Color output (default %(default)s)", default="auto", choices=("yes", "no", "auto"))
	p.add_argument("-s", "--seqcopy", dest="seqcopy", help="copy sequence values? (default %(default)s)", default=False, action=misc.FlagAction)
	p.add_argument("-x", "--execute", metavar="CONNECTSTRING2", dest="execute", help="Execute in target database")
	p.add_argument("-k", "--keepjunk", dest="keepjunk", help="Output objects with '$' or 'SYS_EXPORT_SCHEMA_' in their name? (default %(default)s)", default=False, action=misc.FlagAction)
	p.add_argument("-i", "--ignore", dest="ignore", help="Ignore errors? (default %(default)s)", default=False, action=misc.FlagAction)
	p.add_argument("-e", "--encoding", dest="encoding", help="Encoding for output (default %(default)s)", default="utf-8")

	args = p.parse_args(args)

	if args.color == "yes":
		color = True
	elif args.color == "no":
		color = False
	else:
		color = None
	stdout = astyle.Stream(sys.stdout, color)
	stderr = astyle.Stream(sys.stderr, color)

	connection = orasql.connect(args.connectstring)

	if args.execute:
		connection2 = orasql.connect(args.execute)
		cursor2 = connection2.cursor()
		term = False
	else:
		term = True

	cs1 = s4connectstring(connection.connectstring())
	if args.execute:
		cs2 = s4connectstring(connection2.connectstring())

	def keep(obj):
		if obj.owner is not None:
			return False
		if args.keepjunk:
			return True
		# output pk, fks etc. only when they belong to a table we do output
		if isinstance(obj, (orasql.Constraint, orasql.Index)):
			obj = obj.table()
		if "$" in obj.name or obj.name.startswith("SYS_EXPORT_SCHEMA_"):
			return False
		return True

	for (i, obj) in enumerate(connection.iterobjects(mode="create", schema="user")):
		keepobj = keep(obj)
		if args.verbose:
			if args.execute:
				msg = astyle.style_default("oracreate.py: ", cs1, " -> ", cs2, ": fetching/creating #{}".format(i+1))
			else:
				msg = astyle.style_default("oracreate.py: ", cs1, " fetching #{}".format(i+1))
			msg = astyle.style_default(msg, " ", s4object(str(obj)))
			if not keepobj:
				msg = astyle.style_default(msg, " ", s4warning("(skipped)"))
			stderr.writeln(msg)

		if keepobj:
			if isinstance(obj, orasql.Sequence) and args.seqcopy:
				ddl = obj.createddlcopy(connection, term)
			else:
				ddl = obj.createddl(connection, term)
			if ddl:
				if args.execute:
					try:
						cursor2.execute(ddl)
					except orasql.DatabaseError, exc:
						if not args.ignore or "ORA-01013" in str(exc):
							raise
						stderr.writeln("oracreate.py: ", s4error("{}: {}".format(exc.__class__.__name__, str(exc).strip())))
				else:
					stdout.writeln(ddl.encode(args.encoding))
					stdout.writeln()


if __name__ == "__main__":
	sys.exit(main())
