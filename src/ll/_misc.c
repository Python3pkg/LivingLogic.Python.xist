/*
** Copyright 2007-2008 by LivingLogic AG, Bayreuth, Germany.
** Copyright 2007-2008 by Walter D�rwald
**
** All Rights Reserved
**
** See __init__.py for the license
*/


#include "Python.h"


static PyObject *item(PyObject *self, PyObject *args)
{
	PyObject *iterable;
	Py_ssize_t index;
	PyObject *defaultobj = NULL;
	PyObject *iter;
	if (!PyArg_ParseTuple(args, "On|O:item", &iterable, &index, &defaultobj))
		return NULL;

	iter = PyObject_GetIter(iterable);
	if (!iter)
		return NULL;
	if (index >= 0)
	{
		for (;;)
		{
			PyObject *element = PyIter_Next(iter);
			if (!element)
			{
				Py_DECREF(iter);
				if (PyErr_Occurred())
					return NULL;
				if (defaultobj)
				{
					PyErr_Clear();
					Py_INCREF(defaultobj);
				}
				else
					PyErr_SetString(PyExc_IndexError, "iterator didn't produce enough elements");
				return defaultobj;
			}
			if (!index)
			{
				/* this is the index'th element => return it */
				Py_DECREF(iter);
				return element;
			}
			Py_DECREF(element);
			--index;
		}
		return NULL;
	}
	else
	{
		Py_ssize_t size;
		Py_ssize_t count; /* used by the deallocation code */
		PyObject *result = NULL;
		/* We keep the last abs(index) elements in this circular buffer */
		PyObject **buffer;
		Py_ssize_t headindex = 0;
		index = -index;
		size = index*sizeof(PyObject *);
		if (size/sizeof(PyObject *) != index)
		{
			PyErr_SetString(PyExc_OverflowError, "index too large");
			return NULL;
		}
		buffer = (PyObject **)PyMem_Malloc(size);
		if (!buffer)
			return NULL;
		memset(buffer, 0, size);
		for (;;)
		{
			PyObject *element = PyIter_Next(iter);
			if (++headindex >= index)
				headindex = 0;
			if (!element){
				Py_DECREF(iter);
				if (PyErr_Occurred())
					goto finished;
				/* iterator exhausted, so check if there's an object in the *next*
				 * slot in the ringbuffer (which is the "oldest" object we fetched
				 * from the iterator) */
				if (buffer[headindex])
				{
					result = buffer[headindex];
					/* because the dealloc code will do a decref for all objects */
					Py_INCREF(result);
					goto finished;
				}
				if (defaultobj)
				{
					PyErr_Clear();
					Py_INCREF(defaultobj);
					result = defaultobj;
				}
				else
					PyErr_SetString(PyExc_IndexError, "iterator didn't produce enough elements");
				goto finished;
			}
			else
			{
				/* drop oldest object from the ringbuffer */
				if (buffer[headindex])
				{
					Py_DECREF(buffer[headindex]);
				}
				buffer[headindex] = element;
			}
		}
		finished:
		for (count = index; count; --count)
		{
			if (--headindex < 0)
				headindex = index-1;
			if (!buffer[headindex])
				break;
			Py_DECREF(buffer[headindex]);
		}
		PyMem_Free(buffer);
		return result;
	}
}


PyDoc_STRVAR(item_doc,
"Returns the :var:`index`'th element from the iterable. :var:`index` may be\n\
negative to count from the end. E.g. 0 returns the first element produced by\n\
the iterator, 1 the second, -1 the last one etc. If :var:`index` is negative\n\
the iterator will be completely exhausted, if it's positive it will be\n\
exhausted up to the :var:`index`'th element. If the iterator doesn't produce\n\
that many elements :exc:`IndexError` will be raised, except when\n\
:var:`default` is given, in which case :var:`default` will be returned.");


static PyObject *first(PyObject *self, PyObject *args)
{
	PyObject *iterable;
	PyObject *element;
	PyObject *defaultobj = NULL;
	PyObject *iter;
	if (!PyArg_ParseTuple(args, "O|O:first", &iterable, &defaultobj))
		return NULL;

	iter = PyObject_GetIter(iterable);
	if (!iter)
		return NULL;
	element = PyIter_Next(iter);
	if (!element)
	{
		Py_DECREF(iter);
		if (PyErr_Occurred())
			return NULL;
		if (defaultobj)
		{
			PyErr_Clear();
			Py_INCREF(defaultobj);
		}
		else
			PyErr_SetString(PyExc_IndexError, "iterator didn't produce an element");
		return defaultobj;
	}
	Py_DECREF(iter);
	return element;
}


PyDoc_STRVAR(first_doc,
"Return the first element from the iterable. If the iterator doesn't produce\n\
any elements :exc:`IndexError` will be raised, except when :var:`default` is\n\
given, in which case :var:`default` will be returned.");


static PyObject *last(PyObject *self, PyObject *args)
{
	PyObject *iterable;
	PyObject *defaultobj = NULL;
	PyObject *iter;
	PyObject *lastelement = NULL;
	if (!PyArg_ParseTuple(args, "O|O:last", &iterable, &defaultobj))
		return NULL;

	iter = PyObject_GetIter(iterable);
	if (!iter)
		return NULL;

	for (;;)
	{
		PyObject *element = PyIter_Next(iter);
		if (element)
		{
			Py_XDECREF(lastelement);
			lastelement = element;
		}
		else
		{
			Py_DECREF(iter);
			if (PyErr_Occurred())
				Py_XDECREF(lastelement);
			else
			{
				if (lastelement)
					return lastelement;
				else if (defaultobj)
				{
					Py_INCREF(defaultobj);
					return defaultobj;
				}
				else
					PyErr_SetString(PyExc_IndexError, "iterator didn't produce any elements");
			}
			return NULL;
		}
	}
}


PyDoc_STRVAR(last_doc,
"Return the last element from the iterable. If the iterator doesn't produce\n\
any elements :exc:`IndexError` will be raised, except when :var:`default` is\n\
given, in which case :var:`default` will be returned.");


static PyObject *count(PyObject *self, PyObject *iterable)
{
	Py_ssize_t count = 0;
	PyObject *iter = PyObject_GetIter(iterable);
	if (!iter)
		return NULL;

	for (;;)
	{
		PyObject *element = PyIter_Next(iter);
		if (element)
		{
			++count;
			Py_DECREF(element);
		}
		else
		{
			Py_DECREF(iter);
			if (PyErr_Occurred())
				return NULL;
			return PyInt_FromSize_t(count);
		}
	}
}


PyDoc_STRVAR(count_doc,
"Count the number of elements produced by the iterable. Calling this function\n\
will exhaust the iterator.");


static PyMethodDef _functions[] = {
	{"item",  (PyCFunction)item,  METH_VARARGS, item_doc},
	{"first", (PyCFunction)first, METH_VARARGS, first_doc},
	{"last",  (PyCFunction)last,  METH_VARARGS, last_doc},
	{"count", (PyCFunction)count, METH_O,       count_doc},
	{NULL,     NULL} /* sentinel */
};

static char module__doc__[] =
"This module contains the functions :func:`item` :func:`first`, :func:`last`\n\
and :func:`count`.";


PyMODINIT_FUNC
init_misc(void)
{
	Py_InitModule3("_misc", _functions, module__doc__);
}