# $Header$

# List of pseudo targets
.PHONY: all test install clean dist windist

all:
	python$(PYVERSION) setup.py install

test: all
	py.test

clean:
	python$(PYVERSION) setup.py clean

dist: test
	python$(PYVERSION) `which doc2txt.py` --title History NEWS.xml NEWS
	python$(PYVERSION) `which doc2txt.py` --title "Requirements and installation" INSTALL.xml INSTALL
	python$(PYVERSION) `which doc2txt.py` --title "Howto" HOWTO.xml HOWTO
	python$(PYVERSION) `which doc2txt.py` --title "Examples" EXAMPLES.xml EXAMPLES
	python$(PYVERSION) `which doc2txt.py` --title "Migration and modernization guide" MIGRATION.xml MIGRATION
	python$(PYVERSION) setup.py sdist --formats=bztar,gztar
	python$(PYVERSION) setup.py bdist --formats=egg
	rm NEWS INSTALL HOWTO EXAMPLES MIGRATION

register:
	python$(PYVERSION) setup.py register

upload:
	python$(PYVERSION) setup.py sdist --formats=bztar,gztar upload
	python$(PYVERSION) setup.py bdist --formats=egg upload

windist:
	python$(PYVERSION) C:\\\\Programme\\\\Python24\\\\Scripts\\\\doc2txt.py --title History NEWS.xml NEWS
	python$(PYVERSION) C:\\\\Programme\\\\Python24\\\\Scripts\\\\doc2txt.py --title "Requirements and installation" INSTALL.xml INSTALL
	python$(PYVERSION) C:\\\\Programme\\\\Python24\\\\Scripts\\\\doc2txt.py --title "Howto" HOWTO.xml HOWTO
	python$(PYVERSION) C:\\\\Programme\\\\Python24\\\\Scripts\\\\doc2txt.py --title "Examples" EXAMPLES.xml EXAMPLES
	python$(PYVERSION) C:\\\\Programme\\\\Python24\\\\Scripts\\\\doc2txt.py --title "Migration and modernization guide" MIGRATION.xml MIGRATION
	python$(PYVERSION) setup.py sdist --formats=zip
	python$(PYVERSION) setup.py bdist --formats=wininst
	python$(PYVERSION) setup.py bdist --formats=egg
	rm NEWS INSTALL HOWTO EXAMPLES MIGRATION

livinglogic:
	python$(PYVERSION) `which doc2txt.py` --title History NEWS.xml NEWS
	python$(PYVERSION) `which doc2txt.py` --title "Requirements and installation" INSTALL.xml INSTALL
	python$(PYVERSION) `which doc2txt.py` --title "Howto" HOWTO.xml HOWTO
	python$(PYVERSION) `which doc2txt.py` --title "Examples" EXAMPLES.xml EXAMPLES
	python$(PYVERSION) `which doc2txt.py` --title "Migration and modernization guide" MIGRATION.xml MIGRATION
	python$(PYVERSION) setup.py sdist --formats=bztar,gztar
	python$(PYVERSION) setup.py bdist --formats=egg
	scp dist/*.tar.gz dist/*.tar.bz2 dist/*.egg intranet@intranet.livinglogic.de:~/documentroot/intranet.livinglogic.de/python-downloads/
	rm NEWS INSTALL HOWTO EXAMPLES MIGRATION
