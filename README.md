

Note that all of the scripts access python3.  Make sure that your system has
python3 installed.

REPO is the location of this repository.


Installation instructions:

	cd ${REPO}/open
	python setup.py sdist
	pip install .

	The setup.py call will create a source distribution of the code.
	The pip call will install it in site-packages.  (Need root for this command.)


Run instructions:

	export CONF=${1}
	rm -rf ${CONF}.pp ${CONF}.route
	zfmroute.py -c ${REPO}/open/env/${CONF}.conf -r ${HOME}/${CONF}.route > ${HOME}/${CONF}.pp

	The first export statement isn't necessary.  I use it in a script whereby I set the
	CONF to the command line parameter.

