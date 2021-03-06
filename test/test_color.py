#! /usr/bin/env/python
# -*- coding: utf-8 -*-
# cython: language_level=3, always_allow_keywords=True

## Copyright 2009-2017 by LivingLogic AG, Bayreuth/Germany
## Copyright 2009-2017 by Walter Dörwald
##
## All Rights Reserved
##
## See ll/xist/__init__.py for the license


from ll import color


def test_constructor():
	assert color.Color(10, 20, 30) == (10, 20, 30, 255)
	assert color.Color(40, 50, 60, 70) == (40, 50, 60, 70)


def test_fromcss():
	assert color.Color.fromcss("red") == (0xff, 0x0, 0x0, 0xff)
	assert color.Color.fromcss("#123") == (0x11, 0x22, 0x33, 0xff)
	assert color.Color.fromcss("#123456") == (0x12, 0x34, 0x56, 0xff)
	assert color.Color.fromcss("#abcdef") == (0xab, 0xcd, 0xef, 0xff)
	assert color.Color.fromcss("#ABCDEF") == (0xab, 0xcd, 0xef, 0xff)
	assert color.Color.fromcss("rgb(12, 34, 56)") == (12, 34, 56, 0xff)
	assert color.Color.fromcss("rgb(20%, 40%, 60%)") == (0x33, 0x66, 0x99, 0xff)
	assert color.Color.fromcss("rgba(12, 34, 56, 0)") == (12, 34, 56, 0x0)
	assert color.Color.fromcss("rgba(12, 34, 56, 1)") == (12, 34, 56, 0xff)
	assert color.Color.fromcss("rgba(20%, 40%, 60%, 0)") == (0x33, 0x66, 0x99, 0x0)
	assert color.Color.fromcss("rgba(20%, 40%, 60%, 1)") == (0x33, 0x66, 0x99, 0xff)


def test_fromrgb():
	assert color.Color.fromrgb(0.2, 0.4, 0.6, 0.8) == color.Color(0x33, 0x66, 0x99, 0xcc)


def test_repr():
	assert repr(color.red) == "Color(0xff, 0x00, 0x00)"
	assert repr(color.Color(0x12, 0x34, 0x56, 0x78)) == "Color(0x12, 0x34, 0x56, 0x78)"


def test_str():
	assert str(color.Color(0x12, 0x34, 0x56)) == "#123456"
	assert str(color.Color(0x12, 0x34, 0x56, 0x78)) == "rgba(18,52,86,0.471)"


def test_r_g_b():
	c = color.Color(0x12, 0x34, 0x56, 0x78)
	assert c.r() == 0x12
	assert c.g() == 0x34
	assert c.b() == 0x56
	assert c.a() == 0x78


def test_rgb():
	assert color.Color(0x33, 0x66, 0x99, 0xcc).rgb() == (0.2, 0.4, 0.6)


def test_rgba():
	assert color.Color(0x33, 0x66, 0x99, 0xcc).rgba() == (0.2, 0.4, 0.6, 0.8)


def test_combine():
	assert color.Color(0x12, 0x34, 0x56).combine(r=0x78) == (0x78, 0x34, 0x56, 0xff)
	assert color.Color(0x12, 0x34, 0x56).combine(g=0x78) == (0x12, 0x78, 0x56, 0xff)
	assert color.Color(0x12, 0x34, 0x56).combine(b=0x78) == (0x12, 0x34, 0x78, 0xff)
	assert color.Color(0x12, 0x34, 0x56).combine(a=0x78) == (0x12, 0x34, 0x56, 0x78)


def test_mul():
	assert 2*color.Color(0x12, 0x34, 0x56) == color.Color(0x24, 0x68, 0xac)
	assert color.Color(0x12, 0x34, 0x56)*2 == color.Color(0x24, 0x68, 0xac)


def test_truediv():
	assert color.Color(0x24, 0x68, 0xac)/2 == color.Color(0x12, 0x34, 0x56)


def test_floordiv():
	assert color.Color(0x25, 0x69, 0xad)//2 == color.Color(0x12, 0x34, 0x56)


def test_mod():
	assert color.Color(0x80, 0x80, 0x80) % color.Color(0xff, 0xff, 0xff) == color.Color(0x80, 0x80, 0x80)
	assert color.Color(0x80, 0x80, 0x80, 0x00) % color.Color(0xff, 0xff, 0xff) == color.Color(0xff, 0xff, 0xff)
	assert color.Color(0x80, 0x80, 0x80, 0x80) % color.Color(0xff, 0xff, 0xff) == color.Color(0xbf, 0xbf, 0xbf)
