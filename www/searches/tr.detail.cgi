#!/usr/local/bin/python

# Program: tr.detail.cgi
# Purpose: Displays details of a tracking record, either singly or as part of a
#	series of tracking records.
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	7.1-7.3
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: three optional fields as via a GET or POST submission:  TR_Nr
#		(a strings containing either a single tracking record number or
#		a comma-separated sequence of tracking record numbers);
#		Prev_TR_Screen (a string containing an integer (boolean 0/1)
#		denoting whether or not the last screen displayed was a
#		tracking record detail screen, and thus whether we should show
#		a Previous button or not); and, Expanded (which, if present
#		indicates that we should show an expanded detail page)
#	Outputs: An HTML page (a tracking record detail screen) is sent to
#		stdout, containing two tables of info for the first tracking
#		record specified in TR_Nr.  A Next button would display a
#		similar page for the next tracking record in TR_Nr.  An Edit
#		button would edit the displayed tracking record.  If
#		Prev_TR_Button is 1, then a Previous button is included which
#		would tell the browser to go back to the previous screen.  The
#		top table includes TR #, the current date and time, and the
#		tracking record's title.  The lower table contains the other
#		small data fields:  Area, Type, Staff, etc.  Below the lower
#		table are the two large text fields (Project Definition,
#		Progress Notes) and the Status History (if there is one).  If
#		we are showing an expanded detail page, then tables detailing
#		dependency information appear between the tables and the text
#		fields.
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
import screenlib	# generates needed HTML screens

try:
	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# put it in a dictionary

	# to allow the input fieldnames to be case-insensitive, let's
	# duplicate each input field with a lowercase fieldname equivalent:

	for key in dict.keys ():
		dict [ string.lower (key) ] = dict [key]

	# If there was a previous tracking record detail screen, then there
	# will be a 'prev tr screen' field in the input.  This will let us know
	# whether or not (1/0) we need to display a Previous button or not.

	if dict.has_key ('prev tr screen'):
		prev_tr = string.atoi (dict ['prev tr screen'])
	else:
		prev_tr = 0	# no previous screen --> no Previous button

	# convert a 'tr' parameter (if there is one) to the standard 'tr nr':

	if dict.has_key ('tr'):
		dict ['tr nr'] = copy.deepcopy (dict ['tr'])
		del dict['tr']

	# Look to see if there's a list of tracking records yet to be displayed
	# (passed in field 'tr nr').  If not, present a message stating that.

	if not dict.has_key ('tr nr'):
		screenlib.gen_Message_Screen (
			'WTS: No Tracking Records to Display',
			'No records were selected for display.  Please ' + \
			'press Ok to go back to the previous screen.', 1)
	else:
		tr_list = str (dict ['tr nr'])	# list of tracking records yet
						# to be displayed

		# Try to display the next tracking record in tr_list.  If an
		# exception occurs, that means that we couldn't find that
		# tracking record in the database.

		try:
			doc = screenlib.TrackRec_Detail_Screen ()
			doc.setup (tr_list, prev_tr, dict.has_key ('expanded'))
			doc.write ()
		except ValueError:
			# we need to find out what tracking record number we
			# tried to retrieve.  It's the first one in tr_list:

			tr_num = '(TR%s)' % string.split (tr_list)[0]

			screenlib.gen_Message_Screen (
				'WTS: Can''t Find Tracking Record',
				('The specified tracking record %s ' % tr_num) \
				+ 'does not exist.  Please press Ok to go ' + \
				'back to the previous screen.', 1)
except:
	screenlib.gen_Exception_Screen ('tr.detail.cgi')
