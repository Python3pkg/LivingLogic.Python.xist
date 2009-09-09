/*
 * SGMLOP
 * $Id: //modules/sgmlop/sgmlop.c#20 $
 *
 * The sgmlop accelerator module
 *
 * This module provides a FastParser type, which is designed to speed
 * up the standard sgmllib and xmllib modules.  The parser can be
 * configured to support either basic SGML (enough of it to process
 * HTML documents, at least) or XML.
 *
 * History:
 * 1998-04-04 fl  Created (for coreXML)
 * 1998-04-05 fl  Added close method
 * 1998-04-06 fl  Added parse method, revised callback interface
 * 1998-04-14 fl  Fixed parsing of PI tags
 * 1998-05-14 fl  Cleaned up for first public release
 * 1998-05-19 fl  Fixed xmllib compatibility: handle_proc, handle_special
 * 1998-05-22 fl  Added attribute parser
 * 1999-06-20 fl  Added Element data type, various bug fixes.
 * 2000-05-28 fl  Fixed data truncation error (@XML1)
 * 2000-05-28 fl  Added temporary workaround for unicode problem (@XML2)
 * 2000-05-28 fl  Removed optional close argument (@XML3)
 * 2000-05-28 fl  Raise exception on recursive feed (@XML4)
 * 2000-07-05 fl  Fixed attribute handling in empty tags (@XML6) (release 1.0)
 * 2001-10-01 fl  Release buffer on close
 * 2001-10-01 fl  Added built-in support for standard entities (@XML8)
 * 2001-10-01 fl  Removed experimental Element data type
 * 2001-10-01 fl  Added support for hexadecimal character references
 * 2001-10-02 fl  Improved support for doctype parsing
 * 2001-10-02 fl  Optional well-formedness checker
 * 2001-12-18 fl  Flag missing entity handler only in strict mode (@XML12)
 * 2001-12-29 fl  Fixed compilation under gcc -Wstrict
 * 2002-01-13 fl  Resolve entities in attributes 
 * 2002-03-26 fl  PyArg_NoArgs is deprecated; replace with PyArg_ParseTuple
 * 2002-05-26 fl  Don't mess up on <empty/> tags (@XML20)
 * 2002-11-13 fl  Changed handling of large character entities (@XML15)
 * 2002-11-13 fl  Added support for garbage collection (@XML15)
 * 2003-09-07 fl  Fixed parsing of short PI's (@XMLTOOLKIT24)
 * 2003-09-07 fl  Fixed garbage collection support for Python 2.2 and later
 * 2004-04-04 fl  Fixed parsing of non-ascii attribute values (@XMLTOOLKIT38)
 * 2007-09-12 wd  Python 2.5 updates: use Py_ssize_t
 *
 * Copyright (c) 1998-2007 by Secret Labs AB
 * Copyright (c) 1998-2007 by Fredrik Lundh
 * 
 * fredrik@pythonware.com
 * http://www.pythonware.com
 *
 * By obtaining, using, and/or copying this software and/or its
 * associated documentation, you agree that you have read, understood,
 * and will comply with the following terms and conditions:
 * 
 * Permission to use, copy, modify, and distribute this software and its
 * associated documentation for any purpose and without fee is hereby
 * granted, provided that the above copyright notice appears in all
 * copies, and that both that copyright notice and this permission notice
 * appear in supporting documentation, and that the name of Secret Labs
 * AB or the author not be used in advertising or publicity pertaining to
 * distribution of the software without specific, written prior
 * permission.
 * 
 * SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO
 * THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
 * FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

/* FIXME: basic well-formedness checking */
/* FIXME: add (some kind of) unicode support */
/* FIXME: suppress trailing > after dtd endtag */
/* FIXME: basic structural validation? */

static char copyright[] =
    " SGMLOP 1.1.2 Copyright (c) 1998-2003 by Secret Labs AB ";

#define PY_SIZE_T_CLEAN

#include "Python.h"

#include <ctype.h>

#ifdef SGMLOP_UNICODE_SUPPORT
/* use wide character set (experimental) */
/* FIXME: under Python 1.6, the current version converts Unicode
   strings to UTF-8, and parses the result as if it was an ASCII
   string. */

#define CHAR_T            Py_UNICODE
#define ISALNUM           Py_UNICODE_ISALNUM
#define TOLOWER           Py_UNICODE_TOLOWER
#define EMPTYSTRING()     PyUnicode_FromUnicode(NULL, 0)
#define BUILDSTRING(s, l) PyUnicode_FromUnicode(s, l)
#define PARSEFORMAT       "u#"
#define BUILDFORMAT       "u#"

#define ISSPACE(ch) Py_UNICODE_ISSPACE(ch)

#define LETTER(ch) Py_UNICODE_ISALPHA(ch)

#define NAMECHAR(ch)\
    (Py_UNICODE_ISALNUM(ch) || (ch) == '.' || (ch) == '-' ||\
     (ch) == '_' || (ch) == ':')

#else

/* 8-bit character set */
#define CHAR_T            unsigned char
#define ISALNUM           isalnum
#define TOLOWER           tolower
#define EMPTYSTRING()     PyString_FromString("")
#define BUILDSTRING(s, l) PyString_FromStringAndSize(s, l)
#define PARSEFORMAT       "t#"
#define BUILDFORMAT       "s#"

#define ISSPACE(ch)\
    ((ch) == ' ' || (ch) == '\t' || (ch) == '\r' || (ch) == '\n')

#define LETTER(ch)\
    (((ch) >= 'a' && (ch) <= 'z') || ((ch) >= 'A' && (ch) <= 'Z') ||\
     (ch) >= 0x80)

#define DIGIT(ch)\
    ((ch) >= '0' && (ch) <= '9')

#define NAMECHAR(ch)\
    (LETTER(ch) || DIGIT(ch) || (ch) == '.' || (ch) == '-' ||\
     (ch) == '_' || (ch) == ':')

#endif

#if PY_VERSION_HEX >= 0x02050000
/* use Py_ssize_t (requires Python 2.5 or later) */
#define INTFORMAT "n"
#else
typedef int Py_ssize_t;
#define INTFORMAT "i"
#endif

#if PY_VERSION_HEX >= 0x02000000
/* use garbage collection (requires Python 2.0 or later) */
#define SGMLOP_GC

/* from http://python.ca/nas/python/type-gc.html */
#if defined(Py_TPFLAGS_GC) && !defined(Py_TPFLAGS_HAVE_GC)
/* Python 2.2 GC compatibility macros */
#define Py_TPFLAGS_HAVE_GC Py_TPFLAGS_GC
#define PyObject_GC_New PyObject_New
#define PyObject_GC_Del PyObject_Del
#define PyObject_GC_Track PyObject_GC_Init
#define PyObject_GC_UnTrack PyObject_GC_Fini
#endif

#ifndef Py_TPFLAGS_HAVE_GC
/* no GC */
#define Py_TPFLAGS_HAVE_GC 0
#define PyObject_GC_New PyObject_New
#define PyObject_GC_Del PyObject_Del
#define PyObject_GC_Track
#define PyObject_GC_UnTrack
#define PyGC_HEAD_SIZE 0
typedef int (*visitproc)(PyObject *, void *);
typedef int (*traverseproc)(PyObject *, visitproc, void *);
#endif

#endif

/* ==================================================================== */
/* parser data type */

/* state flags */
#define MAYBE 1
#define SURE 2

typedef struct {
    /* well-formedness checker */
    int (*starttag)(void* self, CHAR_T* b, CHAR_T* e);
    int (*endtag)(void* self, CHAR_T* b, CHAR_T* e);
    int (*attribute)(void* self, CHAR_T* b, CHAR_T* e);
    int (*entityref)(void* self, CHAR_T* b, CHAR_T* e);
    int (*charref)(void* self, CHAR_T* b, CHAR_T* e);
    int (*comment)(void* self, CHAR_T* b, CHAR_T* e);
} Checker;

/* parser type definition */
typedef struct {
    PyObject_HEAD

    /* mode flags */
    int xml; /* 0=sgml/html 1=xml */
    int strict; /* 0=sloppy 1=strict(er) */

    /* state attributes */
    int feed;
    int shorttag; /* 0=normal 2=parsing shorttag */
    int doctype; /* 0=normal 1=dtd pending 2=parsing dtd */
    int counter; /* line/block counter */

    /* optional well-formedness checker */
    /* FIXME: replace with stacked target objects */
    Checker* check;

    /* buffer (holds incomplete tags) */
    CHAR_T* buffer;
    Py_ssize_t bufferlen; /* current amount of data */
    Py_ssize_t buffertotal; /* actually allocated */

    /* callbacks */
    /* FIXME: move to target object */
    PyObject* handle_enterstarttag;
    PyObject* handle_enterattr;
    PyObject* handle_leaveattr;
    PyObject* handle_leavestarttag;
    PyObject* handle_endtag;
    PyObject* handle_proc;
    PyObject* handle_special;
    PyObject* handle_charref;
    PyObject* handle_entityref;
    PyObject* handle_data;
    PyObject* handle_cdata;
    PyObject* handle_comment;

} FastParserObject;

staticforward PyTypeObject FastParser_Type;

/* forward declarations */
static Py_ssize_t fastfeed(
    FastParserObject* self
    );
static int attrparse(
    FastParserObject* self, const CHAR_T *p, const CHAR_T *e
    );

static int entity(const CHAR_T* b, const CHAR_T *e);

static int wf_starttag(Checker* self, CHAR_T* b, CHAR_T* e);
static int wf_endtag(Checker* self, CHAR_T* b, CHAR_T* e);
static int wf_ok(Checker* self, CHAR_T* b, CHAR_T* e);

static Checker wf_checker = {
    (void*) wf_starttag,
    (void*) wf_endtag,
    (void*) wf_ok,
    (void*) wf_ok,
    (void*) wf_ok,
    (void*) wf_ok
};

/* -------------------------------------------------------------------- */
/* parser */

static PyObject*
_sgmlop_new(int xml)
{
    FastParserObject* self;

#if defined(SGMLOP_GC)
    self = PyObject_GC_New(FastParserObject, &FastParser_Type);
#else
    self = PyObject_NEW(FastParserObject, &FastParser_Type);
#endif

    if (self == NULL)
        return NULL;

    self->xml = xml;

    self->strict = 0;
    self->feed = 0;
    self->shorttag = 0;
    self->doctype = 0;
    self->counter = 0;

    self->check = NULL; /* &wf_checker; */

    self->buffer = NULL;
    self->bufferlen = 0;
    self->buffertotal = 0;

    self->handle_enterstarttag = NULL;
    self->handle_leavestarttag = NULL;
    self->handle_enterattr = NULL;
    self->handle_leaveattr = NULL;
    self->handle_endtag = NULL;
    self->handle_proc = NULL;
    self->handle_special = NULL;
    self->handle_charref = NULL;
    self->handle_entityref = NULL;
    self->handle_data = NULL;
    self->handle_cdata = NULL;
    self->handle_comment = NULL;

#if defined(SGMLOP_GC)
    PyObject_GC_Track(self);
#endif

    return (PyObject*) self;
}

static PyObject*
_sgmlop_sgmlparser(PyObject* self, PyObject* args)
{
    if (!PyArg_ParseTuple(args, ":SGMLParser"))
        return NULL;

    return _sgmlop_new(0);
}

static PyObject*
_sgmlop_xmlparser(PyObject* self, PyObject* args)
{
    if (!PyArg_ParseTuple(args, ":XMLParser"))
        return NULL;

    return _sgmlop_new(1);
}

#if defined (SGMLOP_GC)
static int
_sgmlop_traverse(FastParserObject *self, visitproc visit, void *arg)
{
    int err;

#define VISIT(member)\
    if (self->member) {\
        err = visit(self->member, arg);\
        if (err)\
            return err;\
    }

    VISIT(handle_enterstarttag);
    VISIT(handle_leavestarttag);
    VISIT(handle_enterattr);
    VISIT(handle_leaveattr);
    VISIT(handle_endtag);
    VISIT(handle_proc);
    VISIT(handle_special);
    VISIT(handle_charref);
    VISIT(handle_entityref);
    VISIT(handle_data);
    VISIT(handle_cdata);
    VISIT(handle_comment);

    return 0;
}
#endif

static int
_sgmlop_clear(FastParserObject* self)
{
#define CLEAR(member)\
    Py_XDECREF(self->member);\
    self->member = NULL;

    CLEAR(handle_enterstarttag);
    CLEAR(handle_leavestarttag);
    CLEAR(handle_enterattr);
    CLEAR(handle_leaveattr);
    CLEAR(handle_endtag);
    CLEAR(handle_proc);
    CLEAR(handle_special);
    CLEAR(handle_charref);
    CLEAR(handle_entityref);
    CLEAR(handle_data);
    CLEAR(handle_cdata);
    CLEAR(handle_comment);

    return 0;
}

static void
_sgmlop_dealloc(FastParserObject* self)
{
#if defined(SGMLOP_GC)
    PyObject_GC_UnTrack(self);
#endif
    if (self->buffer)
        free(self->buffer);
    _sgmlop_clear(self);
#if defined(SGMLOP_GC)
    PyObject_GC_Del(self);
#else
    PyObject_DEL(self);
#endif
}

static PyObject*
_sgmlop_register(FastParserObject* self, PyObject* args)
{
    /* register a callback object */
    PyObject* item;
    if (!PyArg_ParseTuple(args, "O", &item))
        return NULL;

#define GETCB(member, name)\
    Py_XDECREF(self->member);\
    self->member = PyObject_GetAttrString(item, name);

    GETCB(handle_enterstarttag, "handle_enterstarttag");
    GETCB(handle_leavestarttag, "handle_leavestarttag");
    GETCB(handle_enterattr, "handle_enterattr");
    GETCB(handle_leaveattr, "handle_leaveattr");
    GETCB(handle_endtag, "handle_endtag");
    GETCB(handle_proc, "handle_proc");
    GETCB(handle_special, "handle_special");
    GETCB(handle_charref, "handle_charref");
    GETCB(handle_entityref, "handle_entityref");
    GETCB(handle_data, "handle_data");
    GETCB(handle_cdata, "handle_cdata");
    GETCB(handle_comment, "handle_comment");

    PyErr_Clear();

    Py_INCREF(Py_None);
    return Py_None;
}


/* -------------------------------------------------------------------- */
/* feed data to parser.  the parser processes as much of the data as
   possible, and keeps the rest in a local buffer. */

static PyObject*
feed(FastParserObject* self, CHAR_T* string, int stringlen, int last)
{
    /* common subroutine for SGMLParser.feed and SGMLParser.close */

    int length;

    if (self->feed) {
        /* dealing with recursive feeds isn't exactly trivial, so
           let's just bail out before the parser messes things up */
        PyErr_SetString(PyExc_AssertionError, "recursive feed");
        return NULL;
    }

    /* append new text block to local buffer */
    if (!self->buffer) {
        length = stringlen;
        self->buffer = malloc((length + 1)*sizeof(CHAR_T));
        self->bufferlen = self->shorttag = self->doctype = 0;
        self->buffertotal = stringlen;
    } else {
        length = self->bufferlen + stringlen;
        if (length > self->buffertotal) {
            self->buffer = realloc(self->buffer, (length + 1)*sizeof(CHAR_T));
            self->buffertotal = length;
        }
    }
    if (!self->buffer) {
        PyErr_NoMemory();
        return NULL;
    }
    memcpy(self->buffer + self->bufferlen, string, stringlen*sizeof(CHAR_T));
    self->bufferlen = length;

    self->feed = 1;
    self->counter++;

    length = fastfeed(self);

    self->feed = 0;

    if (length < 0)
        return NULL;

    if (length > self->bufferlen) {
        /* ran beyond the end of the buffer (internal error) */
        PyErr_SetString(PyExc_AssertionError, "buffer overrun");
        return NULL;
    }

    if (length > 0 && length < self->bufferlen)
        /* adjust buffer */
        memmove(self->buffer, self->buffer + length,
                (self->bufferlen - length)*sizeof(CHAR_T));

    self->bufferlen -= length;

    /* FIXME: if data remains in the buffer even through this is the
       last call, do an extra handle_data to get rid of it */

    if (last && self->buffer) {
        free(self->buffer);
        self->buffer = NULL;
    }

    return Py_BuildValue(INTFORMAT, self->bufferlen);
}

static PyObject*
_sgmlop_feed(FastParserObject* self, PyObject* args)
{
    /* feed a chunk of data to the parser */

    CHAR_T* string;
    int stringlen;
    if (!PyArg_ParseTuple(args, PARSEFORMAT ":feed", &string, &stringlen))
        return NULL;

    return feed(self, string, stringlen, 0);
}

static PyObject*
_sgmlop_close(FastParserObject* self, PyObject* args)
{
    /* flush parser buffers */
    CHAR_T ch = 0;

    if (!PyArg_ParseTuple(args, ":close"))
        return NULL;

    return feed(self, &ch, 0, 1);
}

static PyObject*
_sgmlop_parse(FastParserObject* self, PyObject* args)
{
    /* feed a single chunk of data to the parser */

    CHAR_T* string;
    int stringlen;
    if (!PyArg_ParseTuple(args, PARSEFORMAT ":parse", &string, &stringlen))
        return NULL;

    return feed(self, string, stringlen, 1);
}


/* -------------------------------------------------------------------- */
/* type interface */

static PyMethodDef _sgmlop_methods[] = {
    /* register callbacks */
    {"register", (PyCFunction) _sgmlop_register, 1},
    /* incremental parsing */
    {"feed", (PyCFunction) _sgmlop_feed, 1},
    {"close", (PyCFunction) _sgmlop_close, 1},
    /* one-shot parsing */
    {"parse", (PyCFunction) _sgmlop_parse, 1},
    {NULL, NULL}
};

static PyObject*
_sgmlop_getattr(FastParserObject* self, char* name)
{
    return Py_FindMethod(_sgmlop_methods, (PyObject*) self, name);
}

statichere PyTypeObject FastParser_Type = {
    PyObject_HEAD_INIT(NULL)
    0, /* ob_size */
    "FastParser", /* tp_name */
    sizeof(FastParserObject), /* tp_size */
    0, /* tp_itemsize */
    /* methods */
    (destructor)_sgmlop_dealloc, /* tp_dealloc */
    0, /* tp_print */
    (getattrfunc)_sgmlop_getattr, /* tp_getattr */
    0, /* tp_setattr */
};

/* ==================================================================== */
/* python module interface */

static PyMethodDef _functions[] = {
    {"SGMLParser", _sgmlop_sgmlparser, 1},
    {"XMLParser", _sgmlop_xmlparser, 1},
    {NULL, NULL}
};

void
#ifdef WIN32
__declspec(dllexport)
#endif
initsgmlop(void)
{
    /* Patch object type */
    FastParser_Type.ob_type = &PyType_Type;

#if defined (SGMLOP_GC)
    /* enable garbage collection for the parser object */
    FastParser_Type.tp_basicsize += PyGC_HEAD_SIZE;
    FastParser_Type.tp_flags = Py_TPFLAGS_HAVE_GC;
    FastParser_Type.tp_traverse = (traverseproc) _sgmlop_traverse;
    FastParser_Type.tp_clear = (inquiry) _sgmlop_clear;
#endif

    Py_InitModule("sgmlop", _functions);
}

/* -------------------------------------------------------------------- */
/* well-formedness checker */

static int
wf_tag(Checker* self, CHAR_T* b, CHAR_T* e)
{
    /* check that the start tag contains a valid name */
    if (b >= e)
        goto err;
    if (!LETTER(*b) && *b != '_' && *b != ':')
        goto err;
    b++;
    while (b < e) {
        if (!NAMECHAR(*b))
            goto err;
        b++;
    }
    return 1;
  err:
    PyErr_Format(PyExc_SyntaxError, "malformed tag name");
    return 0;
}

static int
wf_starttag(Checker* self, CHAR_T* b, CHAR_T* e)
{
    if (!wf_tag(self, b, e))
        return 0;
    return 1;
}

static int
wf_endtag(Checker* self, CHAR_T* b, CHAR_T* e)
{
    if (!wf_tag(self, b, e))
        return 0;
    return 1;
}

static int
wf_ok(Checker* self, CHAR_T* b, CHAR_T* e)
{
    return 1;
}

/* -------------------------------------------------------------------- */
/* the parser does it all in a single loop, keeping the necessary
   state in a few flag variables and the data buffer.  if you have
   a good optimizer, this can be incredibly fast. */

#define TAG 0x100
#define TAG_START 0x101
#define TAG_END 0x102
#define TAG_EMPTY 0x103
#define DIRECTIVE 0x104
#define DOCTYPE 0x105
#define PI 0x106
#define DTD_START 0x107
#define DTD_END 0x108
#define DTD_ENTITY 0x109
#define CDATA 0x200
#define ENTITYREF 0x400
#define CHARREF 0x401
#define COMMENT 0x800

static int
entity(const CHAR_T* b, const CHAR_T* e)
{
    /* resolve standard entity (return <0 if non-standard/malformed) */
    if (b < e) {
        if (b[0] == 'a') {
            if (b+3 == e && b[1] == 'm' && b[2] == 'p')
                return '&'; /* &amp; */
            else if (b+4 == e && b[1] == 'p' && b[2] == 'o' && b[3] == 's')
                return '\''; /* &apos; */
        } else if (b[0] == 'g' && b+2 == e && b[1] == 't')
            return '>'; /* &gt; */
        else if (b[0] == 'l' && b+2 == e && b[1] == 't')
            return '<'; /* &lt; */
        else if (b[0] == 'q' && b+4 == e && b[1] == 'u' && b[2] == 'o' &&
                 b[3] == 't')
            return '"'; /* &quot; */
        else if (b[0] == '#') {
            /* character entity */
            const CHAR_T *p;
            int ch = 0;
            b++;
            if (b >= e || *b != 'x')
                for (p = b; p < e; p++) {
                    if (*p >= '0' && *p <= '9')
                        ch = ch*10 + (*p - '0');
                    else
                        break; /* malformed */
                }
            else {
                /* hexadecimal escape */
                int digit;
                for (p = b+1; p < e; p++) {
                    if (*p >= '0' && *p <= '9')
                        digit = *p - '0';
                    else if (*p >= 'a' && *p <= 'f')
                        digit = *p - 'a' + 10;
                    else if (*p >= 'A' && *p <= 'F')
                        digit = *p - 'A' + 10;
                    else
                        break; /* malformed */
                    ch = ch*16 + digit;
                }
            }
            return ch;
        }
    }
    return -1; /* malformed */
}

static Py_ssize_t
fastfeed(FastParserObject* self)
{
    CHAR_T *end; /* tail */
    CHAR_T *p, *q, *s; /* scanning pointers */
    CHAR_T *b, *t, *e; /* token start/end */

    int token;

    s = q = p = self->buffer;
    end = self->buffer + self->bufferlen;

    while (p < end) {

        q = p; /* start of token */

        if (*p == '<') {
            int has_attr;

            /* <tags> */
            token = TAG_START;
            if (++p >= end)
                goto eol;

            if (*p == '!') {
                /* <! directive */
                if (++p >= end)
                    goto eol;
                token = DIRECTIVE;
                b = t = p;
                if (*p == '-') {
                    /* <!-- comment --> */
                    token = COMMENT;
                    b = p + 2;
                    for (;;) {
                        if (p+3 >= end)
                            goto eol;
                        if (p[1] != '-')
                            p += 2; /* boyer moore, sort of ;-) */
                        else if (p[0] != '-' || p[2] != '>')
                            p++;
                        else
                            break;
                    }
                    e = p;
                    p += 3;
                    goto eot;
                } else if (self->xml) {
                    /* FIXME: recognize <!ATTLIST data> ? */
                    /* FIXME: recognize <!ELEMENT data> ? */
                    /* FIXME: recognize <!ENTITY data> ? */
                    /* FIXME: recognize <!NOTATION data> ? */
                    if (*p == 'D' ) {
                        /* FIXME: make sure this really is a !DOCTYPE tag */
                        /* <!DOCTYPE data> or <!DOCTYPE data [ data ]> */
                        token = DOCTYPE;
                        self->doctype = MAYBE;
                    } else if (*p == '[') {
                        /* FIXME: make sure this really is a ![CDATA[ tag */
                        /* FIXME: recognize <![INCLUDE */
                        /* FIXME: recognize <![IGNORE */
                        /* <![CDATA[data]]> */
                        token = CDATA;
                        b = t = p + 7;
                        for (;;) {
                            if (p+3 >= end)
                                goto eol;
                            if (p[1] != ']')
                                p += 2;
                            else if (p[0] != ']' || p[2] != '>')
                                p++;
                            else
                                break;
                        }
                        e = p;
                        p += 3;
                        goto eot;
                    }
                }
            } else if (*p == '?') {
                token = PI;
                if (++p >= end)
                    goto eol;
            } else if (*p == '/') {
                /* </endtag> */
                token = TAG_END;
                if (++p >= end)
                    goto eol;
            } else if (ISSPACE(*p))
                continue;

            /* process tag name */
            b = p;
            if (!self->xml)
                while (ISALNUM(*p) || *p == '-' || *p == '.' ||
                       *p == ':' || *p == '?') {
                    *p = TOLOWER(*p);
                    if (++p >= end)
                        goto eol;
                }
            else
                while (*p != '>' && !ISSPACE(*p) && *p != '/' && *p != '?') {
                    if (++p >= end)
                        goto eol;
                }

            t = p;

            has_attr = 0;

            if (*p == '/' && !self->xml) {
                /* <tag/data/ or <tag/> */
                token = TAG_START;
                e = p;
                if (++p >= end)
                    goto eol;
                if (*p == '>') {
                    /* <tag/> */
                    token = TAG_EMPTY;
                    if (++p >= end)
                        goto eol;
                } else
                    /* <tag/data/ */
                    self->shorttag = SURE;
                    /* we'll generate an end tag when we stumble upon
                       the end slash */

            } else {

                /* skip attributes */
                int quote = 0;
                int last = 0;
                while ((*p != '>' && *p != '<') || quote) {
                    if (!ISSPACE(*p)) {
                        has_attr = 1;
                        /* FIXME: note: end tags cannot have attributes! */
                    }
                    if (quote) {
                        if (*p == quote)
                            quote = 0;
                    } else {
                        if (*p == '"' || *p == '\'')
                            quote = *p;
                    }
                    if (*p == '[' && !quote && self->doctype) {
                        self->doctype = SURE;
                        token = DTD_START;
                        e = p++;
                        goto eot;
                    }
                    last = *p;
                    if (++p >= end)
                        goto eol;
                }

                if (*p == '<')
                    e = p;
                else
                    e = p++;

                if (last == '/') {
                    /* <tag/> */
                    e--;
                    token = TAG_EMPTY;
                } else if (token == PI && last == '?')
                    e--;

                if (self->doctype == MAYBE)
                    self->doctype = 0; /* there was no dtd */

                if (has_attr)
                    ; /* FIXME: process attributes */

            }

        } else if (*p == '/' && self->shorttag) {

            /* end of shorttag. this generates an empty end tag */
            token = TAG_END;
            self->shorttag = 0;
            b = t = e = p;
            if (++p >= end)
                goto eol;

        } else if (*p == ']' && self->doctype) {

            /* end of dtd. this generates an empty special tag,
               followed by a > data tag */
            token = DTD_END;
            b = t = e = p;
            if (++p >= end)
                goto eol;
            self->doctype = 0;

        } else if (*p == '%' && self->doctype) {

            /* doctype entities */
            token = DTD_ENTITY;
            if (++p >= end)
                goto eol;
            b = t = p;
            while (*p != ';' && !ISSPACE(*p))
                if (++p >= end)
                    goto eol;
            e = p;
            if (*p == ';')
                p++;

        } else if (*p == '&') {

            /* entities */
            token = ENTITYREF;
            if (++p >= end)
                goto eol;
            if (*p == '#') {
                token = CHARREF;
                if (++p >= end)
                    goto eol;
            } else if (ISSPACE(*p))
                continue;
            b = t = p;
            while (*p != ';' && *p != '<' && *p != '>' && !ISSPACE(*p))
                if (++p >= end)
                    goto eol;
            e = p;
            if (*p == ';')
                p++;

        } else {

            /* raw data */
            if (++p >= end) {
                q = p;
                goto eol;
            }
            continue;

        }

      eot: /* end of token */

        if (q != s && self->handle_data) {
            /* flush any raw data before this tag */
            PyObject* res;
            res = PyObject_CallFunction(
                self->handle_data, BUILDFORMAT, s, q-s
                );
            if (!res)
                return -1;
            Py_DECREF(res);
        }

        /* invoke callbacks */
        if (token & TAG) {
            if (token == TAG_END) {
                if (self->handle_endtag) {
                    PyObject* res;
                    res = PyObject_CallFunction(
                        self->handle_endtag, BUILDFORMAT, b, t-b
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                }
            } else if (token == DIRECTIVE || token == DOCTYPE ||
                       token == DTD_START || token == DTD_ENTITY ||
                       token == DTD_END) {
                if (self->handle_special) {
                    PyObject* res;
                    res = PyObject_CallFunction(
                        self->handle_special, BUILDFORMAT, b, e-b
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                }
            } else if (token == PI) {
                if (self->handle_proc) {
                    PyObject* res;
                    Py_ssize_t len = t-b;
                    while (ISSPACE(*t))
                        t++;
                    res = PyObject_CallFunction(
                        self->handle_proc, BUILDFORMAT BUILDFORMAT,
                        b, len, t, e-t
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                }
            } else if (token == TAG_START || token == TAG_EMPTY) {
                if (self->handle_enterstarttag) {
                    PyObject* res;
                    int attr;
                    Py_ssize_t len = t-b;
                    if (self->check && !self->check->starttag(
                        self->check, b, t
                        ))
                    return -1;
                    while (ISSPACE(*t))
                        t++;
                    res = PyObject_CallFunction(
                        self->handle_enterstarttag, BUILDFORMAT, b, len
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                    attr = attrparse(self, t, e);
                    if (attr)
                        return -1;
                    if (self->handle_leavestarttag) {
                        res = PyObject_CallFunction(
                            self->handle_leavestarttag, BUILDFORMAT, b, len
                            );
                        if (!res)
                            return -1;
                        Py_DECREF(res);
                    }
                    if (token == TAG_EMPTY && self->handle_endtag) {
                        if (self->check && !self->check->endtag(
                            self->check, b, b+len
                            ))
                            return -1;
                        res = PyObject_CallFunction(
                            self->handle_endtag, BUILDFORMAT, b, len
                            );
                        if (!res)
                            return -1;
                        Py_DECREF(res);
                    }
                }
            } else {
                /* can this really happen? */
                PyErr_Format(
                    PyExc_RuntimeError, "unknown token: 0x%x", token
                    );
                return -1;
            }
        } else if (token == ENTITYREF) {
            CHAR_T ch;
            int charref;
  entity:
            if (self->handle_entityref) {
                PyObject* res;
                if (self->check && !self->check->entityref(self->check, b, e))
                    return -1;
                res = PyObject_CallFunction(
                    self->handle_entityref, BUILDFORMAT, b, e-b
                    );
                if (!res)
                    return -1;
                Py_DECREF(res);
                goto next;
            }
            /* check for standard entity */
            charref = entity(b, e);
            if (charref > 0) {
                if (self->handle_data) {
                    PyObject* res;
                    /* all builtin entities fit in a CHAR_T */
                    ch = (CHAR_T) charref;
                    res = PyObject_CallFunction(
                        self->handle_data, BUILDFORMAT, &ch, 1
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                    goto next;
                }
            }
            if (self->handle_data && self->strict) {
                /* if the user wants data, but we cannot resolve this
                   entity, flag it as configuration error */
                PyErr_SetString(
                    PyExc_SyntaxError, "unresolvable entity"
                    );
                return -1;
            }
        } else if (token == CHARREF && (self->handle_charref ||
                                        self->handle_data)) {
            if (self->check && !self->check->charref(self->check, b, e))
                return -1;
            if (self->handle_charref) {
                PyObject* res;
                res = PyObject_CallFunction(
                    self->handle_charref, BUILDFORMAT, b, e-b
                    );
                if (!res)
                    return -1;
                Py_DECREF(res);
            } else {
                /* fallback: handle charref's as data */
                CHAR_T ch;
                int charref = entity(b-1, e);
                if (charref < 0) {
                    b--;
                    goto entity;
                }
                #ifndef SGMLOP_UNICODE_SUPPORT
                if (charref > 255) {
                    /* FIXME: return as unicode */
                    if (self->handle_data && self->strict) {
                        /* if the user wants data, but we cannot resolve this
                           entity, flag it as configuration error */
                        PyErr_SetString(
                            PyExc_SyntaxError, "character entity too large"
                            );
                        return -1;
                    }
                } else
                #endif
                {
                    PyObject* res;
                    ch = charref;
                    res = PyObject_CallFunction(
                        self->handle_data, BUILDFORMAT, &ch, 1
                        );
                    if (!res)
                        return -1;
                    Py_DECREF(res);
                }
            }
        } else if (token == CDATA && (self->handle_cdata ||
                                      self->handle_data)) {
            PyObject* res;
            if (self->handle_cdata) {
                res = PyObject_CallFunction(
                    self->handle_cdata, BUILDFORMAT, b, e-b
                    );
            } else {
                /* fallback: handle cdata as plain data */
                res = PyObject_CallFunction(
                    self->handle_data, BUILDFORMAT, b, e-b
                    );
            }
            if (!res)
                return -1;
            Py_DECREF(res);
        } else if (token == COMMENT && self->handle_comment) {
            PyObject* res;
            if (self->check && !self->check->comment(self->check, b, e))
                return -1;
            res = PyObject_CallFunction(
                self->handle_comment, BUILDFORMAT, b, e-b
                );
            if (!res)
                return -1;
            Py_DECREF(res);
        }
  next:
        q = p; /* start of token */
        s = p; /* start of span */
    }

  eol: /* end of line */
    if (q != s && self->handle_data) {
        PyObject* res;
        res = PyObject_CallFunction(self->handle_data, BUILDFORMAT, s, q-s);
        if (!res)
            return -1;
        Py_DECREF(res);
    }

    /* returns the number of characters consumed in this pass */
    return q - self->buffer;
}

int handle_data(FastParserObject* self, const CHAR_T* b, const CHAR_T* e)
{
    if (self->handle_data && b != e) {
        PyObject* res = PyObject_CallFunction(
            self->handle_data, BUILDFORMAT, b, e-b
        );
        if (!res)
            return -1;
        Py_DECREF(res);
    }
    return 0;
}

int handle_entityref(FastParserObject* self, const CHAR_T* b, const CHAR_T* e)
{
    int code = entity(b, e);
    if (code == -1) {
        if (self->handle_entityref) {
            PyObject* res = PyObject_CallFunction(
                self->handle_entityref, BUILDFORMAT, b, e-b
            );
            if (!res)
                return -1;
            Py_DECREF(res);
        }
    } else {
        CHAR_T c = code;
        return handle_data(self, &c, &c+1);
    }
    return 0;
}

static int
attrparse(FastParserObject* self, const CHAR_T* p, const CHAR_T* end)
{
    PyObject* key = NULL;
    const CHAR_T* q;

    while (p < end) {

        /* skip leading space */
        while (p < end && ISSPACE(*p))
            p++;
        if (p >= end)
            break;

        /* get attribute name (key) */
        q = p;
        while (p < end && *p != '=' && !ISSPACE(*p))
            p++;

        key = BUILDSTRING(q, p-q);
        if (key == NULL)
            goto err;

        if (self->handle_enterattr) {
            PyObject* res = PyObject_CallFunction(
                self->handle_enterattr, "O", key
                );
            if (!res)
                goto err;
            Py_DECREF(res);
        }

        while (p < end && ISSPACE(*p))
            p++;

        if (p < end && *p == '=') {
            CHAR_T quote;
            int is_entity = 0;
            /* attribute value found */

            if (p < end)
                p++;
            while (p < end && ISSPACE(*p))
                p++;

            if (p < end) {
                if (*p == '"' || *p == '\'')
                    quote = *p++;
                else
                    quote = 0;
                q = p;
                while (p < end && (quote ? (*p != quote) : !ISSPACE(*p)) && *p != '>') {
                    if (!is_entity && *p == '&') {
                        if (handle_data(self, q, p))
                            goto err;
                        is_entity = 1;
                        q = ++p;
                    }
                    else if (is_entity && *p == ';') {
                        if (handle_entityref(self, q, p))
                            goto err;
                        is_entity = 0;
                        q = ++p;
                    }
                    else
                        p++;
                }
                if (is_entity) {
                    if (handle_entityref(self, q, p))
                        goto err;
                } else {
                    if (handle_data(self, q, p))
                        goto err;
                }
                if (quote)
                    p++;
            }
        }
        else {
            /* No attribute value */
            if (!self->xml && self->handle_data) {
                PyObject* res = PyObject_CallFunction(
                    self->handle_data, "O", key
                );
                if (!res)
                    goto err;
                Py_DECREF(res);
            }
        }
        if (self->handle_leaveattr) {
            PyObject* res = PyObject_CallFunction(
                self->handle_leaveattr, "O", key
                );
            if (!res)
                goto err;
            Py_DECREF(res);
        }
        Py_DECREF(key);
        key = NULL;
    }

    return 0;

  err:
    Py_XDECREF(key);
    return -1;
}
