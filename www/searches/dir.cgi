#!/usr/local/bin/python

# Program: dir.cgi
# Purpose: This script serves as a gateway to the project directories and
#	their contents.  It saves the user from having to know the right URL
#	for a given tracking record's project directory, and will allow us in
#	the future to change the directory structure without breaking any links
#	(as long as all links go through this gateway script).
# User Requirements Satisfied by This Program:
#	None
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface,
#		with parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Inputs: two fields via a GET or POST submission:  TR_Nr (the integer
#		tracking record number whose directory we need to access) and
#		doc (optional; the string filename to display)
#	Outputs: A blank HTML page is sent to stdout as a response to the
#		submission.  It contains Javascript code needed to immediately
#		replace itself with the correct URL for the input data.
#	Exit Codes: none
#	Other System Requirements: none
# Assumes: nothing
# Implementation:
#	As with all WTS CGI scripts, the main code for this one is wrapped in a
#	try..except statement.  This ensures that we can present an Exception
#	Screen for the user rather than having a hard crash.  (Both are
#	undesirable and should not happen under normal operating circumstances.)

import os
import sys
import cgi
import copy
import string
import Configuration
import wtslib		# provides auxiliary functions
import TrackRec		# provides access to tracking record information and a
			# means of manipulating tracking record data
import screenlib	# provides a means of generating the HTML screen

try:
	# get input values, and convert them to a regular dictionary.

	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# convert to dictionary

	# replicate the keys in "dict" so that they have all-lowercase
	# equivalents in there, too.

	for key in dict.keys ():
		dict [ string.lower (key) ] = dict [key]

	# convert a 'tr' parameter (if there is one) to the standard 'tr nr':

	if dict.has_key ('tr'):
		dict ['tr nr'] = copy.deepcopy (dict ['tr'])
		del dict['tr']

	# the tracking record key must be specified, otherwise it's an error

	if dict.has_key ('tr nr'):
		tr_num = string.atoi (string.strip (dict ['tr nr']) )

		# get the directory for that tracking record

		dir = TrackRec.directoryOf (tr_num)
		if dir is not None:
			dir = os.path.join (Configuration.config ['baseURL'],
				dir)
			if dict.has_key ('doc'):
				dir = os.path.join (dir, dict ['doc'])

			screen = screenlib.GoTo_Screen (onLoad = 'go_to ()')
			screen.setup (dir)
			screen.write ()
		else:
			screenlib.gen_Message_Screen (
				'TR %d Has No Project Directory' % tr_num,
				'''There is no defined project directory for
				tracking record number TR %d''' % tr_num)
	else:
		screenlib.gen_Message_Screen ('Missing TR #',
			'''The dir.cgi script requires a "TR_Nr" argument.
			There must be an error in the link you followed.''')
except:
	screenlib.gen_Exception_Screen ('tr.bailout.cgi')
