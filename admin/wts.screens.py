#!/usr/local/bin/python

# Program: wts.screens.py
# Purpose: provides command-line options for re-generating the home page,
#	query form, and help screens for WTS.
# User Requirements Satisfied by This Program:
#	see WTS User Requirements document, functional requirements 1, 5
# System Requirements Satisfied by This Program:
#	Usage: see global variable USAGE defined below
#	Uses: Python 1.4, HTMLgen 2.0.6,
#		WTS modules: TrackRec, Controlled_Vocab, Configuration,
#			screenlib
#	Envvars: none
#	Inputs: may specify the destination directory (for the created files)
#		at the command line.  Controlled vocabulary information comes
#		from the database.
#	Outputs: html files in the destination directory, depending on command
#		line options, may include:  home page (index.html), query form
#		(tr.query.html), and help files (cv.*.html and tr.*.html)
#	Exit Codes: none
#	Other System Requirements: none
# Assumes: we run this script from the WTS bin directory
# Implementation:
#	Modules:
#		TrackRec - used to map field names to their help files
#		Configuration - used to look up the help file directory
#		Controlled_Vocab - used to load & process the controlled
#			vocabulary field information
#		screeenlib - used in producing the pages (uses WTS_Form,
#			WTS_Document, and Button classes, along with some
#			constants)

USAGE = \
'''
	wts.screens.py [--dir <directory name>][--home][--query][--help][--grid]
		--dir   : sets the destination directory (. by default)
		--home  : generates the home page
		--query : generates the tracking record query page
		--help  : generates the help screens
		--grid  : generates the page for the Status grid query form
'''

import os
import sys
import types
import string

# Since some WTS modules expect the REMOTE_USER environment variable to contain
# the login name of the current user, we'll need to set it using LOGNAME.

os.environ ['REMOTE_USER'] = os.environ ['LOGNAME']

import Configuration
import HTMLgen
import TrackRec
import Controlled_Vocab
import wtslib
import screenlib

PREFIX = Configuration.config ['PREFIX']

class Container:
	# Concept: 
	#	IS: a big bucket into which we can dump HTMLgen objects which
	#		are to be considered as a single conceptual object.  We
	#		view this bucket as that single conceptual object,
	#		without needing to know what other objects it contains.
	#	HAS: a list of HTMLgen objects which comprise the contents of
	#		this Container
	#	DOES: The basic operations of a container include appending
	#		items and giving a string representation of the entire
	#		Container.
	# Implementation:
	#	The only instance variable is named "contents".  It is a list
	#	which contains the HTMLgen objects in this container.
	# Notes:
	#	This construct became necessary as we need to have multiple
	#	HTMLgen objects on a row of a bulleted (or numbered) list.  If
	#	we just use a list of HTMLgen objects to construct the bulleted
	#	list, then each object gets its own bullet.  So, we construct
	#	the bulleted list using a list of Containers, each of which
	#	contains all the HTMLgen objects for a single bullet.

	def __init__ (self,
		*args		# (zero or more) initial items to put in the
				# Container
		):
		# Purpose: initializes a new Container object
		# Returns: nothing
		# Assumes: the items in *args are HTMLgen-compatible (provide
		#	a __str__ method which produces an HTML representation
		#	of the item)
		# Effects: see Purpose.  sets the *args to be the Container's
		#	initial contents.
		# Throws: nothing

		self.contents = list (args)	# initial list of contents


	def append (self,
		item		# item to append to the Container's contents
		):
		# Purpose: appends item to the current contents
		# Returns: nothing
		# Assumes: item is HTMLgen-compatible (provides a __str__
		#	method which produces an HTML representation of item)
		# Effects: appends item to self.contents, the list of items in
		#	this Container.
		# Throws: nothing

		self.contents.append (item)	# add to end of contents


	def __str__ (self):
		# Purpose: retrieve the string representation for the Container,
		#	including all the items in it
		# Returns: a string which is the representation of the
		#	Container (including its items)
		# Assumes: items in self.contents all have a __str__ method
		#	defined
		# Effects: builds and returns a string which represents the
		#	Container and the items within it.
		# Throws: nothing

		s = ''				# initially empty string
		for item in self.contents:	# for each item in the contents
			s = s + str (item)	# add its representation to
						# the string.
		return s			# and return the final s

# ------ END Container Class ------

def gen_Home_Page (
	dir		# string - name of directory in which to create file
	):
	# Purpose: generates the WTS Home Page and writes it to a file (named
	#	'index.html') in dir
	# Returns: nothing
	# Assumes: current user has permission to write in dir
	# Effects: see Purpose.
	# Throws:

	HeadingLevel = 4	# (constant) HTML heading level / size to use
				# for section titles

	# create the document

	doc = screenlib.WTS_Document (cgi = 0,	# this document will go to a
						# file, not a CGI response,
		title = PREFIX + ': Home')	# with specified title.

	# section 1 - Reviewing Tracking Records
	#	add a horizontal rule and then a centered heading

	doc.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Review / Update Tracking Records')))

	# inner list will contain the numbered "quick queries" under the
	# main query bullet

	inner_list = []			# list of quick queries, each of which
					# is a Containe with a link, a
					# description, and a paragraph marker

	# Show Bug List (include bugs, exclude those with a Status of done,
	# cancelled or merged)

	inner_list.append (Container ( \
		HTMLgen.Href ('searches/tr.query.results.cgi?Type=swFix&Not=' +\
			'Status&Status=done&Status=cancelled&Status=merged',
			'Show Bug List'),
		HTMLgen.Small (' - list current tracking records which ' + \
			'have swFix as a Type'),
		HTMLgen.P () ))

	# Show New Tracking Record List

	inner_list.append (Container ( \
		HTMLgen.Href ('searches/tr.query.results.cgi?Status=new', \
			'Show New Tracking Record List'),
		HTMLgen.Small (' - list tracking records with a Status ' + \
			'of new'),
		HTMLgen.P () ))

	# Show My Tracking Record List (include ones set for a staff member of
	# the current user, exclude those with a Status of done, cancelled or
	# merged)

	inner_list.append (Container ( \
		HTMLgen.Href ('searches/tr.query.results.cgi?Staff=' + \
			'REMOTE_USER&Not=Status&Status=cancelled&Status=' + \
			'done&Status=merged',
			'Show My Tracking Record List'),
		HTMLgen.Small (' - list current tracking records for which ' + \
			'the current user is listed as a staff member'), \
		HTMLgen.P ()))

	# Show My Requests (include ones set for a Requested By field with
	# the current user, exclude those with a Status of done, cancelled or
	# merged)

	inner_list.append (Container ( \
		HTMLgen.Href ('searches/tr.query.results.cgi?Requested_By=' + \
			'REMOTE_USER&Not=Status&Status=cancelled&Status=' + \
			'done&Status=merged',
			'Show My Requests'),
		HTMLgen.Small (' - list current tracking records for which ' + \
			'the current user is listed in the Requested By field'),
		HTMLgen.P ()))

	# Retrieve - has a text label, a text box where user can enter a TR #, 
	#	a submit button, a description, and a paragraph marker

	inner_list.append (Container (
		HTMLgen.Text ('Find TR #:'), \
		HTMLgen.Input (type='text', name='TR_Nr', size=5), \
		screenlib.Button ('Retrieve',
		'''s="searches/tr.detail.cgi?TR_Nr=" + QuickRetrieve.TR_Nr.value;
			window.location.href = s;'''),
		screenlib.Button ('Retrieve with Descendants',
		'''s="searches/tr.query.results.cgi?X_Depends_On=1&TR_Nr=" +
			QuickRetrieve.TR_Nr.value;
			window.location.href = s;'''),
		HTMLgen.P () ))

	# the inner list will comprise the "form" on the main screen...  (We
	# need to use a form for the field and the submit button to work)

	frm = screenlib.WTS_Form (
		'searches/tr.detail.cgi',		# cgi to call on submit.
		name='QuickRetrieve',			# name of the form.
		method='GET',				# submission method
		submit = ' ')				# skip the default
							# submit button - we've
							# made our own.

	# add the list of quick queries (inner_list) to the form (frm)

	frm.append (HTMLgen.OrderedList (inner_list))

	# Then, add a bulleted list to the screen we're producing.  The bulleted
	# list contains: a container with a link to the query form, a
	# description, and a paragraph marker, and the form (frm) we just
	# produced with all the quick queries.  Then, we have a link to the
	# Status Grid form...

	doc.append (HTMLgen.BulletList ( [ Container ( \
		HTMLgen.Href ('searches/tr.query.html','Query Tracking Records'),
		HTMLgen.Small (' - query the database for tracking record ' + \
			'information (for display and edit)'), \
		HTMLgen.P (),
		frm),
#		Container (
#			HTMLgen.Href ('searches/tr.status.grid.html',
#				'Status Grid Form'),
#			HTMLgen.Small (''' - generate a grid of Status changes
#				grouped by Area or Type, for a certain time
#				period'''),
#			HTMLgen.P() )
		] ))

	# section 2 - entering new tracking records
	#	add a horizontal rule and a centered heading

	doc.append (HTMLgen.HR ())
	doc.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Create New Tracking Records') ))

	#	and finally add a bulleted list with two containers, each
	#	of which has a link, a description, and a paragraph marker

	doc.append (HTMLgen.BulletList ( [ \
		Container ( \
			HTMLgen.Href ('searches/tr.new.sf.cgi',
				'New Tracking Record - Short Form'),
			HTMLgen.Small (' - enter only the vital information ' +\
				'for a new tracking record using your browser'),
			HTMLgen.P ()),
		Container (
			HTMLgen.Href ('searches/tr.new.cgi',
				'New Tracking Record - Long Form'),
			HTMLgen.Small (' - enter all information for a new ' + \
				'tracking record using your browser'),
			HTMLgen.P () )]
		))

	# section 3 - maintenance stuff
	#	add a horizontal rule and a centered heading

	doc.append (HTMLgen.HR ())
	doc.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Maintenance Tasks & Information') ))

	#	and finally add a bulleted list with two containers, each
	#	of which has a link, a description, and a paragraph marker

	doc.append (HTMLgen.BulletList ( [ \
		Container (
			HTMLgen.Href ('searches/change.password.form.cgi',
				'Change Your WTS Password'),
			HTMLgen.P () ),
		Container ( \
			HTMLgen.Href ('userdocs/faq.html', 'FAQ'),
			HTMLgen.Small (' - frequently asked questions ' + \
				'about WTS'),
			HTMLgen.P ())
		]))

	doc.write (dir + 'index.html')		# lastly, save the WTS Home Page


def gen_Query_Form (
	dir		# destination directory for the file produced
	):
	# Purpose: generate and save the WTS Tracking Record Query Form in the
	#	specified directory under the filename 'tr.query.html'
	# Returns nothing
	# Assumes: has knowledge about fields in a tracking record.
	# Effects: see Purpose.  gets controlled vocabulary information from
	#	the database for inclusion in pick lists.
	# Throws: propagates wtslib.sqlError if errors occur in running the
	#	SQL queries needed to get the controlled vocabulary info
	# Notes:
	#	Fields Produced:
	#		TR_Nr                   Needs_Attention_By
	#      		Title                   Requested_By
	#		Area                    X_Depends_On
	#		Type                    Depends_On_X
	#		Priority                Staff
	#		Status                  Text_Fields
	#		Status_Date             Modification_Date
	#		Size                    Directory
	#		Primary                 Primary_Order
	#		Secondary               Secondary_Order
	#		Tertiary                Tertiary_Order
	#		Displays

	HELP_URL = '../searches/help.cgi?req=%s'	# URL to get help

	HeadingLevel = 4	# (constant) HTML heading level / size to use
				# for section titles

	# -- first create the form --

	frm = screenlib.WTS_Form (
		'tr.query.results.cgi',# CGI to call on submission
		method = 'POST',		# use a POST submission because
						# we have a lot of possible 
						# fields.
		name = 'QueryForm',		# name of the form
		submit = HTMLgen.Input (	# its submit button
			type = 'submit',
			name = 'Submit Query',
			value = 'Submit Query'),
		reset = HTMLgen.Input (		# its reset button
			type = 'reset',
			name = 'Reset',
			value = 'Reset'),
		buttons = screenlib.Button (	# its WTS Home button
			PREFIX + ' Home',
			'window.location.href="%s"' % screenlib.WTS_HOME_PAGE)
		)

	# add a centered heading to the form

	frm.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Query Restrictions')))

	# -- create and append the top table (TR #, Title) --

	top_tbl = HTMLgen.TableLite (	# create the table
		border = 1,		# with a border
		align = 'center',	# centered horizontally on the page
		cellpadding = 5)	# and with some padding between the
					# text and the walls of each cell

	# The first row in the top table has a single row with a single cell,
	# containing a link, a label, and a text box for TR #

	top_tbl.append (HTMLgen.TR (
		HTMLgen.TD (
			HTMLgen.Href (HELP_URL % 'TR_Nr', 'TR #'),
			HTMLgen.Text (' (TR)'), \
			HTMLgen.Input (type = 'text',
				name = 'TR_Nr',
				size = 20)
		)))

	# The second row in the top table has a single row with a single cell,
	# containing a link and a text box for the Title

	top_tbl.append (HTMLgen.TR (
		HTMLgen.TD (
			HTMLgen.Href (HELP_URL % 'Title', 'Title'),
			HTMLgen.Input (type = 'text', \
				name = 'Title',
				size = 40)
		)))

	frm.append (top_tbl)		# add the top table to the form
	frm.append (HTMLgen.P())	# then add a paragraph marker

	# -- create and append the main table (all other data) --

	CV = Controlled_Vocab.cv	# get a quick reference to the standard
					# dictionary of Controlled_Vocab
					# objects

	main_tbl = HTMLgen.TableLite (	# create the main table
		border = 1,		# with a border
		align = 'center',	# centered horizontally on the page
		cellpadding = 5)	# and with some space between the text
					# and the walls of each cell

	# we need to build the first row of the main table - row1

	row1 = HTMLgen.TR ()		# initialize a blank row

	# we need to add two cells to row1 with controlled vocabulary info

	for field in [ 'Area', 'Type' ]:
		row1.append (HTMLgen.TD (	# add a new cell to row1

			# add link and line break

			HTMLgen.Href (HELP_URL % field, field),
			HTMLgen.Text (' ... '),
			HTMLgen.Input (type = 'checkbox',
				name = 'Not',
				value = field),		# fieldname to submit
			HTMLgen.Text ('Not'),
			HTMLgen.BR (),

			# add a pick list box:  effectively prepend the 'any'
			# option to the other options for the selected
			# controlled vocabulary

			HTMLgen.Select (['any'] + \
				CV ['CV_WTS_' + field].pickList (showAll=1),
				name = field,	# fieldname to be submitted
				size = 3,	# show 3 items in the pick list
				multiple = 1,	# allow multiple selections
				selected = [ 'any' ])	# default = 'any'
			))

	# we need to add the third cell in row1 (the top row of the main table):
	# the Needs Attention By field with a link, a line break, and a text box

	row1.append (HTMLgen.TD (
		HTMLgen.Href (HELP_URL % 'Needs_Attention_By',
			'Needs Attention By'),
		HTMLgen.BR (), 
		HTMLgen.Input (type = 'text', name = 'Needs_Attention_By', \
		size = 25)
		))
	main_tbl.append (row1)	# now, add the top row to the main table

	# start building the second row of the main table - row2

	row2 = HTMLgen.TR ()		# initialize a blank row
	row2.append (HTMLgen.TD (	# leftmost cell (Priority) in row2

		# link and a line break

		HTMLgen.Href (HELP_URL % 'Priority', 'Priority'),
		HTMLgen.Text (' ... '),
		HTMLgen.Input (type = 'checkbox',
			name = 'Not',
			value = 'Priority'),		# fieldname to submit
		HTMLgen.Text ('Not'),
		HTMLgen.BR (),

		# pick list box has the 'any' option at the top of the list
		# of other priorities

		HTMLgen.Select (['any'] + \
			CV ['CV_WTS_Priority'].pickList (showAll=1),
			name = 'Priority',	# field to be submitted
			size = 5,		# show 5 at a time
			multiple = 1,		# allow multiple selections
			selected = [ 'any' ])	# default = 'any'
		))
	row2.append (HTMLgen.TD (	# middle cell in row 2 (Requested By)

		# link and a line break

		HTMLgen.Href (HELP_URL % 'Requested_By', 'Req By'),
		HTMLgen.BR (),

		# pick list box has the 'any' option at the top of the list
		# of other staff members

		HTMLgen.Select (['any'] + CV ['CV_Staff'].pickList(showAll=1),
			name = 'Requested_By',	# name to be submitted
			size = 5,		# show 5 at a time
			multiple = 1,		# allow multiple selections
			selected = [ 'any' ])	# default = 'any'
		))
	row2.append (HTMLgen.TD (	# rightmost cell in row2 (Status)

		# link and a line break

		HTMLgen.Href (HELP_URL % 'Status', 'Status'),
		HTMLgen.Text (' ... '),
		HTMLgen.Input (type = 'checkbox',
			name = 'Not',
			value = 'Status'),		# fieldname to submit
		HTMLgen.Text ('Not'),
		HTMLgen.BR (),

		# pick list box has the 'any' option at the top of the list
		# of other statuses

		HTMLgen.Select (['any'] + \
			CV ['CV_WTS_Status'].pickList (showAll=1),
			name = 'Status',	# fieldname to be submitted
			size = 5,		# show 5 at a time
			multiple = 1,		# allow multiple selections
			selected = [ 'any' ]),	# default = 'any'
		))
	main_tbl.append (row2)		# add the second row to the main table

	# build the third row of the main table - row3

	row3 = HTMLgen.TR ()		# initialize a blank row
	row3.append (HTMLgen.TD (	# leftmost cell in row3 (Size)

		# link and a line break

		HTMLgen.Href (HELP_URL % 'Size', 'Size'),
		HTMLgen.Text (' ... '),
		HTMLgen.Input (type = 'checkbox',
			name = 'Not',
			value = 'Size'),		# fieldname to submit
		HTMLgen.Text ('Not'),
		HTMLgen.BR (),

		# pick list box has the 'any' option at the top of the list
		# of other sizes

		HTMLgen.Select (['any'] + \
			CV ['CV_WTS_Size'].pickList (showAll=1),
			name = 'Size',		# fieldname to be submitted
			size = 5,		# show 5 sizes at once
			multiple = 1,		# allow multiple selections
			selected = [ 'any' ])	# default = 'any'
		))
	row3.append (HTMLgen.TD (	# middle cell in row3 (Depends On)
		# link and a line break, followed by a multi-line message about
		# how to do "Depends On" queries.

		HTMLgen.Href (HELP_URL % 'Depends_On', 'Depends On'),
		HTMLgen.BR (),
		HTMLgen.Text ('For dependency-based queries, use the'),
		HTMLgen.BR (),
		HTMLgen.Text ('"For each TR in the query result..."'),
		HTMLgen.BR (),
		HTMLgen.Text ('section below'),
		colspan = 2
		))
	main_tbl.append (row3)		# add the third row to the main table
	
	# build the fourth row in the main table -- row4

	row4 = HTMLgen.TR ()		# initialize a blank row
	row4.append (HTMLgen.TD (	# add right cell in row4 (Staff)

		# link and a line break

		HTMLgen.Href (HELP_URL % 'Staff', 'Staff'),
		HTMLgen.BR (),

		# pick list box has the 'any' option at the top of the list
		# of other staff members

		HTMLgen.Select (['any'] + \
			CV ['CV_Staff'].pickList (showAll=1),
			name = 'Staff',		# fieldname to be submitted
			size = 5,		# show 5 at a time
			multiple = 1,		# allow multiple selections
			selected = [ 'any' ])	# default = 'any'
		))
	row4.append (HTMLgen.TD (	# right cell in row4 - (depends on)

		# link and a line break

		HTMLgen.Href (HELP_URL % 'ForEach',
			'For each TR in the query result...'),
		HTMLgen.BR (),

		# checkbox, label, and line break

		HTMLgen.Input (type = 'checkbox',
			name = 'X_Depends_On'),		# fieldname to submit
		HTMLgen.Text ('Show those depended on by TR'),
		HTMLgen.BR (),

		# checkbox and label

		HTMLgen.Input (type = 'checkbox',
			name = 'Depends_On_X'),		# fieldname to submit
		HTMLgen.Text ('Show those depending on TR'),
		colspan = 2		# this cell should span the two
					# rightmost columns
		))
	main_tbl.append (row4)		# add the fourth row to the main table

	# build row 5 in the main table

	row5 = HTMLgen.TR ()		# initialize a blank row
	row5.append (HTMLgen.TD (

		# label, line break, and text box for searching the three large
		# text fields.

		HTMLgen.Bold (HTMLgen.Text ('Text Fields: ')),
		HTMLgen.Italic (HTMLgen.Text ('('),
			HTMLgen.Href (HELP_URL % 'Project_Definition',
				'Project Definition'),
			HTMLgen.Text (', '),
			HTMLgen.Href (HELP_URL % 'Progress_Notes',
				'Progress Notes'),
			HTMLgen.Text (')')
			),
		HTMLgen.BR (),
		HTMLgen.Input (type = 'text',		
			name = 'Text_Fields',		# fieldname to submit
			size = 35),
		colspan = 2		# this cell should span the two left
					# columns of row5
		))
	row5.append (HTMLgen.TD (	# right cell in row5 (Modification Date)

		# link, line break, and text box

		HTMLgen.Href (HELP_URL % 'Modification_Date',
			'Modification Date'),
		HTMLgen.BR (),
		HTMLgen.Input (type = 'text',
			name = 'Modification_Date',	# fieldname to submit
			size = 25)
		))
	main_tbl.append (row5)		# add the fifth row to the main table

	frm.append (main_tbl)		# finally, add the main table to the
					# form we had produced

	# -- create and append the table with fields to show --

	# add a new centered heading to the form

	frm.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Fields to Show in Results')))

	# In order to build the table with the checkboxes for what fields to
	# show, let's start with a list of lists of tuples.  The table is only
	# one row high.  Each sublist contains the tuples of data for one cell
	# in that row.  Each tuple contains:
	#	(label to display by checkbox, what fieldname to submit,
	#	 default value of checkbox).

	cells = [
		[	('TR Nr', 'TR #', 1),			# cell 1
			('Title', 'Title', 1),
			('Area', 'Area', 1) ],
		[	('Type', 'Type', 1),			# cell 2
			('Needs Attention By', 'Needs Attention By', 0),
			('Priority', 'Priority', 0) ], 
		[	('Requested By', 'Req By', 0),		# cell 3
			('Status', 'Status', 1),
			('Status Date', 'Status Date', 0) ],
		[	('Size', 'Size', 0),			# cell 4
			('Staff', 'Staff', 0) ],
		[	('Directory', 'Directory', 0),		# cell 5
			('Modification Date', 'Modification Date', 0) ]
		]

	row = HTMLgen.TR ()		# initialize a blank row

	# now, we need to step through the five cells in this row...

	for td in cells:
		cell = HTMLgen.TD ()	# initialize a blank cell

		# now, step through the contents of td and add a checkbox, a
		# label, and a line break for each.

		for item in td:

			# notice that all these checkboxes are submitted using
			# the same fieldname - Displays - since it conceptually
			# represents a single field (what to display)

			cell.append (HTMLgen.Input (type = 'checkbox',
				name = 'Displays',
				value = item [0],
				checked = item [2]))
			cell.append (HTMLgen.Text (item [1]))
			cell.append (HTMLgen.BR ())

		# finally, add the new cell to the row

		row.append (cell)

	# create a table for what fields to display

	display_tbl = HTMLgen.TableLite (	# initialize a new table
		border = 1,		# show a border
		align = 'center',	# center horizontally on the screen
		cellpadding = 5)	# include some space between the text
					# and the cell walls.

	display_tbl.append (row)	# finally, add our row to the table
	frm.append (display_tbl)	# and add our table to the form

	# -- create and append the sort order table --

	# add a new centered heading to our form

	frm.append (HTMLgen.Center (HTMLgen.Heading (HeadingLevel, \
		'Sort Order for Results')))

	# now we need to build the table for the sorting criteria

	sort_tbl = HTMLgen.TableLite (	# initialize a new table
		border = 1,		# show a border
		align = 'center',	# center table horizonally on screen
		cellpadding = 5)	# have some space between the text and
					# the cell walls

	# add the header row to sort_tbl, with a blank cell and two labels:
	# fieldname (one column wide) and sort order (two columns wide)

	sort_tbl.append (HTMLgen.TR (	# a new row (the first, in fact)
		HTMLgen.TD (),
		HTMLgen.TD (HTMLgen.Italic (HTMLgen.Text ('fieldname'))),
		HTMLgen.TD (HTMLgen.Italic (HTMLgen.Text ('sort order')),
			colspan = 2)
		))

	# now, as we prepare to build the table, let's start with a list of
	# tuples, each of which is 

	# sort_levels contains a list of tuples.  Each tuple is comprised of:
	#	(string name of sorting level, list containing at most one
	#	 tuple of the form (new option name, new option value)
	#	)

	sort_levels = [ ('Primary', []), ('Secondary', [ ('None', 'None') ]), \
		('Tertiary', [ ('None', 'None') ]) ]

	# sort_fields is a list of tuples, each of which stores:
	#	(option name to show in pick list, option value)
	# We build up the sort_fields by extracting data from the "cells" list
	# above.

	sort_fields = []		# start empty
	for cell in cells:		# go through each sublist (cell)
		for item in cell:	# and go through each item in each cell

			# if the item is not Directory, then we can sort by it,
			# so add it to the sort_fields:

			if item[0] != 'Directory':
				sort_fields.append ( (item [1], item [0]) )

	# now, let's go through our three levels of sorting and add a row to
	# the sorting table for each...

	for row in sort_levels:
		tr = HTMLgen.TR ()	# initialize a new row

		# first cell is a label:  Primary, Secondary, or Tertiary

		tr.append (HTMLgen.TD (HTMLgen.Text (row [0])))

		# second cell is a single-valued pick list.  To get the list
		# of options, we need to add the (name, value) tuple from row
		# to the start of sort_fields.  This is where the "None" option
		# comes from for the secondary and tertiary sorting levels.
		# The fieldname matches the label.

		tr.append (HTMLgen.TD (HTMLgen.Select (row [1] + sort_fields, \
			name = row [0])))

		# the two rightmost cells are radio buttons, one of which is
		# for ascending sort order, and the other of which is for
		# descending sort order.  Their fieldname is the label with
		# '_Order' added at the end.

		tr.append (HTMLgen.TD (
			HTMLgen.Input (type = 'radio',		# radio button
				name = row [0] + '_Order',
				checked = 1,			# checked
				value = 'asc'),
			HTMLgen.Text (' Ascending')))		# label
		tr.append (HTMLgen.TD (
			HTMLgen.Input (type = 'radio',		# radio button
				name = row [0] + '_Order',
				checked = 0,			# not checked
				value = 'desc'),
			HTMLgen.Text (' Descending')))		# label

		# finally add this row to the sort table

		sort_tbl.append (tr)

	frm.append (sort_tbl)		# add the sort table to the form
	frm.append (HTMLgen.P())	# followed by a paragraph marker

	# -- create the document, add the form, and write it all out

	doc = screenlib.WTS_Document (
		cgi = 0,	# produce this page for being saved to a file,
				# rather than as a CGi reply
		title = PREFIX + ': Tracking Record Query Form')
	doc.append (frm)
	doc.write (dir + 'tr.query.html')


def gen_Help_Screens (
	dir		# directory in which to create the help files
	):
	# Purpose: to generate and save new versions of the help files (for
	#	each tracking record field) in the specified dir
	# Returns: nothing
	# Assumes: current user has permission to write in dir
	# Effects: see Purpose.  gets controlled vocabulary information from
	#	the database for inclusion in pick lists.
	# Throws: propagates wtslib.sqlError if errors occur in running the
	# Notes: For controlled vocabulary fields, we need to produce a page
	#	with two frames, one for the descriptive information and another
	#	for the table showing the vocabulary.

	# Let's start with a list of information for the help files we need to
	# produce.  Each tuple in the list below contains the information for
	# one field:
	#	(file name, title, include file for cntrl vocab (or None),
	#	description, list of strings about querying)

	help_files = [ 
		('tr.number.html',
			'TR # - Tracking Record Number',
			None,
			'''unique, immutable identifier for a tracking record,
				generated and assigned by the system when a new
				tracking record is saved.''',
			['''When querying, you may specify a range of tracking
				record numbers using "..".  For example:''',
			'''57..100 -- means all tracking records numbered from
				57 to 100''',
			'..57 -- means all tracking records numbered up to 57',
			'''57.. -- means all tracking records numbered higher
				than 57''' ]),
		('tr.title.html',
			'Title',
			None,
			'''short, one-line descriptive title of the tracking
				record''',
			['''When querying, you may enter a word or phrase as you
				would like it to appear in the title of each
				tracking record returned by the query.''']),
		('tr.area.html',
			'Area',
			'cv.area.html',
			'indicates which "part" of the system is affected',
			['''When querying, check off all Areas you would like to
			see displayed.''',
			'''This acts as an "OR":  if you select both "misc" and
			"sysAdmin", the query will look for tracking records
			that are in either of those Areas (or both)''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''',
			'''Checking the "Not" box will result in querying for
			tracking records which have Areas other than (or in
			addition to) those checked.''' ]),
		('tr.routing.html',
			'Category',
			'cv.category.html',
			'''the "Route To" field indicates the "category"
			to which this tracking record should be routed -- who
			gets the e-mail notification and who is assigned as
			default staff members?''',
			['Not queryable']),
		('tr.forwarding.html',
			'Category',
			'cv.category.html',
			'''the "Forward TR" field indicates the "category"
			to which this tracking record should be forwarded,
			including the sending of e-mail notifications and
			possibly adding default values for the Area, Staff,
			Status, and Type fields.''',
			['Not queryable']),
		('tr.type.html',
			'Type',
			'cv.type.html',
			'what is the product of this tracking record?',
			['''When querying, check off all Types you would like to
			see displayed.''',
			'''This acts as an "OR":  if you select both "misc" and
			"sysAdmin", the query will look for tracking records
			that are either of those Types (or both)''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''',
			'''Checking the "Not" box will result in querying for
			tracking records which have Types other than (or in
			addition to) those checked.''' ]),
		('tr.attention.html',
			'Needs Attention By',
			None,
			'''date and time by which this tracking record must
				have attention.''',
			['''When querying, you may specify a range of dates
				using "..".  For example:''',
			'''6/1/1998..7/1/1998 -- means all tracking records
				with a "Needs Attention By" date between (and
				including) 6/1/1998 and 7/1/1998''',
			'''..7/1/1998 -- means all tracking records with a
				"Needs Attention By" date before (and including)
				7/1/1998''',
			'''6/1/1998.. -- means all tracking records with a
				"Needs Attention By" date after (and including)
				6/1/1998''' ]),
		('tr.priority.html',
			'Priority',
			'cv.priority.html',
			'how important is the project, regardless of size?',
			['''When querying, check off all Priorities you would
			like to see displayed.''',
			'''This acts as an "OR":  if you select both "high" and
			"low", the query will look for tracking records
			that have either of those Priorities''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''',
			'''Checking the "Not" box will result in querying for
			tracking records which have Priorities other than
			those checked.''' ]),
		('tr.definition.html',
			'Project Definition',
			None,
			'''a more detailed description of the needs and scope
				of the project, including overview and possibly
				requirements, design, and test plans.  can
				contain HTML markups''',
			['''When querying, you may enter a word or phrase as you
				would like it to appear in either the Project
				Definition or Progress Notes of each
				tracking record returned by the query.''']),
		('tr.notes.html',
			'Progress Notes',
			None,
			'''notes about what was done: what source files or
				configurations were changed, review or test
				results, etc.  can contain HTML markups.''',
			['''When querying, you may enter a word or phrase as you
				would like it to appear in either the Project
				Definition or Progress Notes of each
				tracking record returned by the query.''']),
		('tr.depends.html',
			'Depends On',
			None,
			'''TR #'s of tracking records on which this tracking
				record depends.  Entered as a comma-separated
				list of TR numbers.  For example:  TR15, TR16,
				TR21''',
			['''Queryable using the "For each TR in the query
				result..." section''']),
		('tr.reqby.html',
			'Requested By',
			'cv.staff.html',
			'''who originally made the request that originated this
				tracking record, or who is the primary person
				with knowledge about what we need?''',
			['''When querying, check off all Staff Members you would
			like to have appear in the "Requested By" field.''',
			'''This acts as an "OR":  if you select both "jak" and
			"jer", the query will look for tracking records
			that have either of those people in the "Requested By"
			field''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''' ]),
		('tr.status.html',
			'Status',
			'cv.status.html',
			'''The Status field defines what phase of its life
				cycle the tracking record is in.  If you change
				the Status without also changing the Status Date
				(setting an "effective date/time" for the new
				status), WTS will automatically set the Status
				Date to be the current date & time.  A change to
				the Status of a tracking record generates an
				entry in the Status History.''',
			['''When querying, check off all Statuses you would
			like to see displayed.''',
			'''This acts as an "OR":  if you select both "new" and
			"closed", the query will look for tracking records
			that have either of those Statuses''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''',
			'''Checking the "Not" box will result in querying for
			tracking records which have Statuses other than
			those checked.''' ]),
		('tr.statusdate.html',
			'Status Date',
			None,
			'effective date of the current status.',
			['''When querying, you may specify a range of dates
				using "..".  For example:''',
			'''6/1/1998..7/1/1998 -- means all tracking records
				with a "Status Date" between (and
				including) 6/1/1998 and 7/1/1998''',
			'''..7/1/1998 -- means all tracking records with a
				"Status Date" before (and including)
				7/1/1998''',
			'''6/1/1998.. -- means all tracking records with a
				"Status Date" after (and including)
				6/1/1998''' ]),
		('tr.size.html',
			'Size',
			'cv.size.html',
			'''a guestimate of how much work the tracking record is
				(for planning purposes)''',
			['''When querying, check off all Sizes you would like to
			see displayed.''',
			'''This acts as an "OR":  if you select both "tiny" and
			"small", the query will look for tracking records
			that have either of those Sizes''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''',
			'''Checking the "Not" box will result in querying for
			tracking records which have Sizes other than
			those checked.''' ]),
		('tr.staff.html',
			'Staff',
			'cv.staff.html',
			'keeps track of who is working on the tracking record',
			['''When querying, check off all Staff Members you would
			like to have appear in the "Staff" field.''',
			'''This acts as an "OR":  if you select both "jak" and
			"jer", the query will look for tracking records
			that have either of those people in the "Staff"
			field''',
			'''Any selections by the user will cause the default
			selection ("any") to be ignored.''' ]),
		('tr.directory.html',
			'Directory',
			None,
			'''name of a unix directory containing more details
				(other documents, etc.) for this tracking
				record''',
			['Not queryable']),
		('tr.moddate.html',
			'Modification Date',
			None,
			'''date and time when this tracking record was last
				saved.''',
			['''When querying, you may specify a range of dates
				using "..".  For example:''',
			'''6/1/1998..7/1/1998 -- means all tracking records
				which were last modified between (and
				including) 6/1/1998 and 7/1/1998''',
			'''..7/1/1998 -- means all tracking records which were
				last modified before (and including)
				7/1/1998''',
			'''6/1/1998.. -- means all tracking records which were
				last modified after (and including)
				6/1/1998''' ]),
		('tr.date.html',
			'Date',
			None,
			'current date and time',
			['Not queryable']),
		('tr.display.html',
			'Display',
			None,
			'specifies which fields to display',
			['''When querying, check off all tracking records you
			would like to continue looking at (either in a
			Redisplay, Grid, or series of Detail displays)''']),
		('tr.history.html',
			'Status History',
			None,
			'''complete list of changes in this tracking record's
				status, including dates, times, and the person
				making the change, ordered from newest to
				oldest''',
			['Not queryable']),
		('tr.for.each.html',
			'For Each TR in the Query Result...',
			None,
			'''provides a way to augment the query results with
				other tracking records which are related (by
				dependencies) to those in the basic query
				result.''',
			['Query behavior for each checkbox is below:',
			'''Show those depended on by TR -- For each tracking
				record in the basic query result, also include
				all those on which that one depends, either
				directly or indirectly.  For example, if A
				depends on B, and B depends on C, and A would
				be in the basic query result, also include B
				and C.''',
			'''Show those depending on TR -- For each tracking
				record in the basic query result, also include
				all those which depend on it, either directly
				or indirectly.  For example, if A depends on B,
				and B depends on C, and C would be in the basic
				query result, also include A and B.''' ] )
		]

	# now we need to process each of these tuples (one per help file)
	#	(file name, title, include file for cntrl vocab,
	#	description, string or list of strings about querying)

	for (filename, title, include, descrip, query) in help_files:

		# let's build a list of HTMLgen objects for the query info:

		queryList = [ HTMLgen.Italic (query [0]) ]
		if len (query) > 1:
			list = []
			for item in query [1:]:
				list.append (HTMLgen.Text (item))
			queryList.append (HTMLgen.BulletList (list))

		# "include" indicates a file to be included (with definitions
		# for controlled vocabulary items.)  If this is None, we can
		# proceed with a regular document.  Otherwise, we need to set
		# up a doc with two frames - one for the definitions, and
		# one with the vocabulary table.

		if include is None:

			# initialize a standard document, incorporating the
			# given title and noting that it will be saved to a
			# file (not returning as the result of CGI)

			doc = screenlib.WTS_Document (
				title = PREFIX + ': Help - ' + title,
				cgi = 0)

			# add a bold version of the basic description,
			# followed by a paragraph marker

			doc.append (HTMLgen.Bold ('Description - ' + descrip))
			doc.append (HTMLgen.P())

			# append each item in the list of query information:

			for item in queryList:
				doc.append (item)

			# and, write it out to the specified filename

			doc.write (dir + filename)
		else:
			# We need to make three documents, one to hold the
			# two frames, and one to go in each frame.

			# main document (which contains the frames)

			# strip the '.html' extension off the given filename,
			# and append '.general.html' for the general file

			general_fn = filename[:-5] + '.general.html'

			# get the filename for the controlled vocabulary doc

			defs_fn = include

			# initialize a document for frames with the fieldname
			# in the title, and which will be saved rather than
			# returned as a CGI response.

			doc = HTMLgen.FramesetDocument ( \
				title = PREFIX + ': Help - ' + title,
				cgi = 0)

			# now, let's create a Frameset to hold our frames,
			# with the first frame getting 40% of the browser
			# window.  The second frame will get 60%.

			fm_set = HTMLgen.Frameset (rows = '40%, 60%')

			fm_set.append (HTMLgen.Frame (	
				src = general_fn, 	# filename of to bring
				name = 'general',	# in with the
				scrolling = 'auto'))	# descriptions
			fm_set.append (HTMLgen.Frame (
				src = defs_fn,		# filename of to bring
				name = 'defs',		# in with the vocab
				scrolling = 'auto'))	# definitions

			# add the Frameset to the screen, and write it out

			doc.append (fm_set)
			doc.write (dir + filename)

			# now, we need to generate the documents for the two
			# frames:

			# standard document (the descriptions), with the given
			# in the title, and formatted as a file rather than a
			# CGI response

			doc = screenlib.WTS_Document (
				title = PREFIX + \
					': Help - %s - General Info' % title,
				cgi = 0)

			# add a bold version of the basic description,
			# followed by a paragraph marker

			doc.append (HTMLgen.Bold ('Description - ' + descrip))
			doc.append (HTMLgen.P())

			# append each item in the list of query information:

			for item in queryList:
				doc.append (item)

			doc.write (dir + general_fn)	# write the file

			# controlled vocab definitions document (table of cv
			# definitions) 

			# table_name is the name of the database table to 
			# reference for controlled vocabulary information

			# name_for_user is the "title" that the user should see
			# at the top of the document.

			if title in ['Staff', 'From Whom', 'Requested By']:

				# the above three fields all use the same
				# table of staff information

				table_name = 'CV_Staff'
				name_for_user = 'Staff'
			else:
				table_name = 'CV_WTS_' + title
				name_for_user = title

			# let the Controlled_Vocab module create the
			# appropriate help file

			Controlled_Vocab.create_Include_File (
				table_name,		# table to reference
				dir + defs_fn,		# file to create
				name_for_user)		# title to use
	return


def gen_StatusGrid_Form (
	dir			# directory in which to create the form
	):
	# Purpose: to generate and save a new version of the screen which lets
	#	the user specify parameters for a Status Grid screen
	# Returns: nothing
	# Assumes: current user has permission to write in dir
	# Effects: writes the file "tr.status.grid.html" to "dir"
	# Throws: nothing

	# build the form with its buttons

	frm = screenlib.WTS_Form (
		'tr.status.grid.cgi',	 	# CGI to call on submission
		method = 'GET',			# use a GET submission because
						# we have only two fields.
		name = 'StatusGridForm',	# name of the form
		submit = HTMLgen.Input (	# its submit button
			type = 'submit',
			name = 'Generate Grid',
			value = 'Generate Grid'),
		reset = HTMLgen.Input (		# its reset button
			type = 'reset',
			name = 'Reset',
			value = 'Reset'),
		buttons = screenlib.Button (	# its WTS Home button
			PREFIX + ' Home',
			'window.location.href="%s"' % screenlib.WTS_HOME_PAGE)
		)

	# add the query fields:

	frm.append ('Analyze by: ')
	frm.append (HTMLgen.Select ( ['Area', 'Type'], name = 'RowType'))
	frm.append (HTMLgen.BR ())
	frm.append ('Look for Status changes in the date range: ')
	frm.append (HTMLgen.Input (type = 'text', name = 'DateRange',
		value = '', size = 25))
	frm.append (HTMLgen.P())
	frm.append (HTMLgen.HR ())

	# add instructions

	frm.append ('''This form allows you to generate a Status Grid based on
		your chosen range of dates and type of analysis
		(by ''',
	HTMLgen.Href ('help.cgi?req=Area', 'Area'),
		' or by ',
	HTMLgen.Href ('help.cgi?req=Type', 'Type'),
		').')
	frm.append (HTMLgen.P())
	frm.append ('The grid will:', HTMLgen.UL ( [
		Container ('show a column for each ',
		HTMLgen.Href ('help.cgi?req=Status', 'Status')),
		Container ('show a row for each ',
		HTMLgen.Href ('help.cgi?req=Area', 'Area'),
			' or ',
			HTMLgen.Href ('help.cgi?req=Type', 'Type'),
			', whichever is selected'),
		Container ('examine TRs which had a ',
		HTMLgen.Href ('help.cgi?req=Status', 'Status'),
			' change in that date range'),
		Container ('display in each cell the number of tracking ',
			'records which finished that date range with the ',
			HTMLgen.Href ('help.cgi?req=Status', 'Status'),
			' corresponding to that column, and which has the ',
			HTMLgen.Href ('help.cgi?req=Area', 'Area'),
			'/',
			HTMLgen.Href ('help.cgi?req=Type', 'Type'),
			' of that row')
		] ))
	frm.append (HTMLgen.HR())

	# build and save the document

	doc = screenlib.WTS_Document (cgi = 0,	# this document will go to a
						# file, not a CGI response,
		title = 'Status Grid Form')	# with specified title.
	doc.append (frm)
	doc.write (dir + 'tr.status.grid.html')
	return


# -- main program --

if __name__ == '__main__':
	options, error_flag = wtslib.parseCommandLine (sys.argv, \
				['dir=', 'home', 'query', 'help', 'grid'])
	if error_flag != 0:
		print USAGE	# present user with usage instructions
	else:
		if options.has_key ('dir'):

			# if the directory was specified, then get it

			dir = options ['dir'][0]
			if dir [-1] <> '/':
				dir = dir + '/'
			del options ['dir']		# this has been handled
		else:
			dir = './'	# use the current directory

		# now, process all the options specified

		for option in options.keys ():
			if option == 'home':		# if we need to create
				gen_Home_Page (dir)	# the home page, do it.

			elif option == 'query':		# if we need to create
				gen_Query_Form (dir)	# the query form, do it.

			elif option == 'help':		# if we need to create
				gen_Help_Screens (dir)	# help files, do it.

			elif option == 'grid':
				gen_StatusGrid_Form (dir)

		# or, if there were no options, then we need to give the user
		# some usage instructions...

		if options == {}:
			print USAGE
