#!/usr/local/bin/python

'''
# Name:		TrackRec.py
# Author:	Jon Beal
# Purpose:	Implements the TrackRec class for WTS, and contains all
#		code which needs to know the internal representation of
#		tracking records, either in the TrackRec object or in the
#		database.  Provides abstract operations on tracking records
#		to those outside this module.
# On Import:	We initialize a bunch of global variables
# Classes:
#	TrackRec
# Functions:
#	blank (string)
#	build_And_Run_SQL (Clean_Query_Dict)
#		consider_TR_Nr ()			/\
#		consider_simpleText ()			||
#		consider_date ()			||
#		consider_single_valued_cv ()		||
#		consider_multi_valued_cv ()	used only by build_And_Run_SQL
#		consider_dependencies ()	to help build the query
#		lookup_multi_valued_cv ()		||
#		compile_multi_valued_cv ()		||
#		compile_single_valued_cv ()		||
#		sort_results ()				\/
#	build_Query_Table (clean_Results)
#	directoryPath (dir)
#	directoryURL (dir)
#	expand_TR_Range (range, key)			- internal use only
#	expand_TR (tr numbers, key)			- internal use only
#	getStatusTable (row_type, date_range)
#	opposite (item)
#	parse_And_Merge (list of Query_Row_Dict, key name)
#	queryTitle (query string)
#	recompute_Closure ()
#	remove (orig, del_item)
#	save_WTS_TrackRec (values, method)		- internal use only
#	save_Standard_M2M (values, old_values, method)	- internal use only
#	save_Text_Fields (values, old_values, method)	- internal use only
#	save_Relationships (values, old_values, method)	- internal use only
#	self_test ()
#	sqlForRelativesOf (tr num, relationship type)
#	updateTransitiveClosure (tr num, relationship type)
#	validate_Query_Form (Raw_Query_Dict)
#	validate_TrackRec_Entry (Raw_TR_Dict)
#	with_db_names (input dict)		- internal use only
#	with_nice_names (input dict)		- internal use only
'''

import types
import string
import HTMLgen
import Controlled_Vocab
import Configuration
import WTS_DB_Object
import wtslib
import copy
import os
import time
import regex
import regsub
import Digraph
import Set
import Arc
import ArcSet
import Template


#-GLOBALS-------------------------------------------------------------------

TRUE = 1
FALSE = 0

error_separator = ':::'		# string used to separate the various error
				# messages which are combined into a single
				# string and returned as an exception value.

# "error" exception is the standard exception raised by the TrackRec module

error = "TrackRec.error"
	# when "error" is raised the value string returned may take one of
	# several forms:
	#	in validate_Query_Form and validate_TrackRec_Entry, if any
	#	validation errors occurred:
	#		comma-space separated string of error descriptions
	#	if an unrecognizable tracking record number range on the
	#	query form is entered:
	#		'Could not interpret TR range'
	#	if bad dates are encountered in getStatusTable():
	#	if we try to add/remove to/from a CV which is not multi-valued,
	#		'%s is not a multi-valued field' % name of CV

# "alreadyLocked" exception is raised when we attempt to lock a TrackRec that
# has already been locked

alreadyLocked = "TrackRec.alreadyLocked"
	# when "alreadyLocked" is raised, the value string returned consists of:
	#	'locked by %s on %s' % (name of user who locked it, date and
	#		time when locked)

# "notLocked" exception is raised when we attempt to save or unlock a TrackRec
# which the current user does not have locked.  (Another user may have it
# locked, or it may just not be locked.)

notLocked = "TrackRec.notLocked"
	# when "notLocked is raised, the value string returned will be either:
	#	if it is not locked:
	#		'no valid lock on TR %d.' % tracking record number
	#	if it is locked by another user:
	#		'no valid lock on TR %d.  It was locked by %s on %s'
	#			% (tracking record number, user who locked it,
	#				when it was locked)

HELP_URL = '../searches/help.cgi?req=%s'	# standard URL string for help

CHMOD = '/usr/bin/chmod'			# full path to chmod command
CHGRP = '/usr/bin/chgrp'			# full path to chgrp command

# "constants" to help us remember the type of a save operation.  (The save
# method calls several internal-only methods which need to know what type of
# save operation we are dealing with.)  These constants are used only in this
# file, so the values can be changed below if we ever need to.

TR_NEW = 1	# internal constant to denote that our save method is for a
		# new tracking record.  (so use insert statements)

TR_OLD = 2	# internal constant to denote that our save method is for an
		# existing tracking record.  (so use update statements)

# "constants" to define the types of large text fields (Both large text
# fields are saved to the database in the same table.  Each type is identified
# by a unique code, as given below.)

PROJECT_DEFINITION = 2 		# type-code for the Project Definition
PROGRESS_NOTES = 3		# type-code for the Progress Notes

PROJECT_DEFINITION_TEMPLATE = 'data/definitionTemplate.html'

PROJECT_DIR_GROUPING = 100	# number of project directories to group
				# together under each parent directory

# "constants" to identify types of relationships among tracking records (only
# one type currently)

DEPENDS_ON = 1		# tracking record X depends on tracking record Y if
			# X cannot be completed until Y is completed

# There are five major areas where we need to identify the fields of a
# tracking records:  in the database, in the object, on an HTML page (which
# the user reads), behind the scenes on an HTML form (where we name the
# fields which will be sent to the CGI), and in the name of the field's
# corresponding help file.  This results in the possibility of having five
# different fieldnames referring to any one tracking record attribute.  There
# is a necessary coupling among these names for each attribute, as follows:
#
#       database fieldnames - follow standard MGI field naming conventions
#               (keys begin with '_' with each word capitalized, other fields
#               in lowercase).  These are the keys of dictionary DB_TO_NAME
#               and the values of dictionary NAME_TO_DB.  They are only used
#               when saving to or loading from the database.
#       object fieldnames - Once a tracking record has been loaded from the
#               the database, its fieldnames are converted from the database
#               fieldnames to be those which are easier to read for the user
#               (and which are used on the HTML screens).  These are the keys
#               of NAME_TO_DB and the values of DB_TO_NAME.  They are also
#               expressed in the list ATTRIBUTES and are the keys of the
#               dictionary HELP_FILES (which maps these names to the help
#               file names).  Several of these fields are not appropriate to
#               be edited, so we note which ones should not appear in a text
#               file TrackRec representation in NO_TEXT_EDIT.  These were
#		formerly referred to as "nice" or "easily readable", so these
#		terms may persist throughout the comments.  (Clean up over time)
#       HTML page names - The user needs to see a more conventional English
#               name for each tracking record attribute, rather than the
#               database fieldnames.  We use the same names on HTML pages as
#               we do in the object itself.  (keys of NAME_TO_DB, values of
#               DB_TO_NAME, items of ATTRIBUTES)
#       HTML form fieldnames - Since having spaces in HTML form fieldnames is
#               a little awkward (and since the user never sees these names
#               anyway), we map all spaces in the object fieldnames to be
#               underscores.
#       help file names - Each tracking record attribute has a corresponding
#		help file.  The name of each help file is stored as a value of
#		the dictionary HELP_FILES, and is keyed by its object fieldname.
#               Not all object fieldnames have help files (only the fields
#               that are visible to the user).  A couple other help file
#               names were defined, too, as it was convenient.  (Display and
#               Date)
#
# Basically, the links are as pictured:
#
# database fieldnames <------> object fieldnames --------> help file names
#                              (& HTML page names)
#                                     |
#                                     +----------------> HTML form fieldnames
#
# Two functions are defined to facilitate the two-way mapping from database
# fieldnames to object fieldnames and back:
#   The function with_nice_names takes a dictionary with database fieldnames
#   as keys, and returns a dictionary with those keys mapped to their
#   equivalent object fieldnames.
#   The function with_db_names does the inverse mapping (object fieldnames
#   to their database equivalents).

# A function in wtslib (underscored ()) is used to convert object fieldnames to
# their HTML form fieldname equivalents.  The function FieldStorage_to_Dict
# (also in wtslib) converts them back (while performing other actions).

# below we define the attributes of a tracking record.  These are the
# fieldnames as presented to the user (and as stored internally).  They are
# identical to the keys of NAME_TO_DB (below), but rather than just doing
# NAME_TO_DB.keys (), we need to list them because the ordering is crucial for
# properly formatting text files which represent a tracking record.  (used in
# the command-line interface)

ATTRIBUTES = [  'TR Nr',
                'Title',                'Area',
                'Type',                 'Needs Attention By',
                'Priority',             'Requested By',
                'Status',               'Status Date',
                'Status Staff',         'Size',
                'Depends On',           'Staff',
                'Directory',
                'Project Definition',	'Progress Notes',
                'Status History',       'Modification Date' ]

# sets of attributes to define single-valued CV fields, multi-valued fields,

SINGLE_VALUED_CV = [ 'Status', 'Priority' ]
MULTI_VALUED = [ 'Area', 'Type', 'Staff', 'Requested By', 'Depends On' ]

# these two dictionaries map from "nice" (easily readable) names for the user
# (which are also used in the TrackRec object) to database fieldnames, and
# back again

NAME_TO_DB = {  'TR Nr' :               '_TR_key',
                'Priority' :            'priority_name',
                'Size' :                'size_name',
                'Status' :              'status_name',
                'Status Staff' :        'status_staff_username',
                'Status Date' :         'status_set_date',
                'Title' :               'tr_title',
                'Directory' :           'directory_variable',
                'Type' :                'type',
                'Needs Attention By' :  'attention_by',
                'Area' :                'area',
                'Staff' :               'staff_list',
                'Project Definition' :	'project_definition',
                'Progress Notes' :	'progress_notes',
                'Requested By' :        'requested_by',
                'Status History' :      'status_history',
                'Depends On' :          'depends_on',
                'Modification Date' :   'modification_date' }

DB_TO_NAME = {  '_TR_key' :                     'TR Nr',
                'priority_name' :               'Priority',
                'size_name' :                   'Size',
                'status_name' :                 'Status',
                'status_staff_username' :       'Status Staff',
                'status_set_date' :             'Status Date',
                'tr_title' :                    'Title',
                'directory_variable' :          'Directory',
                'type' :                        'Type',
                'attention_by' :                'Needs Attention By',
                'area' :                        'Area',
                'staff_list' :                  'Staff',
                'project_definition' :		'Project Definition',
                'progress_notes' :		'Progress Notes',
                'requested_by' :                'Requested By',
                'status_history' :              'Status History',
                'modification_date' :           'Modification Date',
                'depends_on' :                  'Depends On' }

# mapping from nice field names (for the user, and used in the TrackRec
# object) to the filename of their help files

HELP_FILES = {  'TR Nr' :               'tr.number.html',
                'Priority' :            'tr.priority.html',
                'Size' :                'tr.size.html',
                'Status' :              'tr.status.html',
                'Status Date' :         'tr.statusdate.html',
                'Title' :               'tr.title.html',
                'Directory' :           'tr.directory.html',
                'Type' :                'tr.type.html',
                'Needs Attention By' :  'tr.attention.html',
                'Area' :                'tr.area.html',
                'Staff' :               'tr.staff.html',
                'Project Definition' :	'tr.definition.html',
                'Progress Notes' :	'tr.notes.html',
                'Requested By' :        'tr.reqby.html',
                'Status History' :      'tr.history.html',
                'Modification Date' :   'tr.moddate.html',
                'Depends On' :          'tr.depends.html',
                'Date' :                'tr.date.html',
                'Display' :             'tr.display.html',
		'Routing' :		'tr.routing.html', 
		'Forwarding' :		'tr.forwarding.html' }

# which fields should not show up when we are editing with an external editor?
# (identify using the user-readable names which are also used inside the
# TrackRec object)

NO_TEXT_EDIT = [ 'TR Nr', 'Status Staff', 'Modification Date', 'Directory', 
	'Status History' ]


#-CLASS AND METHODS---------------------------------------------------------

class Raw_TD (HTMLgen.TD):
	html_escape = 'NO'

class TrackRec (WTS_DB_Object.WTS_DB_Object):
	# Concept:
	#	IS:	A TrackRec object is one complete tracking record for
	#		one project - with all its associated information.
	#	HAS:	a unique key value (TR #) and certain other tracking
	#		record attributes:  title, area, type, date by which
	#		attention is needed, priority, who requested this
	#		project, status, date of last status change, who
	#		set the current status, size, which other tracking
	#		records does this one depend on, who is working on
	#		this tracking record, directory containing related
	#		documents, project definition, progress notes, history
	#		of status changes, and modification date.
	#	DOES:	The following are common operations for TrackRec
	#		objects:  creating a new one, loading an existing one
	#		from the database, providing methods to change/set the
	#		values of an existing one and saving those changes,
	#		producing an HTML display of one.
	# Implementation:
	#	Tracking Records have no class variables (in the Java sense),
	#	though we do use global variables as documented above (where
	#	they are defined).  There are several instance variables, as
	#	noted below:
	#		key_name - name of the string key (for the _Config_Name
	#			field) which we use to look up the last
	#			assigned tracking record number (the int_value
	#			field) in the configuration table WTS_Config.
	#		key_value - the database key (an integer) assigned to
	#			this tracking record.  This will be None for a
	#			new tracking record until a new one is assigned
	#			during the save operation.
	#		attributes - list of strings, each of which is a key
	#			into data (and backup) and which identifies one
	#			of the pieces of tracking record data (like
	#			the "Title" or "Size", etc.).  This list is in
	#			the order in which fields should appear in a
	#			text file.  The values are the same as those in
	#			the global ATTRIBUTES, but this instance
	#			variable is needed so we can inherit from
	#			WTS_DB_Object.
	#		required_attributes - list of strings (a subset of
	#			attributes) which are required to have non-None
	#			values for a tracking record to be valid when
	#			saved.
	#		data - a dictionary which contains the data for this
	#			tracking record.  Keys are the attributes (as
	#			defined above).  Values are strings.  Single-
	#			valued controlled vocabulary items are stored
	#			as the string value (like "small" for Size)
	#			rather than as the integer key.  Multi-valued
	#			controlled vocabulary items are stored as a
	#			string with comma-separated values.  (like
	#			"unknown, web" for Area)
	#		backup - a dictionary which is a copy of "data" from
	#			when the object is created (as new, or when
	#			loaded from the database).  When we save 
	#			changes to an existing tracking record, we can
	#			compare "data" to "backup" to see what fields
	#			have changed from their original values, and so
	#			which ones need to be saved.
	#	Methods				inherits from WTS_DB_Object
	#		__init__ (optional TR #)		X
	#		addToCV (string CV attribute name,
	#			string of comma-separated CV
	#			items)
	#		all_Attributes ()			X
	#		allocate_Key ()				X
	#		dict ()					X
	#		getRoutingMessage ()
	#		getAttribute (attribute name)
	#		html_Display ()
	#		html_Edit_LongForm ()
	#		html_New_ShortForm ()
	#		isEmergency ()
	#		load ()
	#		lock ()
	#		num ()
	#		removeFromCV (string CV attribute name,
	#			string of comma-separated CV
	#			items)
	#		required_Attributes ()			X
	#		save ()
	#		setAttribute (attribute name, value)
	#		set_Defaults ()				X
	#		set_Values (dictionary of attributes
	#			& values)
	#		unlock ()
	#		verify_Current_Lock ()

	def __init__ (self,
		TR_Number = None	# integer tracking record number (key)
		):
		# Purpose: creates and initializes a new TrackRec object
		# Returns: nothing
		# Assumes: db's database routines have been initialized
		# Effects: see purpose.  If TR_Number is None, then we create
		#	create a new (empty) tracking record.  If TR_Number is
		#	non-None, then we load the specified one from the
		#	database.
		# Throws: propagates from self.load () -- 1. a wtslib.sqlError
		#	if loading an existing tracking record and the SQL
		#	statements fail for some reason.  2. a ValueError if
		#	TR_Number is non-None and a tracking record with that
		#	TR # cannot be loaded from the database.

		global ATTRIBUTES, PROJECT_DEFINITION_TEMPLATE

		# call parent's init

		WTS_DB_Object.WTS_DB_Object.__init__ (self)

		# The above __init__ call sets up two attributes that we want
		# to keep:
		#	self.data	dictionary which maps fieldnames (in the
		#		 	user-readable format) to field values
		#	self.key_value	current integer database key for this
		#			tracking record object.  (default None)

		# now, override two defaults with the known TrackRec data

		self.key_name = '_TR_key'	# name of the _Config_Name key
						# to use when looking up the
						# last tracking record number
						# assigned from the WTS_Config
						# table in the database.

		self.attributes = ATTRIBUTES	# list of fieldnames in a
						# tracking record (in the user-
						# readable format), in the
						# order they should appear when
						# saved to an external file.

		# while TR Nr, Status Date, and Status Staff are required,
		# we don't need the validation script to check for them, as
		# they will have defaults filled in automatically (if they do
		# not exist).  So, list the attributes that are required and
		# which must be checked in the validation process:

		self.required_attributes = [ 'Priority', 'Size', \
			'Status', 'Title', 'Type', 'Area', 'Requested By' ]

		# if the user did not specify a tracking record number, then
		# this is a new one; set the default values.

		if (TR_Number == None):
			self.set_Defaults ()

			# Since we are dealing with a new tracking record, we
			# should load the template for the Project Definition
			# field.  The default template stored in a text file at:
			#	PROJECT_DEFINITION_TEMPLATE
			# We need to read that file and collect its contents in
			# a variable (named 'definition_default') that we can
			# then assign to the Project Definition field.

			fp = open (PROJECT_DEFINITION_TEMPLATE, 'r')
			lines = fp.readlines ()
			fp.close ()

			definition_default = ''
			for line in lines:
				definition_default = definition_default + line

			self.set_Values ( { 'Project Definition' :
						definition_default } )

		# otherwise, he/she is requesting an existing tracking record,
		# so note the key value and load it from the database.

		else:
			self.key_value = TR_Number	# set the known key
			self.load ()			# fills in self.data

		# self.backup will store an exact copy of the tracking record's
		# "original" data -- the data that it was initialized with.
		# This will be very useful when we do a save operation on a
		# tracking record which already exists in the database, so that
		# we can look and save only fields that have changed.

		self.backup = copy.deepcopy (self.data)


	def removeFromCV (self,
		CV_attr,	# string; name of controlled vocab TR attribute
		vals		# string of comma-separated values to remove
		):
		# Purpose: remove each value in "vals" from the specified
		#	"CV_attr" field of this TR, if they're there
		# Returns: nothing
		# Assumes: CV items in "vals" are valid and are contained
		#	in the controlled vocabulary for "CV_attr"
		# Effects: updates self.data ['"CV_attr"'] to ensure that it
		#	does not contain any items contained in "vals"
		# Throws: TrackRec.error if "CV_attr" is not multi-valued

		if CV_attr not in MULTI_VALUED:
			raise error, '%s is not a multi-valued field' % CV_attr
		field = Set.Set ()
		for item in wtslib.string_To_List (self.data [CV_attr]):
			if len (item) > 0:
				field.add (item)
		for item in wtslib.string_To_List (vals):
			field.remove (item)
		self.data [CV_attr] = str (field)
		if str(field) == '':
			self.data [CV_attr] = None
		else:
			self.data [CV_attr] = str (field)
		return


	def addToCV (self,
		CV_attr,	# string; name of controlled vocab TR attribute
		vals		# string of comma-separated values to add
		):
		# Purpose: add each value in "vals" to the specified "CV_attr"
		#	field of this TR, if they're not already there
		# Returns: nothing
		# Assumes: CV items in "vals" are valid and are contained
		#	in the controlled vocabulary for "CV_attr"
		# Effects: updates self.data ['"CV_attr"'] to ensure that it
		#	contains all the items contained in "vals"
		# Throws: TrackRec.error if "CV_attr" is not multi-valued

		if CV_attr not in MULTI_VALUED:
			raise error, '%s is not a multi-valued field' % CV_attr
		field = Set.Set ()
		for item in wtslib.string_To_List (self.data [CV_attr]):
			if len (item) > 0:
				field.add (item)
		for item in wtslib.string_To_List (vals):
			if len (item) > 0:
				# if we're adding any other value, then we need
				# to remove any instances of "unknown"

				field.remove ("unknown")
				field.add (item)
		if str(field) == '':
			self.data [CV_attr] = None
		else:
			self.data [CV_attr] = str (field)
		return


	def hasProjectDirectory (self):
		# Purpose: test whether this tracking record has a project
		#	directory defined
		# Returns: boolean; 1 if we have a project directory, 0 if not
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.data ['Directory'] is not None


	def getAttribute (self,
		nice_name	# fieldname, one of those in 'ATTRIBUTES'
		):
		# Purpose: retrieve the value of a particular field
		# Returns: string value of the field, or None if the fieldname
		#	is unknown
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		if self.data.has_key (nice_name):
			return self.data[nice_name]
		return None


	def setAttribute (self,
		nice_name,	# string; a fieldnames in 'ATTRIBUTES'
		value		# string; the new value for the field
		):
		# Purpose: set the field specified by 'nice_name' to equal the
		#	given 'value'
		# Returns: boolean; 0 if not okay, 1 if okay
		# Assumes: nothing
		# Effects: updates self.data
		# Throws: nothing
		# Notes: For multi-valued controlled vocabulary fields, we
		#	provide special handling for '+' and '-' operators.
		#	If 'value' contains a '+' before a specified CV term,
		#	then we add that term.  If 'value' contains a '-'
		#	before a CV term, then we remove that term.  If a +
		#	or - is specified for at least one field, then it must
		#	be specified for each field.  If 'value' does not use
		#	a '+' or '-', then we replace the field's value.
		# Examples:
		#	tr.setAttribute ('Staff', 'jsb, tcw')
		#		sets the Staff list to be 'jsb, tcw'
		#	tr.setAttribute ('Staff', '+jsb, -tcw')
		#		adds jsb to the existing Staff list, and
		#		removes tcw if he is in it.

		plusMinus = regex.compile ('[+-]')
		if not self.data.has_key (nice_name):
			return FALSE

		if nice_name in SINGLE_VALUED_CV:
			value = regsub.gsub('[+-]', '', value)
			self.set_Values ( {nice_name : value} )

		elif nice_name in MULTI_VALUED:
			if plusMinus.search (value) == -1:
				self.set_Values ( {nice_name : value} )
			else:
				changes = regsub.split (value, ' *, *')
				for c in changes:
					if c[0] == '+':
						self.addToCV(nice_name, c[1:])
					elif c[0] == '-':
						self.removeFromCV (nice_name,
							c[1:])
					else:
						return FALSE
		else:
			self.set_Values ( {nice_name : value} )
		return TRUE


	def getRoutingMessage (self):
		# Purpose: get the message which serves as a simple summary of
		#	this tracking record (to be used in sending e-mails
		#	when it is created)
		# Returns: a string
		# Assumes: the Title, Priority, and Project Definition fields
		#	have string values
		# Effects: nothing
		# Throws: nothing

		num = self.num()
		if os.environ.has_key ('HTTP_HOST'):
			host = os.environ ['HTTP_HOST']
		else:
			host = 'titan'

		s = "TR %s -- http://%s/wts/searches/tr.detail.cgi?" % \
			(num, host)
		s = s + "TR=%s\n\n" % num
		s = s + ("Title:    %s\n" % self.data ['Title'])
		s = s + ("Priority: %s\n\n" % self.data ['Priority'])
		s = s + ("Project Definition:\n-------------------\n\n%s\n" % \
			self.data ["Project Definition"][:500])
		return s


	def html_Display (self,
		expanded = 0		# non-zero if we want an expanded
					# display (more detail re: dependencies)
		):
		# Purpose: return a list of HTMLgen objects which represent
		#	the tracking record for display purposes only (not for
		#	editing)
		# Returns: list of HTMLgen objects
		# Assumes: nothing
		# Effects: see purpose
		# Throws:  nothing
		# Notes:   The display of a tracking record consists of two
		#	tables of information, followed by three large text
		#	fields.  The first table contains two rows, one with
		#	the TR # and the current date & time, and the other
		#	contains the tracking record title.  Below that is a
		#	second, larger table which contains four rows.  Row 1
		#	contains the area, type, and need-attention-by date.
		#	Row 2 has the priority, list of staff members who
		#	requested this project, status, and status date.  Row 3
		#	contains the size, dependency information, and document
		#	directory.  Row 5 has the list of staff members
		#	assigned to this tracking record.  Below this table 
		#	are fields for the the project definition, and the
		#	progress notes.

		global HELP_URL, HELP_FILES

		# first do the table with the quick summary information

		summary_table = HTMLgen.TableLite (border=3, align='center')

		# row 1 : tr #, current date and time

		summary_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'TR_Nr',
					HTMLgen.Bold ('TR #')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['TR Nr']) ), \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Modification_Date',
					HTMLgen.Bold ('Modification Date')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data['Modification Date']))))

		# row 2 : title

		summary_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Title',
					HTMLgen.Bold ('Title')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Title']),
				colspan = 2 ) ) )

		# then do the table with the general information

		general_table = HTMLgen.TableLite (border=3, align='center')

		# row 1 : area, type, needs attention by

		general_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Area',
					HTMLgen.Bold ('Area')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Area']) ), \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Type',
					HTMLgen.Bold ('Type')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Type']) ), \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Needs_Attention_By',
					HTMLgen.Bold (
						'Needs Attention By (date)')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Needs Attention By'])
				) ) )

		# row 2 : priority, requested by, status, and status date

		general_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Priority',
					HTMLgen.Bold ('Priority')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Priority']) ), \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Requested_By',
					HTMLgen.Bold ('Req By')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Requested By']) ), \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Status',
					HTMLgen.Bold ('Status')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Status']),
				HTMLgen.Text (' - '),
				HTMLgen.Href (HELP_URL % 'Status_Date',
					HTMLgen.Bold ('Date')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Status Date']),
				) ) )

		# row 3 : size, dependencies, and directory

		# left cell:

		row = HTMLgen.TR (HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Size',
					HTMLgen.Bold ('Size')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Size']) ))
		# middle cell:

		# format the dependencies by appending a 'TR' to each number,
		# and by making each a link the the detail screen for that TR.

		cell = HTMLgen.TD (HTMLgen.Href (HELP_URL % 'Depends_On',
			HTMLgen.Bold ('Depends On')), HTMLgen.Text (' ') )
                if self.data.has_key ('Depends On'):
			list = self.data ['Depends On'].values ()
			list.sort ()
                else:
			list = []
		list_len = len (list)
		counter = 0
		for item in list:
			cell.append (HTMLgen.Href ( \
				'tr.detail.cgi?TR_Nr=%d' % item,
				'TR%d' % item))
			counter = counter + 1
			if counter < list_len:
				cell.append (HTMLgen.Text (', '))
		row.append (cell)

		# right cell:		

		row.append (HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Directory',
					HTMLgen.Bold ('Directory')), \
				HTMLgen.Text (' '), \
				HTMLgen.RawText (str(self.data ['Directory']))))
		general_table.append (row)

		# row 4 : staff, and two blank cells

		general_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Staff',
					HTMLgen.Bold ('Staff')), \
				HTMLgen.Text (' '), \
				HTMLgen.Text (self.data ['Staff']) ), \
			HTMLgen.TD ( \
				HTMLgen.BR () ), \
			HTMLgen.TD ( \
				HTMLgen.BR () ), \
				) )

		# collect the two objects so far and put in dividers

		objects = [ summary_table, HTMLgen.P (), general_table, \
			HTMLgen.BR () ]

		# if we need an expanded display, then we need info about
		# dependencies in here...

		if expanded:
			# all descendants:

			q1 = '''select tr._TR_key, tr.tr_title, tr._Status_key
				from WTS_TrackRec tr, WTS_Relationship rel
				where	(rel._TR_key = %s) and
					(tr._TR_key = rel._Related_TR_key) and
					(transitive_closure = 1) and
					(relationship_type = %s)
				order by tr._TR_key''' % \
				(self.num (), DEPENDS_ON)
			
			# ancestors:

			q2 = '''select tr._TR_key, tr.tr_title, tr._Status_key
				from WTS_TrackRec tr, WTS_Relationship rel
				where	(rel._Related_TR_key = %s) and
					(tr._TR_key = rel._TR_key) and
					(transitive_closure = 1) and
					(relationship_type = %s)
				order by tr._TR_key''' % \
				(self.num (), DEPENDS_ON)

			# get a quick reference to keyToName() method of the
			# Status controlled vocabulary object:

			status = Controlled_Vocab.cv ['CV_WTS_Status'].keyToName

			# and note the cgi string needed to display TRs:

			cgi = 'tr.detail.cgi?TR_Nr=%s'

			# retrieve all info from database:

			[descendants, ancestors] = wtslib.sql ([q1, q2], 'auto')

			# now, build the tables for each set of dependency info:

			single_row = HTMLgen.TR()

			for (title, rows) in [
				('All TRs On Which This TR Depends',
					descendants),
				('All TRs Which Depend On This TR', ancestors)]:

				tbl = HTMLgen.TableLite(border=3,align='center')
				tbl.append (HTMLgen.TR (HTMLgen.TH (title,
					colspan = 3)))
				tbl.append (HTMLgen.TR (
					HTMLgen.TH (HTMLgen.Href (HELP_URL % \
						'TR_Nr',
						HTMLgen.Bold ('TR #'))),
					HTMLgen.TH (HTMLgen.Href (HELP_URL % \
						'Title',
						HTMLgen.Bold ('Title'))),
					HTMLgen.TH (HTMLgen.Href (HELP_URL % \
						'Status',
						HTMLgen.Bold ('Status')))))

				for row in rows:
					# don't bother to include this TR in
					# the lists about its dependencies:

					if str(row ['_TR_key']) == self.num():
						continue
					tbl.append (HTMLgen.TR (
						HTMLgen.TD (HTMLgen.Href (
							cgi % row ['_TR_key'],
							row ['_TR_key'])),
						HTMLgen.TD (row ['tr_title']),
						HTMLgen.TD (status (row
							['_Status_key']))))

				single_row.append (HTMLgen.TD (tbl,
					valign="top"))

			objects.append (HTMLgen.Center (HTMLgen.TableLite (
				single_row)))

		# project definition

		objects.append ( HTMLgen.Href (HELP_URL % 'Project_Definition',
			HTMLgen.Bold ('Project Definition:')) )
		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.RawText (
			self.data ['Project Definition']) )
		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.BR () )

		# progress notes

		objects.append ( HTMLgen.Href (HELP_URL % 'Progress_Notes',
			HTMLgen.Bold ('Progress Notes:')) )
		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.RawText (self.data ['Progress Notes']))
		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.BR () )

		# status history

		history = wtslib.string_To_List (string.strip ( \
			self.data ['Status History']))
		history = remove (history, '')

		if len (history) > 0:
			objects.append ( HTMLgen.Href (HELP_URL % \
				'Status_History',
				HTMLgen.Bold (
					'Status History: (newest first)')) )
			objects.append ( HTMLgen.BR () )
			objects.append ( HTMLgen.BulletList (history) )

		return objects


	def html_Edit_LongForm (self):
		# Purpose: return a list of HTMLgen objects which represent
		#	the tracking record for editing or entry
		# Returns: list of HTMLgen objects
		# Assumes: nothing
		# Effects: see purpose
		# Throws:  nothing
		# Notes:   The display of a tracking record consists of two
		#	tables of information, followed by three large text
		#	fields.  The first table contains two rows, one with
		#	either the TR # (when editing existing tracking records,
		#	field is not editable) or a pick list for routing info
		#	(when entering a new tracking record), and the current
		#	date & time (not editable), and the other row contains a
		#	text box for the tracking record title.  Below that is a
		#	second, larger table which contains four rows.  Row 1
		#	contains the multi-value pick lists for are a and type,
		#	along with a text box for the need- attention-by date.
		#	Row 2 has a pick lists for priority, a multi-valued pick
		#	list for staff members who requested this project, a
		#	pick list for status, and a text box for status date.
		#	Row 3 contains a pick list for size, and text boxes for 
		#	dependency information and document directory.  Row 4
		#	has a multi-value pick list of staff members assigned
		#	to this tracking record.  Below this table are text
		#	areas (large multi-row boxes) for the project
		#	definition, and the progress notes.
		#	The fieldnames on the form (as they would be submitted)
		#	include:
		#		TR_Nr		Needs_Attention_By
		#		Title		Requested_By
		#		Area		Depends_On
		#		Type		Create_Directory_Flag
		#		Priority	Staff   
		#		Status		Routing
		#		Status_Date	Project Definition
		#		Status_Staff	Progress Notes
		#		Size


                global HELP_URL, HELP_FILES

		TEXT_ROWS = 30		# rows in a text area
		TEXT_COLS = 80		# columns in a text area
		DATE_SIZE = 20		# size of a date box
		SELECT_ROWS = 5		# rows in a multi-select box

		# get a reference to the current controlled vocabulary module
		# (for use in producing the selection lists on the form)

		CV = Controlled_Vocab.cv
		category_list = CV ['CV_WTS_Category'].ordered_names ()
		route_to = CV ['CV_WTS_Category'].key_dict () [
			CV ['CV_WTS_Category'].default_key () ]

		# build lists of CV items selected

		selArea = wtslib.string_To_List (self.data['Area'])
		selType = wtslib.string_To_List (self.data['Type'])
		selPriority = [self.data['Priority']]
		selReqBy = wtslib.string_To_List (self.data['Requested By'])
		selStatus = wtslib.string_To_List (self.data['Status'])
		selSize = wtslib.string_To_List (self.data['Size'])
		if self.data.has_key ('Staff'):
			selStaff = wtslib.string_To_List (self.data['Staff'])
		else:
			selStaff = []

		# first do the table with the quick summary information

		summary_table = HTMLgen.TableLite (border=1, align='center', \
			cellpadding = 5)

		# row 1
		# the contents of the first row depend on whether this is a
		# new tracking record or not.  If it is new, we need a selection
		# list for Routing and the current date & time.  If it is not
		# new, we need to display the tracking record number and have a
		# selection list for Routing.

		if self.num () == 'None':

			# this is a new tracking record

			summary_table.append (HTMLgen.TR (
				HTMLgen.TD (
					HTMLgen.Href (HELP_URL % 'Routing',
						'Route To'),
					HTMLgen.Text (' '),
					HTMLgen.Select (category_list,
						name='Routing',
						selected = [ route_to ]) ),
				HTMLgen.TD (
                	                HTMLgen.Href (HELP_URL % 'Date', \
						'Date'),
					HTMLgen.Text (' '), \
					HTMLgen.Text (wtslib.current_Time ()))))
		else:

			# we're editing an existing TR

			summary_table.append (HTMLgen.TR (
				HTMLgen.TD (
                                	HTMLgen.Href (HELP_URL % 'TR_Nr', \
						'TR #'),
					HTMLgen.Text (' '),
					HTMLgen.Text (self.data ['TR Nr']) ),
				HTMLgen.TD (
					HTMLgen.Href (HELP_URL % 'Forwarding',
						'Forward TR'),
					HTMLgen.Text (' '),
					HTMLgen.Select (category_list,
						name='Forwarding',
						selected = [ "don't route" ]))))
		# row 2 : title

		summary_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Title',
					'Title'), \
				HTMLgen.Text (' '), \
				HTMLgen.Input (type='text', \
					size=(DATE_SIZE * 2), \
					name='Title', \
					value= self.data ['Title']),
					colspan = 2 ) ) )

		# then do the table with the general information

		general_table = HTMLgen.TableLite (border=1, align='center', \
			cellpadding = 5)

		# row 1 : area, type, and needs attention by

		general_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Area',
					'Area'), \
				HTMLgen.BR (), \
				HTMLgen.Select ( \
					CV ['CV_WTS_Area'].pickList (selArea),
					size = SELECT_ROWS, multiple=1, \
					name='Area',
					selected = selArea) ),
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Type',
					'Type'), \
				HTMLgen.BR (), \
				HTMLgen.Select ( \
					CV ['CV_WTS_Type'].pickList (selType),
					size=SELECT_ROWS, multiple=1, \
					name='Type',
					selected = selType) ),
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Needs_Attention_By',
					'Needs Attention By (date)'), \
				HTMLgen.BR (), \
				HTMLgen.Input (type='text', size=DATE_SIZE, \
					name='Needs_Attention_By', 
					value=self.data ['Needs Attention By'])
				) ) )

		# row 2 : priority, requested by, status, and status date

		# do the two easy ones first - priority and req by

		row_2 = HTMLgen.TR ( \
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Priority', \
					'Priority'), \
				HTMLgen.BR (), \
				HTMLgen.Select ( \
					CV ['CV_WTS_Priority'].pickList ( \
						selPriority),
					name='Priority',
					selected = selPriority)),
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Requested_By',
					'Req By'), \
				HTMLgen.BR (), \
				HTMLgen.Select ( \
					CV ['CV_Staff'].pickList (selReqBy),
					size=SELECT_ROWS, multiple=1, \
					name='Requested_By',
					selected = selReqBy) ) )

		# now, we need to do status, which has two components

		item = HTMLgen.TD ( \
                        HTMLgen.Href (HELP_URL % 'Status',
				'Status'), \
			HTMLgen.BR (), \
			HTMLgen.Select ( \
				CV ['CV_WTS_Status'].pickList (selStatus),
				name='Status', selected = selStatus),
			HTMLgen.BR (),
                        HTMLgen.Href (HELP_URL % 'Status_Date',
				'Date'), \
			HTMLgen.BR () )

		item.append (HTMLgen.Input (type='text', name='Status_Date', \
			size = DATE_SIZE,
			value = wtslib.parse_DateTime ( \
				self.data ['Status Date'])[0]))
		item.append (HTMLgen.Input (type='hidden', name='Status_Staff',\
			value = self.data ['Status Staff']))

		# finally, add the status (in item) to the row, and then add
		# the row to the table

		row_2.append (item)
		general_table.append (row_2)

		# in preparation for row 3, format the dependencies by
		# appending a 'TR' to each number

                if self.data.has_key ('Depends On'):
			list = self.data ['Depends On'].values ()
			list.sort ()
                else:
			list = []
		dependencies = ''
		for item in list:
			dependencies = dependencies + ('TR%d, ' % item)
		dependencies = dependencies [:-2]

		# row 3 : size, dependencies, and directory

		row3 = HTMLgen.TR ()

		# first, add the cell for the Size field

		row3.append (HTMLgen.TD (
                        HTMLgen.Href (HELP_URL % 'Size', 'Size'),
			HTMLgen.BR (),
			HTMLgen.Select (CV ['CV_WTS_Size'].pickList (selSize),
				name='Size', selected = selSize) ) )

		# second, add the Depends On field

		row3.append (HTMLgen.TD (
                        HTMLgen.Href (HELP_URL % 'Depends_On',
				'Depends On'),
			HTMLgen.BR (),
			HTMLgen.Input (type='text', size=DATE_SIZE,
				name='Depends_On', value=dependencies) ))

		# third, we need to add the Directory information.  If we have
		# a defined Directory, then write it out as RawText so that it
		# will appear as a link.  (And, we also need to include it as a
		# hidden field so that it will go in as part of the submitted
		# tracking record.  If the Directory is None, then we should
		# write out a checkbox field named Create_Directory_Flag

		if str (self.data ['Directory']) != 'None':
			row3.append (HTMLgen.TD (
				HTMLgen.Href (HELP_URL % 'Directory',
					'Directory'), \
				HTMLgen.Text (' '),
				HTMLgen.RawText (str(self.data ['Directory']))))
		else:
			# Below the checkbox, we now need to write out the name
			# of the directory which would be created (if we know).

			if self.num () == 'None':
				# this is a new tracking record (with no number)
				# so we don't know what it's directory will be

				path = ''
			else:
				# get the names of the prospective project
				# directory and its parent

				(parent_dir, project_dir) = \
					newBaseDirectoryPieces (
						string.atoi (self.num ()))

				# build the full unix path to the parent
				# directory, then to the project directory

				path = os.path.join (
					Configuration.config ['baseUnixPath'],
					parent_dir)
				path = os.path.join (path, project_dir)

			row3.append (HTMLgen.TD (
				HTMLgen.Input (type='checkbox',
					name='Create_Directory_Flag',
					value='Create_Directory_Flag'),
				HTMLgen.Text ('Create '),
				HTMLgen.Href (HELP_URL % 'Directory',
					'Project Directory'),
				HTMLgen.BR (),
				HTMLgen.Text (path) ))

		general_table.append (row3)	# add the completed row 3

		# row 4 : staff, and two blank squares

		general_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Staff',
					'Staff'), \
				HTMLgen.BR (), \
				HTMLgen.Select ( \
					CV ['CV_Staff'].pickList(selStaff),
					size=SELECT_ROWS, multiple=1, \
					name='Staff', selected = selStaff)),
			HTMLgen.TD ( \
				HTMLgen.BR () ), \
			HTMLgen.TD ( \
				HTMLgen.BR () ), \
				) )

		# collect the objects so far, and put in dividng markers

		objects = [ summary_table, HTMLgen.P (), general_table, \
			HTMLgen.BR () ]

		# project definition - note that we need to escape all amperands
		#	in the text.  ("&" --> "&amp;")

		proj_def = self.data ['Project Definition']
		if proj_def is not None:
			proj_def = wtslib.escapeAmps (proj_def)

		objects.append (getTableWithTemplates ( \
			'Project Definition',
			'Project_Definition',
			proj_def, '1', TEXT_ROWS, TEXT_COLS,
			self.data['TR Nr']))

		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.BR () )

		# progress notes - note that we need to escape all amperands
		#	in the text.  ("&" --> "&amp;")

		notes = self.data ['Progress Notes']
		if notes is not None:
			notes = wtslib.escapeAmps (notes)

		objects.append (getTableWithTemplates ( \
			'Progress Notes',
			'Progress_Notes',
			notes, '2', TEXT_ROWS, TEXT_COLS,
			self.data['TR Nr']))

		objects.append ( HTMLgen.BR () )
		objects.append ( HTMLgen.BR () )

		# don't put status history on the edit screen (since it can't
		# be changed anyway)

		# we should, however, add a hidden field with the tracking
		# record number...  (to aid in saving the changes after
		# editing is finished)

		objects.append (HTMLgen.Input (type='hidden', name='TR_Nr', \
			value = self.data ['TR Nr']))

		return objects


	def isEmergency (self):
		# Purpose: test to see if this TR is an emergency
		# Returns: TRUE if self's Priority is 'emergency', or FALSE if
		#	not
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return (self.data ['Priority'] == 'emergency')


	def html_New_ShortForm (self):
		# Purpose: return a list of HTMLgen objects which represent
		#	this new tracking record on a short form
		# Returns: list of HTMLgen objects
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing
		# Notes: The display of a tracking record short form consists of
		#	two tables of information.  The top table holds two
		#	rows of addressing information, the first row with a
		#	the user name entering the tracking record, and the
		#	second row where he/she may choose a routing category.
		#	The lower table contains four fields (Priority, Needs
		#	Attention By, Size, and Project Definition)  This table
		#	is layed out as:
		#		Priority	Size	Needs Attention By
		#		Description
		#	The fieldnames on the form (as they would be submitted)
		#	include:
		#		Requested_By		Routing
		#		Needs_Attention_By	Priority
		#		Project_Definition	Size

		global SEND_TO_LIST, TYPE_LIST, HELP_URL, HELP_FILES

		DATE_SIZE = 20		# size of a date box

		# get lists of terms from the controlled vocabulary objects for
		# users, priorities, sizes, and routing categories.  As this
		# must be a new TR, just use the active terms (not retired).

		CV = Controlled_Vocab.cv
		user_list = CV ['CV_Staff'].ordered_names ()
		priority_list = CV ['CV_WTS_Priority'].ordered_names ()
		size_list = CV ['CV_WTS_Size'].ordered_names ()
		category_list = CV ['CV_WTS_Category'].ordered_names ()

		# suggestions - list of suggestionsf or things to include in
		# the Description field:

		suggestions = [ 'Machine Name', 'Query Name and Values', \
			'Web Form', 'Editing Interface Screen', \
			'Particular Fieldname', 'Exact Messages Displayed', \
			'Your Intentions' ]

		# first do the table for the addressing section

		# addressing_table is an HTMLgen table which represents the
		# address section of a request, encompassing Requested By and
		# the Routing category.

		addressing_table = HTMLgen.TableLite (border=1, \
			cellpadding=5, align='center')

		route_to = CV ['CV_WTS_Category'].key_dict () [
			CV ['CV_WTS_Category'].default_key () ]

		addressing_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Routing',
					'Route To'),
				HTMLgen.Text (' '), \
				HTMLgen.Select (category_list,
					name='Routing',
					selected = [ route_to ])
					),
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Requested_By',
					'Requested By'), \
				HTMLgen.Text (' '), \
				HTMLgen.Select (user_list,
					name='Requested_By',
					selected = [self.data ['Requested By']]
					) ) ) )
		addressing_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
                                HTMLgen.Href (HELP_URL % 'Title',
					'Title'), \
				HTMLgen.Text (' '), \
				HTMLgen.Input (type='text', \
					size=(DATE_SIZE * 2), \
					name='Title'), colspan = 2 ) ) )

		# then, do the table for the data section

		# data_table is an HTMLgen table which represents the data
		# section of a request, encompassing Priority, Request Type,
		# Needs Attention By, and Project Definition.  Also included are
		# a list of suggestions for the Project Definition field.  The
		# layout is:
		#	Priority 	| Size	| Suggestions
		#	-------------------------
		#	N.Attention By		|
		#	-------------------------------------
		#	Project Definition

		suggestions = [ 'Machine Name', 'Query Name and Values',
			'Web Form', 'Editing Interface Screen',
			'Particulary Fieldname', 'Exact Messages Displayed',
			'Your Intentions' ]

		data_table = HTMLgen.TableLite (border=1, \
			cellpadding=5, align='center')

		data_table.append (HTMLgen.TR ( \
			HTMLgen.TD ( \
				HTMLgen.Href (HELP_URL % 'Priority', \
					'Priority'),
				HTMLgen.Text (' '), \
				HTMLgen.Select (priority_list, \
					selected = [ self.data ['Priority']],
					name = 'Priority') ), \
			HTMLgen.TD (
				HTMLgen.Href (HELP_URL % 'Size', 'Size'), \
				HTMLgen.Text (' '), \
				HTMLgen.Select (size_list, name = 'Size') ),
			HTMLgen.TD (
				HTMLgen.Heading (4,
					'Project Definition Suggestions'),
				HTMLgen.P (),
				HTMLgen.BulletList (suggestions),
				rowspan = 2 ) ) )

		data_table.append (HTMLgen.TR (
			HTMLgen.TD (
				HTMLgen.Href (HELP_URL % 'Needs_Attention_By',
					'Needs Attention By'),
				HTMLgen.Text (' '),
				HTMLgen.Input (type='text', size=20,
					name='Needs_Attention_By',
					value=self.data ['Needs Attention By']),
					colspan = 2
				) ) )

		data_table.append (HTMLgen.TR ( \
			HTMLgen.TD (getTableWithTemplates ( \
					'Project Definition',
					'Project_Definition',
					'', '1', 15, 70,
					self.data['TR Nr']),
				colspan = 3) ) )

		hidden_fields = [
			HTMLgen.Input (type='hidden', name='Status',
				value = self.data ['Status']),
			HTMLgen.Input (type='hidden', name='Area',
				value = self.data ['Area']),
			HTMLgen.Input (type='hidden', name='Type',
				value = self.data ['Type']) ]

		# then, return both tables with a paragraph mark between them

		return [addressing_table, HTMLgen.P(), HTMLgen.P(),
			data_table] + hidden_fields


	def lock (self):
		# Purpose: locks the current tracking record for editing, to
		#	ensure that only one user edits this tracking record
		#	at a time
		# Returns: nothing
		# Assumes: that self is a tracking record that was loaded from
		#	the database.
		# Effects: locks the current tracking record for editing.
		# Throws: 1. TrackRec.alreadyLocked if this tracking record has
		#	already been locked by another user.  2. IndexError if
		#	this tracking record cannot be found in the database.
		#	3. wtslib.sqlError if there is a problem executing the
		#	SQL statements.
		# Notes: This should be an atomic operation, though it 
		#	currently is not.  We should be able to check the lock
		#	status and then lock it if possible in a single step.
		#	This is a global MGI problem, and can be addressed when
		#	the group finds a general solution.

                global alreadyLocked

		qry = '''select convert (varchar, locked_when, 100) locked_when,
				_Locked_Staff_key
			from WTS_TrackRec
			where (_TR_key = %s)''' % self.data['TR Nr']
		result = wtslib.sql (qry)

		# if it is already locked, then give up.

		if (result[0]['_Locked_Staff_key'] <> None):
			CV = Controlled_Vocab.cv ['CV_Staff'].key_dict ()
                        raise alreadyLocked, 'locked by %s on %s' % \
				(str (CV [result[0]['_Locked_Staff_key']]),
				result[0]['locked_when'])

		# otherwise, lock it.

		qry = '''update WTS_TrackRec
			set locked_when = getdate(),
				_Locked_Staff_key = s._Staff_key
			from WTS_TrackRec t, CV_Staff s
			where ((s.staff_username="%s") and
				(t._TR_key = %s))''' % \
				(os.environ['REMOTE_USER'], self.num ())
		result = wtslib.sql (qry)


	def num (self):
		# Purpose: returns the key of the current tracking record
		# Returns: string key of the current tracking record, if a key
		#	has been assigned (which it has if this tracking record
		#	was loaded from the database), or None if no key has
		#	yet been assigned (which means this is a new, unsaved
		#	tracking record).
		# Assumes: nothing
		# Effects: see returns
		# Throws:  nothing
		# Notes: Use this method with caution.  We should not let the
		#	key value just float around needlessly.  Make sure the
		#	code that calls this really needs the key value.

		return str (self.key_value)


	def load (self):
		# Purpose: load info for this tracking record from the database
		# Returns: nothing
		# Assumes: db's SQL routines have been initialized
		# Effects: clears all current tracking record information in
		#	self.data (except the key value), and loads in values
		#	for this tracking record from the database.
		# Throws: 1. ValueError if no tracking record with the current
		#	TR # exists in the database.  2. wtslib.sqlError if an
		#	error occurs in processing the SQL statements.

		global PROJECT_DEFINITION, PROGRESS_NOTES

		my_num = self.num ()		# get my tracking record number

		# reset all the values to defaults

		self.set_Defaults ()

		# The default value for the Project Definition field is a
		# template loaded from a file.  This is what we would expect
		# for a new tracking record, but it is not the behavior we want
		# when we load a tracking record.  (If we are loading a
		# tracking record, we may have already decided to delete this
		# template, in which case we don't want to do it again.)  So,
		# let's start the Project Definition field at None.

		self.set_Values ( { 'Project Definition' : None } )

		# we need to go to the database and lookup current values for
		# the tracking record.  Splitting this into multiple queries
		# and then using Python to combine the information has reduced
		# this operation from nearly a minute down to under 2 seconds.
		# Rick said this could be due to bad results from sybase's
		# query optimizer, which is only good for queries with 4-5
		# tables at most.

		# At a later date, we should simplify these queries.  As a
		# result of other revisions, all the controlled vocabulary info
		# that we need is already loaded in the Controlled_Vocab module.
		# We can remove all the extra joins to the CV_WTS_* tables,
		# just retrieve the keys, and then use Controlled_Vocab to
		# fill in the corresponding values.  (again, to be done later)

		queries =  [
                        # 0. general tracking record info and simple controlled
			#    vocabulary lookups
                        '''
                        select tr._TR_key, pri.priority_name,
                                size.size_name, stat.status_name,
                                staff1.staff_username status_staff_username,
                                convert (varchar, tr.attention_by, 100)
                                attention_by,
                                convert (varchar, tr.status_set_date, 100)
                                status_set_date, tr.tr_title,
                                tr.directory_variable,
                                convert (varchar, tr.modification_date, 100)
				modification_date
			from WTS_TrackRec tr, CV_WTS_Priority pri,
                                CV_WTS_Size size, CV_WTS_Status stat,
                                CV_Staff staff1
			where ((tr._Priority_key = pri._Priority_key) and
                                (tr._Size_key = size._Size_key) and 
                                (tr._Status_key = stat._Status_key) and
                                (tr._Status_Staff_key = staff1._Staff_key) and
                                (tr._TR_key = %s))''' % my_num,

                        # 1. the text blocks:  Progress Notes and Project
			#    Definition
			'''
                        select text_type, text_block
                        from WTS_Text
                        where (_TR_key = %s)''' % my_num,
			
                        # 2. status history of this tracking record
			'''
                        select sh._TR_key, stat.status_name,
                                staff.staff_username,
                                convert (varchar, sh.set_date, 100) set_date_txt
			from WTS_Status_History sh, CV_WTS_Status stat,
                               CV_Staff staff
                        where ((sh._Staff_key = staff._Staff_key) and
                                 (sh._Status_key = stat._Status_key) and
                                 (sh._TR_key = %s))
			order by sh.set_date desc''' % my_num,

                        # 3. dependencies of this tracking record
			'''
                        select _TR_key, _Related_TR_key
                        from WTS_Relationship
                        where ((relationship_type = %d) and
                                (transitive_closure = 0) and
                                (_TR_key = %s))''' % (DEPENDS_ON, my_num),

                        # 4. areas of this tracking record
			'''
                        select _TR_key, area_name area
                        from WTS_Area MMarea, CV_WTS_Area CVarea
                        where ((MMarea._Area_key = CVarea._Area_key)
                                and (MMarea._TR_key = %s))
			order by CVarea.area_order''' % my_num,
			
                        # 5. types of this tracking record
			'''
                        select _TR_key, type_name type
                        from WTS_Type MMtype, CV_WTS_Type CVtype
                        where ((MMtype._Type_key = CVtype._Type_key) and
                                (MMtype._TR_key = %s))
			order by CVtype.type_order''' % my_num,
			
                        # 6. staff members assigned to this tracking record
                        '''
                        select _TR_key, staff_username staff_list
                        from WTS_Staff_Assignment MMstaff, CV_Staff CVstaff
                        where ((MMstaff._Staff_key = CVstaff._Staff_key) and
                                (MMstaff._TR_key = %s))
			order by CVstaff.staff_grouping, CVstaff.staff_username
			''' % my_num,
			
                        # 7. staff members who requested this tracking record
                        '''
                        select _TR_key, staff_username requested_by
                        from WTS_Requested_By MMreqby, CV_Staff CVstaff
                        where ((MMreqby._Staff_key = CVstaff._Staff_key) and
	                        (MMreqby._TR_key = %s))
			order by CVstaff.staff_grouping, CVstaff.staff_username
			''' % my_num
			]

		results = wtslib.sql (queries)

                # results is now a list of lists of dictionaries.  It contains
                # eight elements.  Each element represents the results of a
                # SQL select statement and is a list of dictionaries, with one
                # dictionary per row returned by the query.  Roughly, results
                # items are:

                # [0] = general TR info:    [ { _TR_key, _Priority_key,
                #       (only one row)          _Size_key, _Status_key,
                #                               _Staff_key, attention_by,
                #                               status_set_date, tr_title,
                #                               directory_variable,
		#				modification_date }        ]
                # [1] = text fields:        [ { text_type, text_block } ... ]
                #       (0-3 rows)
                # [2] = m-m status history: [ { _TR_key, _Status_key,
                #                               _Staff_key, set_date_txt } ... ]
                # [3] = m-m relationships:  [ { _TR_key,
                #                               _Related_TR_key }       ... ]
                # [4] = m-m area:           [ { _TR_key, _Area_key }    ... ]
                # [5] = m-m type:           [ { _TR_key, _Type_key }    ... ]
                # [6] = m-m staff:          [ { _TR_key, _Staff_key }   ... ]
                # [7] = m-m requested by:   [ { _TR_key, _Staff_key }   ... ] 

		# put a call in here to parse & merge for the main tracking
                # record information (query 0).  There's only one tracking
		# record returned, so just get it and put it in record.
		# (This is where the ValueError may be raised, if we didn't
		# find the tracking record.)

		[ record ] = parse_And_Merge (results [0], '_TR_key')

		# convert the dates to the standard WTS format.  Since these
		# values are coming from the database, we know this is a valid
		# conversion, just dump the errors in a bogus temporary
		# variable named 'ignore_errors'

		record ['status_set_date'], ignore_errors = \
			wtslib.parse_DateTime ( \
				str (record ['status_set_date']))
		record ['attention_by'], ignore_errors = \
			wtslib.parse_DateTime (str (record ['attention_by']))
		record ['modification_date'], ignore_errors = \
			wtslib.parse_DateTime ( \
				str (record ['modification_date']))

		# We need to update the Directory field in the record to
		# reflect changes specified in the "Managing Project Directories
		# with WTS" document:  We now store a URL to this directory,
		# with the displayed text being the unix path for it.  (That's
		# what directoryURL() returns)

		if str (record ['directory_variable']) != 'None':
			record ['directory_variable'] = directoryURL (
				record ['directory_variable'])

                # now, pick the big text fields out of query 1

		record ['project_definition'] = ''
		record ['progress_notes'] = ''
		for row in results [1]:
			if row ['text_type'] == PROJECT_DEFINITION:
				record ['project_definition'] = \
					row ['text_block']
			elif row ['text_type'] == PROGRESS_NOTES:
				record ['progress_notes'] = row ['text_block']

                # now, get the status history info from query 2, starting with
		# the current status...

		temp = '%s - set by %s - effective %s, ' % \
			(record ['status_name'],
			record ['status_staff_username'],
			record ['status_set_date'])

		for row in results [2]:

			# get the date in the standard WTS format and ignore
			# any errors (there shouldn't be any since this is
			# coming directly from the database)

			date, ignore = wtslib.parse_DateTime (
				row ['set_date_txt'])

			temp = temp + row ['status_name'] + ' - set by ' + \
				row ['staff_username'] + ' - effective ' + \
				date + ', '
		record ['status_history'] = temp [:-2]

                # get the relationship info from query 3

		record ['depends_on'] = Set.Set ()
		for row in results [3]:
			record ['depends_on'].add (row ['_Related_TR_key'])

                # go through the rest of the queries (4-7) and tack on any
		# information

		extra_queries = range (4, len (results))
		for i in extra_queries:
			temp = parse_And_Merge (results [i], '_TR_key')
			if len (temp) > 0:
				key_list = temp[0].keys ()
				for k in key_list:
					if k <> '_TR_key':
						record [k] = temp [0][k]

		# now, put the values returned in the proper places in self

		self.set_Values (with_nice_names (record ))


	def save (self,
		newProjectDirectoryFlag = 0	# boolean; 1 if we are to
						# create a new project directory
						# for this tracking record
		):
		# Purpose: saves all fields for the current tracking record to
		#	the database
		# Returns: nothing
		# Assumes: 1. db's sql routines have been initialized.
		#	2. any user entries for this tracking record have come
		#	through TrackRec.validate_TrackRec_Entry okay.
		# Effects: may update, add, and delete rows to database tables:
		#	WTS_TrackRec, WTS_Relationship, WTS_Type, WTS_Area,
		#	WTS_Staff_Assignment, WTS_Text, WTS_Requested_By,
		#	WTS_Status_History.  New tracking records are handled
		#	by using sql insert statements.  Existing tracking
		#	records have their existing values updated by doing an
		#	update query on WTS_TrackRec, and then inserting and
		#	deleting rows in the other tables to handle fields with
		#	many-to-many relationships as needed.  This should help
		#	minimize the number of queries run.
		# Throws: 1. wtslib.sqlError if problems occur while running
		#	the sql statements; 2. propagates (from
		#	verify_Current_Lock ()) TrackRec.notLocked if the
		#	current user does not have the tracking record locked.
		# Notes: If this tracking record exists in the database (so this
		#	is an edit session), then before saving the tracking
		#	record, we must first verify that the current user has
		#	it locked.
		#	We should also note that we added the optional
		#	"newProjectDirectoryFlag" so that project directory
		#	creation could be done, and the directory_variable
		#	field updates handled in the same batch as the other
		#	database updates.

		global TR_NEW, TR_OLD		# operation types
		global CHMOD, CHGRP		# unix command paths

		# if self has no TrackRec key, then we need to allocate one
		# and treat self as a new tracking record.

		# the easiest way to handle this is with a two-step process.
		# part 1 has two options, A and B.

		# 1. do one of the following:
		#	A. if this is a new tracking record, then use an
		#		insert query on WTS_TrackRec
		#	B. if this is an existing tracking record, then do
		#		an update query on WTS_TrackRec
		# 2. now examine self.backup and self.data to see what 
		#	attributes have changed (what other tables need to
		#	be altered).  Use delete and insert queries as needed.

		# get easy references to the set of old values (backup) and
		# the set of controlled vocabularies

		backup = with_db_names (self.backup)
		CV = Controlled_Vocab.cv

		queries = []			# no queries yet

		# figure out how to handle WTS_TrackRec (based on whether
		# this is a new tracking record or not)

		if (self.key_value == None):

			method = TR_NEW		# do insert queries for new TR

			# since this is a new tracking record, we need to
			# allocate a new key value

			self.allocate_Key ()
			self.set_Values ( { 'TR Nr' : str(self.key_value) } )

			# we also need to set the status date and staff

			self.set_Values ( { \
				'Status Date' : wtslib.current_Time (),
				'Status Staff' : os.environ ['REMOTE_USER'] } )
		else:
			method = TR_OLD		# do update queries for old TR

			# before proceeding farther, let's verify that the
			# current user has a lock on this existing tracking
			# record.  TrackRec.notLocked is raised if he/she does
			# not have a lock.

			self.verify_Current_Lock ()

			# if we lost either the status date or status staff,
			# then assign current ones.  (could happen in an
			# external editing session.)

			if (len (self.data ['Status Date']) == 0) or \
				(len (self.data ['Status Staff']) == 0):
				self.set_Values ( { \
				'Status Date' : wtslib.current_Time (),
				'Status Staff' : os.environ ['REMOTE_USER'] } )

			# this is an existing TR, so we may need to archive
			# an entry in the status history (if we have a change
			# in status).

			# check to see if the status changed

			if self.data ['Status'] <> backup ['status_name']:

				# update the status staff field to be the user
				# who set the status (the current user)

				self.set_Values ({ 'Status Staff' :
					os.environ ['REMOTE_USER'] })

				# if the date was not changed by the user, then
				# set it to the current time.  (This allows the
				# user to pick an effective time for the status
				# change, and if he/she doesn't, we assume that
				# the change is effective as of now.)

				dateChanged = (self.data ['Status Date'] <> \
					backup ['status_set_date'])

				if not dateChanged:
					self.set_Values ( { 'Status Date' :
						wtslib.current_Time () } )

				# need to write a new entry to the status
				# history table.  (use the already-loaded
				# controlled vocab info to save unnecessary
				# joins in the query)

				staff_key = CV ['CV_Staff'] \
					[ backup ['status_staff_username'] ]
				status_key = CV ['CV_WTS_Status'] \
					[ backup ['status_name'] ]
				queries.append ( \
					'''insert WTS_Status_History (_TR_key,
						_Status_key, set_date,
						_Staff_key)
					values (%d, %d, "%s", %d)''' % \
					(backup ['_TR_key'], status_key,
					backup ['status_set_date'], staff_key)
					)

		# if we need to create a project directory, do it and update the
		# 'Directory' field in self.data:

		if newProjectDirectoryFlag != 0:
			# get the names of the project directory and its parent

			( parent_dir, project_dir ) = newBaseDirectoryPieces (
				string.atoi (self.num ()))

			# build the full unix path to the parent directory

			parent_path = os.path.join (
				Configuration.config ['baseUnixPath'],
				parent_dir)

			# if the parent directory does not yet exist, create it,
			# turn on its sticky bit, and set the group to 'mgi'

			if not os.path.exists (parent_path):
				os.mkdir (parent_path)
				os.chmod (parent_path, 0755)	# rwxr-xr-x

				# We need to do two system calls here, one
				# because python only uses octal mode for chmod
				# and the sticky bit can't be set using octal
				# mode, and the other because python does not
				# provide a chgrp function.

				os.system ('%s g+s %s' % (CHMOD, parent_path))
				os.system ('%s mgi %s' % (CHGRP, parent_path))

			# finally, create the project directory, make it
			# writable by the group, turn on its sticky bit, and
			# record its name (from the parent directory down) in
			# this object's "Directory" field.

			self.set_Values ( { 'Directory' : 
				os.path.join (parent_dir, project_dir) } )

			project_path = os.path.join (parent_path, project_dir)

			os.mkdir (project_path)
			os.chmod (project_path, 0775)		# rwxrwxr-x

			# We need to do two system calls here, one because
			# python only uses octal mode for chmod and the sticky
			# bit can't be set using octal mode, and the other
			# because python does not provide a chgrp function.

			os.system ('%s g+s %s' % (CHMOD, project_path))
			os.system ('%s mgi %s' % (CHGRP, project_path))

		# now, get a dictionary of database fieldnames and the
		# current values

		values = with_db_names (self.dict ())

		# now, collect the necessary queries:

		queries = queries + save_WTS_TrackRec (values, method)
		queries = queries + save_Standard_M2M (values, backup, method)
		queries = queries + save_Text_Fields (values, backup, method)
		queries = queries + save_Relationships (values, backup, method)

		# execute the queries...

		result = wtslib.sql (queries)

		# and, update the transitive closure (only if the "Depends On"
		# field has changed).  Give the TR number, the constant for the
		# "depends on" relationship, the old value of the "Depends On"
		# field, and the new value of the field to the new
		# updateTransitiveClosure function.

		if not backup ['depends_on'].equals (values ['depends_on']):
			updateTransitiveClosure (
				string.atoi (self.num ()),	# TR number
				DEPENDS_ON)

		# We also need to update the .htaccess mappings in the project
		# directories, if we changed this project's title:

		if values ['tr_title'] != backup ['tr_title']:
			try:
				rebuild_htaccess (string.atoi (self.num ()))
			except:
				pass	# if it failed, no big deal.  ignore it.

		# and, copy the newly saved data into self.backup so that it
		# represents what is currently in the database

		self.backup = copy.deepcopy (self.data)
		return

		
	def set_Defaults (self):
		# Purpose: reset all attributes of this tracking record to
		#	their defaults, but leave the TR # intact if one exists
		# Returns: nothing
		# Assumes: nothing
		# Effects: see purpose.  We check for an existing TR # in case
		#	we would want to reset the values of an existing
		#	tracking record.  (in which case, we wouldn't want to
		#	also reset the TR # to be None)
		# Throws: nothing

		# if we don't have a defined TR #, then set it to None.
		# otherwise, just leave it alone.

		if not self.data.has_key ('TR Nr'):
			self.set_Values ( { 'TR Nr' : None } )

		self.set_Values ( { \
			'Priority' : 'unknown', \
			'Status Staff' : os.environ ['REMOTE_USER'], \
			'Size' : 'unknown', \
			'Status' : 'new', \
			'Status Date' : wtslib.current_Time(), \
			'Title' : None, \
			'Directory' : None, \
			'Depends On' : Set.Set (),
			'Type' : 'unknown',
			'Area' : 'unknown',
			'Project Definition' : None,
			'Progress Notes' : None,
			'Needs Attention By' : None,
			'Requested By' : os.environ['REMOTE_USER'],
			'Status History' : None,
			'Staff' : None } )
		return


	def set_Values (self,
		dict		# dictionary with object fieldnames as keys
				# which refer to the values we would like to
				# set for those fieldnames in this object
		):
		# Purpose: set the data values for this object to be those
		#	specified in "dict"
		# Returns: nothing
		# Assumes: nothing
		# Effects: For each key of "dict", get its value from "dict".
		#	Set that value for the corresponding object fieldname
		#	(in the TrackRec object).  Uses the parent class
		#	"WTS_DB_Object" to do the initial processing, and then
		#	processes the large text fields (Project Definition and
		#	Progress Notes) to trim all lines to, at most, 80 chars.
		# Throws: nothing
		# Notes: This method only changes values in memory, not in the
		#	database.  Be sure to use the save() method as needed
		#	to commit changes to the database.
		# Example: see the corresponding method in WTS_DB_Object class.

		# use the default behavior from the parent class

		WTS_DB_Object.WTS_DB_Object.set_Values (self, dict)

		# now, trim the two large text fields as needed

		big_text_fields = [ 'Project Definition', 'Progress Notes' ]

		for fieldname in big_text_fields:
			if self.data.has_key (fieldname):
				if self.data [fieldname] is not None:
					# Before proceeding to split up the
					# field (if needed), we need to check
					# that the field is preformatted here.
					# We don't want to go reformatting
					# HTML-formatted text.

					if wtslib.isPRE (self.data [fieldname]):
						self.data [fieldname] = \
							wtslib.wrapLines ( \
								self.data [
								fieldname ], 80)
		return


	def unlock (self,
		override = None		# set this to be non-None if we need to
					# unlock the tracking record regardless
					# of who has it locked.
		):
		# Purpose: unlock the current tracking record so that it may be
		#	edited by other users
		# Returns: nothing
		# Assumes: db's sql routines have been initialized
		# Effects: clears the locking information for this tracking
		#	record in the database (the _Locked_Staff_key and
		#	locked_when fields in the WTS_TrackRec table).
		# Throws: 1. wtslib.sqlError if a problem occurs when executing
		#	the sql statement; 2. TrackRec.notLocked is propagated
		#	from verify_Current_Lock if the current user does not
		#	have a lock on this existing tracking record
		# Notes: We normally test to see if the current user has a lock
		#	on this tracking record.  However, we need to be able
		#	to allow the command line interface to override this
		#	behavior.  (We need to be able to free errant locks,
		#	even if the locking staff member is on vacation.)

		# if "override" is not set, then before proceeding farther,
		# let's verify that the current user has a lock on this
		# existing tracking record.  TrackRec.notLocked is raised if
		# he/she does not have a lock.

		if override == None:
			self.verify_Current_Lock ()

		qry = '''update WTS_TrackRec
			set _Locked_Staff_key = null, locked_when = null
			where (_TR_key= %s)''' % self.data ['TR Nr']
		result = wtslib.sql (qry)
		return


	def verify_Current_Lock (self):
		# Purpose: verify that the current user has a lock on this
		#	tracking record
		# Returns: nothing
		# Assumes: db's sql routines have been initialized
		# Effects: contacts the database to see who, if anyone, has this
		#	tracking record locked.  If not the current user, then
		#	raise an exception.
		# Throws: 1. wtslib.sqlError if a problem occurs in executing
		#	the SQL statements; 2. TrackRec.notLocked if the current
		#	user does not have a valid lock on this tracking record.

                global notLocked

		# get the current locking information from the database

		qry = '''select convert (varchar, tr.locked_when, 100)
				locked_when, cv.staff_username staff_username
			from	WTS_TrackRec tr, CV_Staff cv
			where	(tr._TR_key = %s) and
				(tr._Locked_Staff_key = cv._Staff_key)''' % \
			self.num ()
		result = wtslib.sql (qry)

		# if it not locked, then raise the notLocked exception

		if (len (result) == 0):
			raise notLocked, 'no valid lock on TR %s' % self.num ()	

		# if it is locked by a different user, then raise the notLocked
		# exception, with the more detailed value information

		if result [0]['staff_username'] != os.environ ['REMOTE_USER']:
			s = 'no valid lock on TR %s.  ' % self.num ()
			s = s + 'It was locked by %s on %s.' % \
				(result [0]['staff_username'],
				result [0]['locked_when'])
			raise notLocked, s

		return		# otherwise, it is locked by the current user

### End of Class: TrackRec ###

#-MODULE FUNCTIONS------------------------------------------------

def build_And_Run_SQL (
	clean_dict	# a validated dictionary of fieldname -> desired values
			# (from the tracking record Query Form) to use in
			# generating and running queries
	):
	# Purpose: builds and runs the SQL queries as specified by the user on
	#	the tracking record Query Form
	# Returns: a list of dictionaries (as returned from db.sql ()),
	#	each of which corresponds to a single tracking record.  Recall
	#	that a query returns all tracking records that meet the
	#	constraints of the user's query.
	# Assumes: 1. db's sql routines have been initialized.
	#	2. clean_dict has no bad values -- it has been validated by
	#	TrackRec.validate_Query_Form.  3. proper values for Display,
	#	Primary, Secondary, Tertiary, Primary Order, Secondary Order,
	#	and Tertiary Order are defined in clean_dict.
	# Effects: Builds queries to retrieve tracking record information from
	#	the database, using the query constraints specified in
	#	clean_dict.  Combines the results of these queries to generate
	#	the list of dictionaries (each of which contains the data for a
	#	single tracking record) returned.
	# Throws: wtslib.sqlError if an error occurs while running the SQL
	#	statements
	# Notes: Each dictionary in the list returned will have the same keys.
	#	The keys, however, vary depending on the clean_dict which was
	#	passed in.  This is to accomodate the fact that, on the query
	#	form, we can check off which fields we would like to have
	#	displayed.  We make sure to only get and return only those
	#	fields, saving both time and space.
	#
	#	In order to build a query we create four lists:  "select",
	#	"frm", "where", and "order".  (They represent the SELECT, FROM,
	#	WHERE, and ORDER BY parts of a SQL query, and are explained
	#	when initialized below.)
	#
	#	A family of functions (consider_* ()) are called one after
	#	another to build the SQL statement based on the constraints
	#	specified in "clean_dict".  They do this by adding to the
	#	"select", "frm", "where", and "order" lists as needed.  Each
	#	one of these functions considers (or takes responsibility for)
	#	a single type of field.  For example, "consider_date ()" is
	#	used to update the lists for any date fields in the query.
	#
	#	The list "order" is built by pulling out from "clean_dict" the
	#	three database fields to order the results by (Primary,
	#	Secondary, and Tertiary) and the direction of order (asc, desc)
	#	for each of them (Primary Order, Secondary Order, and Tertiary
	#	Order).  Each "consider" function then checks the "order" list
	#	to look for the fieldname it is responsible for and the
	#	"ordering" tuple to find its associated direction; if it finds
	#	it, then we need to sort by that field and we update the lists
	#	as needed.
	#
	#	Sorting can be a little tricky.  For single-valued controlled
	#	vocabulary fields (Size, Status, etc.) we sort using a
	#	"sort_order" column in the CV table.  For dates, we need to
	#	sort by the datetime value while returning a properly formatted
	#	string value.  For varchar fields, we just sort alphabetically.
	#	All these can be done in the database (which we expect will
	#	provide a performance benefit).  If, however, we need to sort
	#	by one or more of the multi-valued controlled vocabulary fields,
	#	we need to use Python to assemble each value from the many-to-
	#	many relationships in the database.  This means that we've
	#	already brought the data (unordered) out of the database.  So,
	#	in that case, we just sort it in Python.
	#
	#	As a final note, the "Directory" field requires special
	#	handling.  The database stores only a relative directory.  We
	#	really want to return a URL to that directory.  So, as a final
	#	data cleanup, we replace values in the Directory field (if there
	#	is one) with the appropriate URL.

	global NAME_TO_DB

	# main parts of the select query

	select = []			# list containing strings, each of which
					# is one field to go in the "select"
					# clause of a SQL select statement

	frm = [ 'WTS_TrackRec tr' ]	# list of strings, each of which is one
					# table name (and optional abbreviation)
					# to go in the "from" clause of a SQL
					# select statement

	where = []	# list of strings, each of which is a clause which
			# should be "and"-ed with the others in the "where"
			# portion of a SQL select statement.  These clauses are
			# those used to specify selection criteria (as opposed
			# to those in "joins").

	joins = []	# list of strings, each of which is a clause used to
			# join tables (when included in the "where" clause of a
			# SQL select statement.  These will be "and"-ed with
			# those in "where" to produce the full "where" clause
			# of a query.

	order = [ None, None, None ]	# list of three items, each of which is
					# either a string or None.  Each string
					# specifies one fieldname by which to
					# sort in the SQL select statement we
					# are producing.  order [i] is the i-th
					# field to sort by.

        clean_keys = clean_dict.keys ()		# all fieldnames defined in
						# the input dictionary

        # organize info about how the results will be sorted.  Define a tuple
        # with three items, one for each level of sorting.  Each item in the
	# tuple is the name of the field to sort by at that level.  For example,
	# if the user chose to sort by Size, then Type, with no third level,
	# "sorting" would be: ('Size', 'Type', 'None')

       	sorting = ( clean_dict ['Primary'], clean_dict ['Secondary'], \
			clean_dict ['Tertiary'] )

        # get info about the ordering of each sort field (asc or desc).  The
	# three entries in "ordering" are parallel to those in "sorting".  If,
	# in the above example, the user left the default ascending order for
	# the first and third levels, but wanted descending order for the
	# second level, "ordering" would be:  ('asc', 'desc', 'asc')

	ordering = (	clean_dict ['Primary Order'], \
			clean_dict ['Secondary Order'], \
			clean_dict ['Tertiary Order'] )	

	# get a list of fields to display.  "to_display" uses the object field-
	# names.  For example, if the user checked for us to display the Area,
	# Type, and Size fields, then to_display would be:
	#	[ 'Area', 'Type', 'Size' ]
	# Note that spaces in the "Displays" string were stripped out during
	# the validation process.

	to_display = wtslib.string_To_List (clean_dict ['Displays'], ',')

	# "keys_to_display" is parallel to "to_display", except that it contains
	# the equivalent database fieldnames.  For the above example,
	# "keys_to_display" would be:  [ 'area', 'type', 'size_name' ]

	keys_to_display = []
	for item in to_display:
		keys_to_display.append ( NAME_TO_DB [item] )

	# now, go through field-by-field and handle each individually.

	# *** TR number ***

	select.append ('tr._TR_key')		# tracking record number is
						# always selected for display

	consider_TR_Nr (clean_dict, clean_keys, where, sorting, order, ordering)

	# *** Title and Directory (both use 'like' clauses) ***

	consider_simpleText ('Title', 'tr.tr_title', to_display, select,
		clean_dict, clean_keys, where, sorting, order, ordering)
	consider_simpleText ('Directory', 'tr.directory_variable', to_display,
		select, clean_dict, clean_keys, where, sorting, order, ordering)

	# *** Single-valued Controlled Vocabularies ***

	# take the three single-valued controlled vocabulary fields into
	# consideration when building the query

	single_cv_fields = [	# temporary variable for controlled vocabulary
				# field information.
		('Priority', 'tr._Priority_key', 'CV_WTS_Priority cpr', \
			'cpr._Priority_key', 'cpr.priority_order'), 
		('Size', 'tr._Size_key', 'CV_WTS_Size csi', 'csi._Size_key', \
			'csi.size_order') ]

	if not clean_dict.has_key ('Status Date'):
		single_cv_fields.append ( ('Status', 'tr._Status_key',
			'CV_WTS_Status cst', 'cst._Status_key',
			'cst.status_order') )
		queries = []
		tbl = ''
		tbl_abbrev = 'tr'
	else:
		[ startDate, stopDate ] = string.split (
			clean_dict ['Status Date'], '..')
		tbl, queries = getSqlForTempStatusTable (startDate, stopDate)
		tbl_abbrev = 'hs'
		single_cv_fields.append ( ('Status',
			'%s._Status_key' % tbl_abbrev,
			'CV_WTS_Status cst', 'cst._Status_key',
			'cst.status_order') )
		frm.append ('%s %s' % (tbl, tbl_abbrev))
		joins.append ('(%s._TR_key = tr._TR_key)' % tbl_abbrev)


	for (name, main_fieldname, cv_table, cv_fieldname, priority_fieldname) \
		in single_cv_fields:

		consider_single_valued_cv (name, main_fieldname, cv_table,
			cv_fieldname, priority_fieldname, to_display, select,
			clean_dict, clean_keys, where, joins, sorting, order,
			ordering, frm)

	# *** Date Fields (all use relational operators) ***

	# take the three date fields into consideration when building the query

	date_fields = [		# temporary variable to describe date fields
		('Needs Attention By', 'tr.attention_by',
			'sortable_attention_by'),
		('Status Date', '%s.status_set_date' % tbl_abbrev,
			'sortable_status_set_date'),
		('Modification Date', 'tr.modification_date',
			'sortable_modification_date') ]

	for (name, fieldname, sortable_fieldname) in date_fields:
		consider_date (name, fieldname, sortable_fieldname, to_display,
			select, clean_dict, clean_keys, where, sorting, order,
			ordering)

	# *** Multi-valued Controlled Vocabularies ***

	# For multi-valued controlled vocabulary fields, we can only use them
	# to help define our search criteria at this point.  (In other words,
	# we look to see if we need to include any info from them in the
	# "where" clause of a sql select statement -- we do not actually 
	# retrieve values for those fields yet.)

	python_sort = 0		# boolean (0/1) - assume that we don't need to
				# do the sorting in python, but rather that we
				# can do it in the database.  If at least one
				# multi-valued field is needed for sorting,
				# then we can't do it in the database.
	display_multi = 0	# boolean (0/1) - assume that we don't need to
				# display any of these multi-valued fields.  If
				# we need to display even one of these fields,
				# then we need to set this boolean for use later
				# on.
	temp_sort = 0		# temporary variable - boolean to indicate
				# whether the multi-valued controlled vocab in
				# this iteration of the loop requires us to
				# sort the results using Python.
	temp_display = 0	# temporary variable - boolean to indicate
				# whether the multi-valued controlled vocab in
				# this iteration of the loop needs to be
				# displayed in the results.

	multi_cv = [		# temporary variable for controlled vocab info
		('Area', 'WTS_Area', 'ar', '_Area_key'),
		('Type', 'WTS_Type', 'ty', '_Type_key'),
		('Requested By', 'WTS_Requested_By', 'rq', '_Staff_key'), 
		('Staff', 'WTS_Staff_Assignment', 'st', '_Staff_key') ]

	# go through and check each multi-valued controlled vocabulary field to
	# see if it is needed for sorting or display

	for (name, mm_table, abbrev, fieldname) in multi_cv:
		temp_sort, temp_display = consider_multi_valued_cv (name,
			mm_table, abbrev, fieldname, to_display, clean_dict,
			clean_keys, where, joins, sorting, frm)
		python_sort = python_sort or temp_sort
		display_multi = display_multi or temp_display

	# *** Big Text fields (define selection criteria only) ***

	# big text fields are not used for sorting or display on the query
	# results form.  They are only used in defining selection criteria.

	if 'Text Fields' in clean_keys:
		frm.append ('WTS_Text tx')	# put new table in From list

		# now, add clauses to the "joins" list that link the main
		# tracking record (in tr) to its big text fields (in tx), and
		# add to "where" to restrict the selection to only those
		# tracking records which have the entered value in one of its
		# text fields.

		joins.append ('tr._TR_key = tx._TR_key')
		where.append ('tx.text_block like "%s%s%s"' % \
			("%", clean_dict ['Text Fields'], "%"))

	# at this point, we have enough information to generate and run the
	# first query, which:
	#	selects based on basic info in WTS_TrackRec
	#	returns info from fields in WTS_TrackRec
	#	selects based on many-to-many relationships
	#	selects based on Text data (project definition, progress notes)
	# and since all selected fields (to be returned by the query) are from
	# WTS_TrackRec, each row returned should be one tracking record.

	# we're going to be working a lot with a temporary table in the
	# database.  Let's build and remember its name in temp_table:

	temp_table = '#TMP_Query_%s' % os.environ ['REMOTE_USER']

	# now, build the initial query which selects all the fields we have
	# noted so far (select) from the various tables we have noted (frm),
	# and puts that information in the specified temp_table

	qry = 'select %s into %s from %s' % \
		(wtslib.list_To_String (select), temp_table,
		wtslib.list_To_String (frm))

	# now, we need to complete the initial query by AND-ing all the clauses
	# in "where" together with those in "joins", and putting them in a
	# WHERE clause at the end of the SQL select statement:

	if len (where + joins) > 0:	# if there were any restrictions/joins
		qry = qry + ' where '
		for clause in where + joins:
			qry = qry + '(%s) and ' % clause

		qry = qry [:-5]			# trim final ' and ' at the end

	queries.append (qry)

	# now, we need to handle the "depends on" relationships if either
	# related checkbox ('X Depends On' or 'Depends on X') is checked.  If
	# either is checked, several queries are generated to add more tracking
	# record information to temp_table; we need to append these queries to
	# the list of queries.

	queries = queries + consider_dependencies (temp_table, select, frm,
				joins,
				'X Depends On' in clean_keys,	# 0/1
				'Depends On X' in clean_keys)	# 0/1

	# now, go and pull the results out of the temp table (with sorting,
	# if we can do it in the database).  The temp table should contain the
	# basic information (all that found in WTS_TrackRec) for all tracking
	# records which meet the query criteria.  It does not contain any of
	# the data from the many-to-many relationships.

	main_query_position = len (queries)	# remember the position of the
						# query which is used to get
						# the information from the
						# database (the one we're about
						# to add)
	if not python_sort:

		# if we don't have to sort in Python, then we can do the
		# sorting directly in the database.  (This is preferred)

                order = remove (order, None)	# remove any remaining None-s
						# since they are irrelevant to
						# ordering the records (and
						# would cause problems in the
						# query generation.
		queries.append ('''
			select *
			from %s
			order by %s''' % \
				(temp_table, wtslib.list_To_String (order)))
	else:
		# otherwise, we'll just extract the data and sort it later
		# in Python.

		queries.append ('select * from %s' % temp_table)

	# at this point, we have retrieved the basic information for the
	# tracking records to be displayed.  We still have another main
	# concern:  multi-valued controlled vocabulary fields.  We may just
	# need to retrieve them for display, or we may need to use them in
	# the sorting process.  (We may not need to do either)

	queried_cv = {}	# dictionary which will use as keys the names of multi-
			# valued controlled vocabulary fields which we need to
			# look up.  Each key has as its value the index into
			# queries (same as the index into results a little
			# farther down) where we look up the values for that
			# field.

	if (python_sort or display_multi):
		lookup_multi_valued_cv (temp_table, multi_cv, to_display,
			sorting, queries, queried_cv)

	# finally, we have built SQL statements to put all the data in
	# temp_table.  We have built SQL statements to extract that data.  Now,
	# add the last SQL statement to clean up after ourselves - drop the
	# temp tables.

	for t in [ temp_table, tbl ]:
		if t != '':
			queries.append ('drop table %s' % t)

	# finally, run all the queries and get the results

	results = wtslib.sql (queries)

	# results has an extremely variable format, totally depending on the
	# options chosen by the user on the tracking record query form.  It is
	# a list of lists of dictionaries, as is typical when multiple sets
	# of SQL results come back from wtslib.sql or db.sql.  Here's a
	# very general overview of its format:

	# results [0] - 	results of query to select basic tracking record
	#			info from WTS_TrackRec for those matching the
	#			basic (non-dependency) query criteria.  Its
	#			results were put into temp_table, so it returns
	#			[].
	# results [1..main_query_position - 1] - up to four queries to handle
	#			dependencies among tracking records if the user
	#			selected "Depends On X" or "X Depends On" at the
	#			query form.  These queries add info to
	#			temp_table and so should each return [].
	# results [main_query_position] - this result is a list of dictionaries,
	#			each of which is a row from temp_table (which
	#			is the basic data for the tracking records
	#			selected).  If we were able to do sorting in
	#			the database, then the dictionaries in this
	#			list are in the proper order.  The variable
	#			main_query_position will be between 1 and 5,
	#			depending on how many queries were used above
	#			for dependencies.  Each dictionary has the same
	#			set of keys; however, that set will vary
	#			depending on which options for display and
	#			sorting the user selected on the query form.
	# results [main_query_position + 1..] -	up to four entries remain in
	#			results, depending on how many of the multi-
	#			valued controlled vocabulary fields were
	#			selected for display or sorting.  Each of these
	#			results will be a list of dictionaries.  Each
	#			dictionary will contain a tracking record key
	#			(_TR_key) and a controlled vocab index (_*_key).
	#			A given tracking record key may occur in
	#			multiple dictionaries, as each will contain only
	#			one c.v. value.  Each of these results is
	#			indexed in queried_cv [attribute name].  So, if
	#			we asked to display Area, the data retrieved for
	#			it would be at:  results [queried_cv ['Area']].
	# There could be up to two additional entries which are empty sets of
	# results.  These are from dropping temp tables as needed.

	# Since list traversal is very slow, let's build a dictionary keyed
	# by tracking record numbers which refer to the actual dictionaries of
	# information for their tracking records.

	track_recs = {}		# dictionary of [ tr # ] ==> { tr info }

	# the main query has one dictionary of basic information for each
	# tracking record which fits the query criteria.  Use its (mandatory)
	# _TR_key field as its key in track_recs.

	for row in results [ main_query_position ]:
		track_recs [ row [ '_TR_key' ] ] = row

	tr_numbers = track_recs.keys ()		# get all tracking record
						# numbers returned in query

	# Now we need to merge the many-to-many relationships returned with the
	# basic tracking record info already returned

	# first, add the entries from the m-m controlled vocabs

	compile_multi_valued_cv (track_recs, tr_numbers, queried_cv, results)
	
	# now do single-valued controlled-vocabulary lookups where necessary.

	compile_single_valued_cv (track_recs, tr_numbers)

	# We have now pulled all the data together in track_recs, an unsorted
	# dictionary.  We need to pull the information back out of it and put
	# it in a list in the proper sorted order.

	final_results = []	# will contain dictionaries (each of which is
				# the data for a single tracking record) in the
				# order requested by the user on the query form

	if not python_sort:	# if we don't need to do the sorting in python,
				# then we already did it in the database.  We
				# have done all our updates using track_recs,
				# which is a dictionary of references to mutable
				# objects (one dictionary for each tracking
				# record) in the main query results.  So, the
				# results for the main query are already sorted
				# and can be used as our final_results.

		final_results = results [ main_query_position ]

	else:
		# pass relevant information in to the sort_results function
		# which will produce the sorted list in final_results

		final_results = sort_results (track_recs, tr_numbers, sorting,
			ordering)

	# now, strip out unnecessary fields (some were only used to aid in
	# sorting the results, and we only want to return the fields which the
	# user asked to display.

	global DB_TO_NAME		# we need to convert the key names from
					# their database fieldnames to the
					# object attribute names for the user.
	for row in final_results:

		# for each tracking record, look at each field...

		for field in row.keys():

			# if we need to display this field, then add a new
			# entry with the same value keyed by the corresponding
			# object attribute name (which is more easily readable)

			if field in keys_to_display:
				row [ DB_TO_NAME [field]] = row [field]

			del row [field]		# then delete the old field

		# and, if there is a Directory field, then replace its value
		# with the appropriate URL

		if row.has_key ('Directory'):
			if str (row ['Directory']) != 'None':
				row ['Directory'] = \
					directoryURL (row ['Directory'])

	return final_results

# --- begin helper functions for build_And_Run_SQL --- #

def consider_TR_Nr (
	clean_dict,	# validated dictionary of fieldname -> desired value
			# pairs to use in generating and running queries.
	clean_keys,	# list of keys in clean_dict
	where,		# list of string clauses for the "where" part of a
			# SQL select statement.
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	order,		# three-item list containing string clauses on how to
			# sort the results.  (for the "order by" part of a
			# SQL select statement)
	ordering	# three-item tuple containing a string identifying how
			# each level of sorting should be conducted:
			# ('asc' = ascending order, 'desc' = descending order)
	):
	# Purpose: to alter "order" and append to "where" such that we are
	#	selecting results based partly on tracking record number
	# Returns: nothing
	# Assumes: nothing
	# Effects: Alters "where" if we need to select the query results based
	#	on the tracking record number (appends strings of clauses
	#	suitable for inclusion in the "where" part of a SQL select
	#	statement).
	#	Alters "order" if we need to sort by the tracking record number
	#	(builds a clause which is suitable for inclusion in the "order
	#	by" part of a SQL select statement).
	# Throws: nothing

	# if we have a query restriction based on tracking record number...

	if 'TR Nr' in clean_keys:		# add where clauses
		tr_where = ''		# local temporary variable used to
					# collect OR-ed together clauses for
					# the "where" part of a query.

		# note that, in validation of clean_dict, the value for key
		# 'TR Nr' now is a list of strings of clauses.  Simply add
		# each clause to tr_where, preceded by an or.

		for item in clean_dict ['TR Nr']:
			tr_where = tr_where + ' or ' + item

		where.append (tr_where [4:])	# strip the leading ' or ' and
						# add this string of clauses to
						# where.

	# there are up to three levels of sorting.  Go through each, and see if
	# it is based on TR #.  If so, set the corresponding item in order to
	# be the name of the field and the 'asc' or 'desc' designation.

	for i in [0, 1, 2]:
		if sorting [i] == 'TR Nr':
			order [i] = '_TR_key ' + ordering [i]
	return

def consider_simpleText (
	name,		# name of the field (in object attribute (user-readable)
			# form) to examine
	fieldname,	# name of the corresponding field in the database,
			# including a two-letter abbreviation for the table name
	to_display,	# list of names of object attributes to display
	select,		# list of fieldnames to select from the database
	clean_dict,	# validated dictionary of fieldname -> desired value
			# pairs to use in generating and running queries.
	clean_keys,	# list of keys in clean_dict
	where,		# list of string clauses for the "where" part of a
			# SQL select statement.
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	order,		# three-item list containing string clauses on how to
			# sort the results.  (for the "order by" part of a
			# SQL select statement)
	ordering	# three-item tuple containing a string identifying how
			# each level of sorting should be conducted:
			# ('asc' = ascending order, 'desc' = descending order)
	):
	# Purpose: to alter select, order, and where such that we are selecting
	#	results based partly on the specified object attribute (name)
	# Returns: nothing
	# Assumes: fieldname is of the form "X.Y" where X is the two-letter
	#	abbreviation of a table name and Y is the fieldname within it.
	# Effects: Alters where if we need to select the query results based on
	#	the specified object attribute (appends strings of clauses
	#	suitable for inclusion in the "where" and "select" parts of a
	#	SQL select statement). 	Alters order if we need to sort by the
	#	specified object attribute (builds a clause which is suitable
	#	for inclusion in the "order by" part of a SQL select statement.
	# Throws: nothing

	if name in to_display:			# if we need to display it,
		select.append (fieldname)	# then add it to the select list

	# if this attribute name is in the list of keys for the cleaned
	# dictionary, then the user entered a restriction for use in the "where"
	# part of the query.  Add a clause to where which will search anywhere
	# in the associated field for the specified string.

	if name in clean_keys:
		where.append ('%s like "%s%s%s"' % \
			(fieldname, "%", clean_dict [name], "%"))

	# there are up to three levels of sorting.  Go through each, and see if
	# it is based on the specified object attribute.  If so, set the
	# corresponding item in order to be the name of the field (without the
	# leading table abbreviation) and the 'asc' or 'desc' designation.

	for i in [ 0, 1, 2 ]:
		if sorting [i] == name:
			order [i] = fieldname [3:] + ' ' + ordering [i]
	return


def consider_date (
	name,		# name of the date field (in object attribute (user-
			# readable) form) to examine, e.g.- "Needs Attention By"
	fieldname,	# name of the corresponding field in the database,
			# including a two-letter abbreviation for the table name
	sort_fieldname,	# name of the new fieldname to create for sorting
			# purposes.  (the regular fieldname will be converted
			# from a datetime to a string, which isn't easily
			# sortable).
	to_display,	# list of names of object attributes to display
	select,		# list of fieldnames to select from the database
	clean_dict,	# validated dictionary of fieldname -> desired value
			# pairs to use in generating and running queries.
	clean_keys,	# list of keys in clean_dict
	where,		# list of string clauses for the "where" part of a
			# SQL select statement.
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	order,		# three-item list containing string clauses on how to
			# sort the results.  (for the "order by" part of a
			# SQL select statement)
	ordering	# three-item tuple containing a string identifying how
			# each level of sorting should be conducted:
			# ('asc' = ascending order, 'desc' = descending order)
	):
	# Purpose: to alter select, order, and where such that we are selecting
	#	results based partly on the specified object attribute (name)
	# Returns: nothing
	# Assumes: fieldname is of the form "X.Y" where X is the two-letter
	#	abbreviation of a table name and Y is the fieldname within it.
	# Effects: Alters where if we need to select the query results based on
	#	the specified object attribute (a date) (appends strings of
	#	clauses suitable for inclusion in the "where" and "select" parts
	#	of a SQL select statement).  Alters order if we need to sort by
	#	the specified object attribute (builds a clause which is
	#	suitable for inclusion in the "order by" part of a SQL select
	#	statement.
	# Throws: nothing

	# if we need to display this one, then convert it to a string and
	# use the same fieldname (though without the leading table abbreviation)

	if name in to_display:
		select.append ('convert (varchar, %s, 100) %s' % \
			(fieldname, fieldname [3:]))

	# now, if this date field was specified in the dictionary of inputs
	# from the user, then we know we need to add clauses to where for it.
	# since it has been validated, we know that we have a starting datetime
	# followed by '..' followed by a stopping datetime.

	if name in clean_keys:
		brk = string.find (clean_dict [name],	# find separator
			'..')
		start = clean_dict [name][:brk]		# all before separator 
		stop = clean_dict [name][(brk + 2):]	# all after separator

		# then, if there is a date defined for start and/or stop,
		# add the clauses to "where" which ensure the field
		# value is after the start date and before the stop date

		if start <> '':
			where.append ('%s >= "%s"' % (fieldname, start))
		if stop <> '':
			where.append ('%s <= "%s"' % (fieldname, stop))

	# there are up to three levels of sorting.  Go through each, and see if
	# it is based on the specified object attribute.  If so, set the
	# corresponding item in order to be the name of the field (without the
	# leading table abbreviation) and the 'asc' or 'desc' designation.

	for i in [ 0, 1, 2 ]:
		if sorting [i] == name:
			select.append (fieldname + ' ' + sort_fieldname)
			order [i] = sort_fieldname + ' ' + ordering [i]
	return

def consider_single_valued_cv (
	name,		# name of the single-valued controlled vocabulary field
			# (in object attribute (user-readable) form) to examine
	main_fieldname,	# name of the corresponding field in the main tracking
			# record table, including a 2-letter abbreviation for
			# the table name
	table_abbrev,	# string containing the table name and 3-letter
			# abbreviation containing the controlled vocabulary.
	cv_fieldname,	# name of the corresponding field in the controlled
			# vocabulary table, including the 3-letter abbreviation
			# for the controlled vocabulary table name
	order_fieldname,# name of the fieldname to be used in ordering the
			# controlled vocabulary, including the 3-letter
			# abbreviation for the controlled vocabulary table.
	to_display,	# list of names of object attributes to display
	select,		# list of fieldnames to select from the database
	clean_dict,	# validated dictionary of fieldname -> desired value
			# pairs to use in generating and running queries.
	clean_keys,	# list of keys in clean_dict
	where,		# list of string clauses for the "where" part of a
			# SQL select statement.
	joins,		# list of string clauses which are used to join tables
			# in the "where" part of a SQL select statement
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	order,		# three-item list containing string clauses on how to
			# sort the results.  (for the "order by" part of a
			# SQL select statement)
	ordering,	# three-item tuple containing a string identifying how
			# each level of sorting should be conducted:
			# ('asc' = ascending order, 'desc' = descending order)
	frm		# list of table names from which to select values
	):
	# Purpose: to alter "select", "order", "frm", "where", and "joins" such
	#	that we are selecting results based partly on the specified
	#	object fieldname ("name")
	# Returns: nothing
	# Assumes: parameters are formatted as described above
	# Effects: Alters "where", "select", and "joins" if we need to select
	#	the query results based on the specified object fieldname (a
	#	single-valued controlled vocabulary field) (appends strings of
	#	clauses suitable for inclusion in the "where" and "select" parts
	#	of a SQL select statement).  Alters "order" if we need to sort
	#	by the specified object fieldname (builds a clause which is
	#	suitable for inclusion in the "order by" part of a SQL select
	#	statement.
	# Throws: nothing

	if name in to_display:			# if we need to show this field,
		select.append (main_fieldname)	# then we need to retrieve it
						# in the select statement.

	# if the user specified a restriction for this field it will be in the
	# list of keys for the clean_dict.  In this case, we need to add the
	# list of chosen controlled vocabulary keys to the where part of the
	# SQL statement.

	if name in clean_keys:

		# if at least one "Not" box was checked and one of them was for
		# this controlled vocab field, we need to look for those that
		# were not selected...

		if ("Not" in clean_keys) and \
			string.find (clean_dict ["Not"], name) != -1:
			where.append ('%s not in %s' % (main_fieldname,
				clean_dict [name]))
		else:

		# otherwise, look for those that were selected...

			where.append ('%s in %s' % (main_fieldname,
				clean_dict [name] ))

	# there are up to three levels of sorting.  Go through each, and see if
	# it is based on the specified object attribute.  If so, set the
	# corresponding item in order to be the name of the field (without the
	# leading table abbreviation) and the 'asc' or 'desc' designation.

	for i in [ 0, 1, 2 ]:
		if sorting [i] == name:
			frm.append (table_abbrev)
			select.append (order_fieldname)
			joins.append ('%s = %s' % (main_fieldname,
				cv_fieldname))
			order [i] = order_fieldname [4:] + ' ' + ordering [i]
	return

def consider_multi_valued_cv (
	name,		# name of the multi-valued controlled vocabulary field
			# (in object attribute (user-readable) form) to examine
	mm_tablename,	# name of the table containing the many-to-many 
			# relationship data for this tracking record field
	table_abbrev,	# two-letter abbreviation for mm_tablename
	fieldname,	# name of the field in the table referred to by
			# mm_tablename which corresponds to the controlled
			# vocabulary
	to_display,	# list of names of object attributes to display
	clean_dict,	# validated dictionary of fieldname -> desired value
			# pairs to use in generating and running queries.
	clean_keys,	# list of keys in clean_dict
	where,		# list of string clauses for the "where" part of a
			# SQL select statement.
	joins,		# list of string clauses which are used to join tables
			# in the "where" part of a SQL select statement
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	frm		# list of tables and their abbreviations used in the
			# query (essentially the contents of the "from" section
			# of a SQL select statement)
	):
	# Purpose: to alter the "where" list of clauses to ensure that any
	#	tables needed for the many-to-many controlled vocabulary
	#	fields are included, and alter the "joins" list to ensure that
	#	they have been joined.  also to determine whether sorting may be
	#	done in the database and whether we need to display any of
	#	these multi-valued fields.
	#	results based partly on the specified object attribute (name)
	# Returns: a tuple of booleans (0/1) which has two items:
	#	(need to sort this field, need to display this field)
	# Assumes: parameters are formatted as described above
	# Effects: Alters "where" and "joins" if we need to select the query
	#	results based on the specified object attribute (a multi-valued
	#	controlled vocabulary field) (appends strings of clauses
	#	suitable for inclusion in the "where" part of a SQL select
	#	statement).  Determines if this field is okay to sort in the
	#	database and whether it needs to be displayed.
	# Throws: nothing
					# assume:
	need_to_sort = 0		# we don't need to sort by this field
	need_to_display = 0		# we don't need to display this field

	# if the user specified a restriction for this field it will be in the
	# list of keys for the clean_dict.  In this case, we need to add the
	# list of chosen controlled vocabulary keys to the "where" part of the
	# SQL statement.

	if name in clean_keys:
		frm.append ('%s %s' % (mm_tablename, table_abbrev))
		joins.append ('tr._TR_key = %s._TR_key' % table_abbrev)

		# if at least one "Not" box was checked and one of them was for
		# this controlled vocab field, we need to look for those that
		# were not selected...

		if ("Not" in clean_keys) and \
			string.find (clean_dict ["Not"], name) != -1:
			where.append ('%s.%s not in %s' % (table_abbrev,
				fieldname, clean_dict [name]))
		else:

		# otherwise, look for those that were selected...

			where.append ('%s.%s in %s' % (table_abbrev, fieldname,
				clean_dict [name] ))


	if name in to_display:
		need_to_display = 1	# we do need to display this field
	if name in sorting:
		need_to_sort = 1	# we do need to sort this field

	return (need_to_sort, need_to_display)



def consider_dependencies (
	temp_table,	# name of the temporary table into which to put tracking
			# record information.
	select,		# list of fields to select and add to temp_table
	frm,		# list of table names to select values from
	joins,		# list of string clauses which are used to join tables
			# in the "where" part of a SQL select statement
	x_depends_on,	# boolean (0/1) - true if we should include tracking
			# records depended on by those already in temp_table.
	depends_on_x	# boolean (0/1) - true if we should include tracking
			# records which depend on thsoe already in temp_table.
			#	'X Depends On' in clean_keys,	# 0/1
			#	'Depends On X' in clean_keys)	# 0/1
	):
	# Purpose: to build and return SQL statements which add information to
	#	temp_table for tracking records related (via dependency) to
	#	those already in temp_table, if so requested.
	# Returns: a list of strings (possibly an empty list), each of which is
	#	a SQL statement needed to add the appropriate information to
	#	temp_table
	# Assumes: that the relationship_type field in WTS_Relationship should
	#	be DEPENDS_ON to indicate a "depends on" type relationship.
	# Effects: Generates and returns a list of SQL statements which will
	#	add information to temp_table according to the settings of
	#	x_depends_on and depends_on_x.  (see parameter comments above)
	# Throws: nothing

	dependency_queries = []		# start with no queries for dependency-
					# related information

	if not (x_depends_on or depends_on_x):	# if we don't need to add any
		return dependency_queries	# dependency-related info, then
						# just bail out.

	# let's generate a couple more names for temporary tables, to help
	# handle any dependency information.  We just arbitrarily put a 1 or 2
	# into the string to make it a unique name.  (Previously, I had tried
	# adding a 1 or 2 at the end, but the names were not considered unique.
	# I suspect that sybase only compares the first X characters.)

	temp_table_1 = temp_table [0:4] + '1' + temp_table [4:]
	temp_table_2 = temp_table [0:4] + '2' + temp_table [4:]

	# those depended on by X...  (put them in temp_table_1 to avoid any
	# interference they might cause if both boxes are checked)

	if x_depends_on:

		# we need to add the basic tracking record information for all
		# those depended on by ones already in temp_table (including
		# the full transitive closure).

		dep_qry_1 = '''
			select rel._Related_TR_key _TR_key, %s
			into %s
			from WTS_Relationship rel, %s
			where ((rel._Related_TR_key = tr._TR_key) and
				(rel.transitive_closure = 1) and
				(rel.relationship_type = %d) and
				(rel._TR_key in (select _TR_key from %s)))''' \
			% (wtslib.list_To_String (remove(select, 'tr._TR_key')),
				temp_table_1, wtslib.list_To_String (frm),
				DEPENDS_ON, temp_table)

		# if we need to link any of the tables in "frm", do so:

		if len (joins) > 0:
			for clause in joins:
				dep_qry_1 = dep_qry_1 + ' and (%s)' % clause

		dependency_queries.append (dep_qry_1)

		# now move all those entries from temp_table_1 to temp_table,
		# and drop temp_table_1

		dependency_queries.append ('insert %s select * from %s' % \
			(temp_table, temp_table_1))
		dependency_queries.append ('drop table %s' % temp_table_1)

	# those depending on X...  (put them in temp_table_2 to avoid any
	# interference they might cause if both boxes are checked)

	if depends_on_x:

		# we need to add the basic tracking record information for all
		# those which depend on ones already in temp_table (including
		# the full transitive closure).

		dep_qry_2 = '''
			select rel._TR_key, %s
			into %s
			from WTS_Relationship rel, %s
			where ((rel._TR_key = tr._TR_key) and
				(rel.transitive_closure = 1) and
				(rel.relationship_type = %d) and
				(rel._Related_TR_key in
					(select _TR_key from %s)))''' % \
			(wtslib.list_To_String (remove (select, 'tr._TR_key')),
			temp_table_2, wtslib.list_To_String (frm), DEPENDS_ON,
			temp_table)

		# if we need to link any of the tables in "frm", do so:

		if len (joins) > 0:
			for clause in joins:
				dep_qry_2 = dep_qry_2 + ' and (%s)' % clause

		dependency_queries.append (dep_qry_2)

		# move the entries from temp_table_2 to the main temp_table,
		# and drop temp_table_2

		dependency_queries.append ('insert %s select * from %s' % \
			(temp_table, temp_table_2))
		dependency_queries.append ('drop table %s' % temp_table_2)

	return dependency_queries

def lookup_multi_valued_cv (
	temp_table,	# name of the temporary table into which we put tracking
			# record information.
	multi_cv,	# defined above in build_And_Run_SQL - a list of tuples
			# with info about multi-valued controlled vocabulary
			# fields: name, mm_table, abbrev, fieldname
	to_display,	# list of names of object attributes to display
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	queries,	# list of strings, each of which is a SQL statement
			# used in querying tracking records.
	queried_cv	# defined above in build_And_Run_SQL - a dictionary
			# which maps controlled vocabulary names to the index
			# (into queries) of the query used to retrieve its
			# information.
	):
	# Purpose: to generate queries which look up the values for the
	#	multi-valued controlled vocabulary fields of the tracking
	#	records in temp_table.
	# Returns: nothing
	# Assumes: nothing
	# Effects: goes through the list of fields to_display and those listed
	#	in sorting to determine which multi-valued controlled
	#	vocabulary fields we need to load.  It then adds the necessary
	#	SQL statements to queries, and updates queried_cv so that each
	#	controlled vocabulary name is a key which refers to the index
	#	(into queries) of the statement used to retrieve the values.
	# Throws: nothing

	# step through all possible multi-valued controlled vocabulary fields
	# and generate queries to look up the values for those we need to
	# either display or sort by:

	for (name, mm_table, abbrev, fieldname) in multi_cv:
		if (name in to_display) or (name in sorting):

				# remember which query number is used for this
				# c.v., then generate the query to get this
				# field's information for all tracking records
				# in the temp_table

				queried_cv [name] = len (queries)
				queries.append ('''
					select _TR_key, %s
					from %s
					where _TR_key in (select _TR_key
						from %s)''' % \
					(fieldname, mm_table, temp_table))
	return

def compile_multi_valued_cv (
	track_recs,	# dictionary of dictionaries, each of which contains
			# the basic data for one tracking record.
	tr_numbers,	# list of tracking record numbers in track_recs
	queried_cv,	# dictionary where multi-valued controlled vocabulary
			# field names are mapped to an integer which is the
			# index into results where we may find the corresponding
			# information.
	results		# list of lists of dictionaries - see build_And_Run_SQL
			# for a more complete explanation.
	):
	# Purpose: to add information retrieved for the various multi-valued
	#	controlled vocabulary fields to the tracking record data in
	#	track_recs.
	# Returns: nothing
	# Assumes: nothing
	# Effects: uses queried_cv to find out what multi-valued controlled
	#	vocabulary fields we retrieved and where in results they are
	#	located.  We then compile the information and add it to the
	#	tracking record data in track_recs
	# Throws: nothing

	global NAME_TO_DB

	# set up a dictionary of useful information for the four multi-valued
	# controlled vocabularies.  Format:
	#	vocab name --> (key name, dictionary of key --> text name,
	#			text value field name, ordering field name)

	CV = Controlled_Vocab.cv	# get a quick reference to the
					# controlled vocabulary info that is
					# already loaded in the
					# Controlled_Vocab module
	cv_info = {
		'Area' : ('_Area_key', CV ['CV_WTS_Area'].key_dict (),
			'area_name', 'area_order'),
		'Type' : ('_Type_key', CV ['CV_WTS_Type'].key_dict (),
			'type_name', 'type_order'),
		'Staff' : ('_Staff_key', CV ['CV_Staff'].key_dict (),
			'staff_username', 'staff_username'),
		'Requested By' : ('_Staff_key', CV ['CV_Staff'].key_dict (),
			'staff_username', 'staff_username')
		}

	queried_cv_keys = queried_cv.keys ()	# list of names of queried
						# multi-valued controlled
						# vocabulary fields

	# We need to collect the name values for each cv into a list, and put
	# the list in the proper tracking record entry

	# step through the names of the fields we looked up

	for key in queried_cv_keys:
		db_key = NAME_TO_DB [key]	# the keys in each tracking
						# record's dictionary are in
						# their database fieldname form,
						# so convert the object
						# attribute name to that form.

		# go to the set of results for this particular multi-valued
		# controlled vocabulary field, and step through each row
		# (dictionary) contained therein.

		for row in results [queried_cv [key]]:

			# if we have already begun a list for this field...

                        if track_recs [row ['_TR_key']].has_key (db_key):

				# then just append the new value to it

				track_recs [row ['_TR_key']][db_key].append ( \
					cv_info[key][1][row [cv_info [key][0]]])
                        else:
				# begin a new list of values for this field

				track_recs [row ['_TR_key']][db_key] = [ \
					cv_info [key][1][row [cv_info \
					[key][0]]] ]

		# We have now finished compiling all the information.  Now we
		# need to go through each tracking record and alphabetically
		# sort the values for each multi-valued controlled vocabulary
		# field and convert the list to a string.

		for tr in tr_numbers:
                        if track_recs [tr].has_key (db_key):
				track_recs [tr][db_key].sort ()
                        else:

				# this tracking record had no entries for
				# this multi-valued controlled vocabulary field

				track_recs [tr][db_key] = []	# no data

			# now, convert the list of CV values to a string

			track_recs [tr][db_key] = wtslib.list_To_String ( \
				track_recs [tr][db_key] )
	return

def compile_single_valued_cv (
	track_recs,	# dictionary of dictionaries, each of which contains
			# the basic data for one tracking record.
	tr_numbers	# list of tracking record numbers in track_recs
	):
	# Purpose: to convert the keys stored in the single-valued controlled
	#	vocabulary fields in the tracking record to their text
	#	equivalents
	# Returns: nothing
	# Assumes: nothing
	# Effects: steps through each tracking record in track_recs, looks for
	#	single-value controlled vocabulary fields, and then replaces
	#	the key values with the text equivalents.
	# Throws: nothing

	CV = Controlled_Vocab.cv	# get a quick reference to the
					# controlled vocabulary info that is
					# already loaded in the
					# Controlled_Vocab module

	# set up a list of useful information for the 3 single-valued
	# controlled vocabularies.  Format:
	#	each tuple --> (name of text field, dictionary of key --> text
	#			name, name of key field)

	cv = [	('size_name', CV ['CV_WTS_Size'].key_dict (),
			'_Size_key'),
		('status_name', CV ['CV_WTS_Status'].key_dict (),
			'_Status_key'), \
		('priority_name', CV ['CV_WTS_Priority'].key_dict (),
			'_Priority_key') ]

	# step through all the tracking records...

	for tr in tr_numbers:
		tr_keys = track_recs [tr].keys ()	# list of the defined
							# fieldnames for this
							# tracking record

		# go through the 3 controlled vocabulary fields

		for (fieldname, values, key_fieldname) in cv:

			# if this tracking record has a value defined for that
			# field's key_fieldname, then add a new field with the
			# corresponding fieldname and the text value that
			# matches the key

			if (key_fieldname in tr_keys):
				track_recs [tr][fieldname] = \
					values [track_recs [tr][key_fieldname]]
	return

def sort_results (
	track_recs,	# dictionary of dictionaries, each of which contains
			# the basic data for one tracking record.
	tr_numbers,	# list of tracking record numbers in track_recs
	sorting,	# tuple containing three strings, each the name of a
			# field to use in sorting the results.
	ordering	# three-item tuple containing a string identifying how
			# each level of sorting should be conducted:
			# ('asc' = ascending order, 'desc' = descending order)
	):
	# Purpose: to take the tracking records in the track_recs dictionary
	#	and return them in a list, according to the "sorting" and
	#	"ordering".
	# Returns: list of dictionaries, each of which is the data for a
	#	tracking record, in proper sorted order
	# Assumes: nothing
	# Effects: see Purpose.
	# Throws: nothing

	global NAME_TO_DB

	# list_to_sort is a list of tuples that we build to be sorted
	# by python.  Each tuple is for one tracking record, and
	# contains:
	#	 ( [sort values], { tracking record info } )

	list_to_sort = []
	for tr in tr_numbers:

		# for each tracking record, we need to build a tuple with its
		# "sort values".  These are the values for each field specified
		# as a sort field on the query form. 

		sort_values = []	# up to three values to be used in
					# sorting the results.
		for i in [ 0, 1, 2 ]:		# <= 3 sort levels

			# if there is a defined field for this sorting level,
			# then use it.  Note that we test for a text 'None',
			# since that is how it is passed in from the query form
			# if we don't need that level of sorting.

			if sorting [i] <> 'None':

				# get the actual value of this field

				value = track_recs [tr][NAME_TO_DB[sorting [i]]]

				# now, since we're sorting by this field, we
				# need to handle single-valued controlled
				# vocabularies differently.  (They need to be
				# sorted as specified in their *_order field.)

				if sorting [i] in ['Priority','Status','Size']:
					name = 'CV_WTS_%s' % sorting[i]
					vocab_values = Controlled_Vocab.cv \
						[name].pickList (showAll = 1)
					value = vocab_values.index (value)

				# if we're looking at this field for ascending
				# order, then just use the actual value in
				# sorting the results.

				if ordering [i] == 'asc':
					sort_values.append (value)
				else:

				# otherwise, we need to sort this field in
				# descending order.  use the opposite function
				# (defined in this module) to get the 'opposite'
				# value, which will sort in reverse order.

					sort_values.append (opposite (value))

		# now, add the above-described tuple to the list of items to
		# be sorted.

		list_to_sort.append ((sort_values, track_recs [tr]))

	# python will sort based on the first item of each list element.  These
	# items are the sort_values that we defined for each list element.
	# Hence, we have correct sorting.

	list_to_sort.sort ()

	# then, put the actual tracking record data, in order, into the list
	# for final_results.

	final_results = []		# ensure we start with an empty list

	for (sort_values, track_rec_data) in list_to_sort:
		final_results.append (track_rec_data)

	return final_results

# --- end of helper functions for build_And_Run_SQL --- #


def build_Query_Table (
	clean_results	# a list of dictionaries, each of which represents a
			# single tracking record, as from build_And_Run_SQL.
	):
	# Purpose: build an HTML table of query results (for the Query Results
	#	Screen) from the given clean_results (generated by
	#	build_And_Run_SQL with input from the Query Screen)
	# Returns: a list of HTMLgen objects which represents the clean_results
	#	in an HTML table
	# Assumes: clean_results is valid and came directly from
	#	build_And_Run_SQL
	# Effects: uses the HTMLgen package to build a table showing the data
	#	in clean results, with checkboxes in the leftmost column
	#	(labeled 'Display').  The order of columns is defined in the
	#	code below, and the TR # value for each row (tracking record)
	#	is clickable to go to a detail screen for that tracking record.
	# Throws: nothing
	# Notes: The HTMLgen objects in the list returned should be appended to
	#	an HTMLgen-compliant form object.

	global HELP_URL

	# take note of the date fields, which will need to be converted to the
	# standard WTS format before output

	date_fields = [ 'Needs Attention By', 'Modification Date', \
		'Status Date' ]

	# for now, we define the ordering of the columns.  In the future, we
	# may choose to let the user define this in some way.

	column_order = [ 'TR Nr', 'Title', 'Area', 'Type', \
		'Needs Attention By', 'Priority', 'Requested By', 'Status', \
		'Status Date', 'Size', 'Staff', 'Directory', \
		'Modification Date' ]

	# now, get an ordered list of the columns we actually have

        if len (clean_results) > 0:
		column_set = clean_results [0].keys ()
        else:
		column_set = []
	columns = []			# the ordered list of columns
	for col in column_order:
		if col in column_set:
			columns.append (col)

	# define the table, and add a header row with the first box 'Display'

	tbl = HTMLgen.TableLite (align = 'center', border = 1, cellpadding = 5)

	row = HTMLgen.TR (HTMLgen.TH (HTMLgen.Href (HELP_URL % 'Display', \
		'Display')))

	# add the remaining column headers, each linked to its help file...

	for col in columns:
		row.append (HTMLgen.TH (HTMLgen.Href (HELP_URL % col, col)))
	tbl.append (row)

	# now, add one row for each tracking record in the clean results

	for tr in clean_results:

		# left column in each row is a checkbox for Display

		row = HTMLgen.TR (HTMLgen.TD (HTMLgen.Input (type='checkbox', \
			name='TR_Nr', value=tr ['TR Nr'])))
		for col in columns:

			# if this is a TR#, we need to link it to the detail
			# display for the tracking record

			if col == 'TR Nr':
				row.append (HTMLgen.TD (HTMLgen.Href ( \
					'tr.detail.cgi?TR_Nr=' + \
					str (tr [col]), tr [col]) ))
			else:
				out_value = ''
				if col not in date_fields:
					out_value = tr [col]
				else:
					# this is a date value, so make sure it
					# is properly formatted.  Since it came
					# from the database, the only errors
					# which could occur arise from a null
					# value -- we can screen these out
					# beforehand.  (null values are okay
					# for some date fields)

					if tr [col] is not None:
						out_value, ignore_errors = \
							wtslib.parse_DateTime \
							(tr [col])

				if out_value == '':
					# this field is empty, so just
					# send out a '-' character
					out_value = '-'

				row.append (HTMLgen.TD (HTMLgen.RawText (
					str (out_value))))
		tbl.append (row)

	return [ tbl ]


def parse_And_Merge (
	results,	# list of dictionaries, each of which is a row returned
			# by a SQL statement (as from db.sql using the
			# 'auto' mechanism).
	key_name	# name of the key in the dictionaries in results which
			# is considered a unique identifier for individual
			# conceptual records in "results"
	):
	# Purpose:if a schema has many-to-many relationships, then it is
	#	possible (and probable) that a query will return more than one
	#	row per "conceptual record".  This function goes through
	#	results and combines rows for the same conceptual record by
	#	concatenating different values for each field.  The resulting
	#	list of rows then has only one row per conceptual record. 
	#	Fields which need to store multiple values will contain a
	#	string with a comma-separated set of values.
	# Returns: a list of dictionaries, with one dictionary per unique value
	#	in the field specified by key_name.
	# Assumes: The value specified in key_name is a key of each dictionary
	#	in results.
	# Effects: Accept a list of rows (dictionaries) returned by a SQL query
	#	and return a collapsed list with only one row (dictionary) per
	#	unique value in the field specified by key_name.  If fields in
	#	different rows for the same key_value have different values,
	#	join them in a (string) comma-separated list.  Ignore values
	#	found that are the same.
	# Throws: 1. IndexError if key_name is not a key of one of the
	#	dictionaries in results.
	# Example:
	#    parse_And_Merge ([ {'_TR_key' : 2, 'area_name' : 'web' },
	#		{ '_TR_key' : 2, 'area_name' : 'unknown' },
	#		{ '_TR_key' : 3, 'area_name' : 'unknown' }], '_TR_key')
	#    returns:
	#	[ { '_TR_key' : 2, 'area_name' : 'web, unknown' },
	#	  { '_TR_key' : 3, 'area_name' : 'unknown' } ]

	# work with a dictionary of dictionaries.  key -> row (conceptual
	# record, which is itself a dictionary of fieldname -> value)

	dict = {}

	# now, go through each row in results and add info to dict

	key_list = []			# ordered list of unique keys
	for row in results:
		key = row [key_name]

		# get an alias to the unified record for this row's key

                if dict.has_key (key):
			unified = dict [key]		# found one
                else:

			# this is the first row for this key, so we need
			# to make a new unified record

			dict [key] = {}
			unified = dict [key]

			# and, add this new one to our list of keys

			key_list.append (key)

		# now go through each field in this row, and see if we need
		# to add its value to the unified record.

		unified_keys = unified.keys ()	# keys currently in the unified
						# record...
		for k in row.keys ():
			if k not in unified_keys:
				unified [k] = row [k]	# define new key & value
			elif unified [k] == None:
				unified [k] = row [k]	# define new key & value
			elif unified [k] == row [k]:
				pass		# we already found this value
			elif type (unified [k]) == types.ListType:

				if row [k] not in unified [k]:

					# add to an existing list of values

					unified [k].append (row [k])
			else:
				# create a new list of values, since this is
				# the second possible value we've found.  use
				# a list rather than a string to facilitate
				# searching for inclusion of new values later
				# on.  (with a string, we'd have to deal with
				# nasty stuff like keywords within other
				# keywords & such)

				unified [k] = [ unified [k], row[k] ]
			
	# convert the unified dictionary to a list of rows, in order by the
	# original keys' ordering

	list = []
	for key in key_list:

		# build a new dictionary for this row only (since we now need
		# to convert list data elements to comma-separated values in
		# strings

		new_dict = {}
		for k in dict[key].keys():

			# if we're dealing with a list in this field, then
			# convert it to a string in new_dict

			if type (dict [key][k]) == types.ListType:
				s = ''
				for item in dict [key][k]:
					if (s <> ''):	
						s = s + ', '
					s = s + str (item)
				new_dict [k] = s
			else:
				# if it's not a string, then just copy it as-is

				new_dict [k] = dict [key][k]

		list.append (new_dict)
	return list


def validate_Query_Form (
	raw_dict	# a dictionary of (user-format) fieldname --> field
			# value pairs from a query form.
	):
	# Purpose: To verify that values entered on a query form are valid.
	# Returns: a cleaned-up dictionary of query "restrictions", with key
	#	values being fieldnames in the user-readable format.
	# Assumes: keys of raw_dict are in the user-readable format.  And,
	#	Controlled vocabularies are contained in a dictionary at
	#	Controlled_Vocab.cv, where that dictionary is keyed by table
	#	name to yield a particular Controlled_Vocab object.
	# Effects: Date field values are converted to the standard WTS format.
	#	Multi-valued controlled vocabulary fields are standardized to
	#	use a string of values separated by a comma and a space.
	#	Removes the 'any' selection from controlled vocabulary fields,
	#	as it does not provide any selection restrictions.  All
	#	controlled vocabulary fields values are converted to their key
	#	values rather than names, and are returned as a string with
	#	parenthesis around the key values.  Breaks down tracking
	#	record number ranges into a series of clauses using relational
	#	operators where possible.  Swaps secondary and tertiary ordering
	#	information if secondary is None and tertiary is not.  Converts
	#	fieldnames with underscores to their equivalent fieldnames with
	#	spaces to allow for GET submissions.  Doubles any double quotes
	#	in the Title and Text Fields fields.
	# Throws: 1. TrackRec.error when any validation errors are found.
	# Example: 
	#	validate_Query_Form ( { 'TR Nr' : '1, 3-6, 10-',
	#		'Size' : 'small, medium',
	#		'Modification Date' : 'January 2, 1998..June 1, 1999' }
	#	results in:
	#		{ 'TR Nr' : '(_TR_Nr in (1)) or ((_TR_Nr >= 3) and
	#			(_TR_Nr <= 6)) or (_TR_Nr >= 10)',
	#		'Size' : '2, 3',
	#		'Modification Date' : '01-02-1998..06-01-1999' }

	global error_separator

	CV = Controlled_Vocab.cv	# quick reference to CV info
	errors = []			# no errors so far

	# define a dictionary which maps from names with underscores to
	# names with spaces.  This is to allow for GET submissions, which
	# don't allow spaces in the URL.

	Query_Name_Mapping = {
		'TR'		:	'TR Nr',
		'TR_Nr'		:	'TR Nr',
		'Status_Date'	:	'Status Date',
		'Needs_Attention_By' :	'Needs Attention By',
		'Requested_By'	:	'Requested By',
		'Modification_Date' :	'Modification Date' }

	# make a copy ("raw") of the input dictionary to work with, and
	# convert its keys using "Query_Name_Mapping"

	raw = copy.deepcopy (raw_dict)
	for k in raw.keys ():
		if Query_Name_Mapping.has_key (k):
			raw [Query_Name_Mapping [k]] = copy.deepcopy (raw [k])
			del raw [k]

	# convert the fieldnames embedded in the Displays field using the
	# "Query_Name_Mapping".  Also strip out spaces.

	if raw.has_key ("Displays"):
		fields = []

		# POST submissions come here separated by comma-space, and GET
		# submissions come separated only by commas.  So first, convert:

		stripped = regsub.gsub (', ', ',', raw ['Displays'])

		for field in wtslib.string_To_List (stripped, ','):
			if Query_Name_Mapping.has_key (field):
				fields.append (Query_Name_Mapping [field])
			else:
				fields.append (field)
		raw ["Displays"] = wtslib.list_To_String (fields, ',')

	# note the controlled vocabulary fields and tables:

	controlled_vocabs = [ ('Priority', 'CV_WTS_Priority'), \
		('Size', 'CV_WTS_Size'), ('Status', 'CV_WTS_Status'), \
		('Area', 'CV_WTS_Area'), ('Type', 'CV_WTS_Type'), \
		('Staff', 'CV_Staff'),
		('Requested By', 'CV_Staff'), ('Requested_By', 'CV_Staff'),
		('Status Staff', 'CV_Staff') ]

	# go through each controlled vocabulary and clean it up

	SEP = ', '			# standard separator
	for item in controlled_vocabs:
		clean_string = ''
		this_cv = CV [item[1]]

                if raw.has_key (item [0]):

			# strip spaces and split on commas

			values = string.split (string.translate ( \
				raw [item[0]], \
				string.maketrans ('',''), ' '), ',')
                else:
			values = []	# was not filled in, so ignore it

		for key in values:
			# since we may receive "any" or a divider line
			# ('-----') as one of the "values", we need to be sure
			# to query only with the valid CV items

			if this_cv[key] is not None:
				if clean_string == '':
					clean_string = str (this_cv [key])
				else:
					clean_string = clean_string + SEP + \
						str (this_cv [key])

		# if the clean_string is empty, then remove it from raw

		if clean_string == '':
                        if raw.has_key (item [0]):        # if it is in raw...
                                del raw [item[0]]       # delete it
		else:
			raw [item [0]] = '(' + clean_string + ')'

	# check (and clean up) the date fields

	date_fields = [ 'Status Date', 'Needs Attention By', \
		'Modification Date', 'Status_Date', 'Needs_Attention_By', \
		'Modification_Date' ]
	for item in date_fields:
		if raw.has_key (item):
			(start, stop, err) = wtslib.parse_DateRange (raw [item])
			if err == None:
				# store cleaned-up datetime range

				raw [item] = start + '..' + stop
			else:
				# store the errors found

				for e in err:
					errors.append (item + ':  ' + e)

	# handle the secondary and tertiary sort orderings.  if secondary is
	# none and tertiary is defined, then swap them.

        if raw.has_key ('Secondary') and raw.has_key ('Tertiary'):
		if (raw ['Secondary'] == 'None') and \
			(raw ['Tertiary'] <> 'None'):

                        raw ['Secondary'] = raw ['Tertiary']
                        raw ['Tertiary'] = 'None'

                        temp = raw ['Secondary Order']
                        raw ['Secondary Order'] = raw ['Tertiary Order']
                        raw ['Tertiary Order'] = temp

	# now, if the TR # field is defined, clean it up by generating a set
	# of clauses which handle ranges with relational operators and combine
	# explicitly specified values in a single 'in' check.

	try:
		if raw.has_key ('TR Nr'):
			raw ['TR Nr'] = expand_TR (raw ['TR Nr'], 'tr._TR_key')
	except:
		errors.append ('TR Nr: Cannot parse "' + str (raw ['TR Nr']) + \
			'"')

	# go through the Title and Text fields to ensure that any quotes are
	# doubled (for generating the proper query later on...)

	for field in [ 'Title', 'Text Fields' ]:
		if raw.has_key (field) and \
				(type(raw[field]) == types.StringType):
			raw[field] = wtslib.duplicated_DoubleQuotes (raw[field])

	# now, either bail out by raising an exception (if there were errors),
	# or return the cleaned up dictionary of values (in raw)

	if len (errors) > 0:
		raise error, wtslib.list_To_String (errors, error_separator)
	else:
		return raw


def validate_TrackRec_Entry (
	raw_dict	# a dictionary of (user-format) fieldname --> field
			# value pairs which is the complete information for a
			# single tracking record
	):
	# Purpose: validates and cleans up the values entered for a tracking
	#	record (from the Edit or New screen, or from the command-line
	#	interface).
	# Returns: a cleaned-up dictionary with (user-format) fieldnames and
	#	validated values
	# Assumes: Controlled vocabularies are contained in a dictionary at
	#	Controlled_Vocab.cv, where that dictionary is keyed by table
	#	name to yield a particular Controlled_Vocab object.
	# Effects: Checks the values in raw_dict to see that all required
	#	fields have values, that controlled vocabulary fields use valid
	#	vocabulary items, and that date fields have recognizable values.
	#	Cleans up the date fields to use the standard WTS format.
	#	Cleans up multi-valued controlled vocabulary fields be a string
	#	and to use a comma-space separator between values.  Also removes
	#	the "unknown" value from multi-valued controlled vocabulary
	#	fields if another value is also selected.  Converts the "Depends
	#	On" field to be a set of integer keys.  Cleans up the large text
	#	fields to remove the extra "^M" submitted at the end of each
	#	line by the browser.  Wraps the value of each large text field
	#	in <PRE>..</PRE> if it does not contain any HTML markups.
	# Throws: 1. TrackRec.error if any validation errors occur.
	# Notes: The browser (Netscape, at least) submits a text area with each
	#	line ended by /015/012.  Typical line terminations in unix are
	#	only /012.  This was resulting in a "^M" displayed in the
	#	command line interface when editing a tracking record that was
	#	last saved by the web interface.  So, we just strip out the
	#	/015 characters from each line.

	global error_separator

	CV = Controlled_Vocab.cv	# quick reference to CV info
	errors = []			# no errors so far

	# make a copy of the input dictionary to work with...

	raw = copy.deepcopy (raw_dict)
	raw_keys = raw.keys ()

	# get lists of required attributes and all attributes

	tr = TrackRec ()			# create a temp tr
	req_attributes = tr.required_Attributes ()
	all_attributes = tr.all_Attributes ()
	del tr					# clean-up the temp tr

	# check to see that all required fields are present

	missing = None
	no_values = None
	for item in req_attributes:
		if item not in raw_keys:
                        if missing is not None:
				missing = missing + ', ' + item
                        else:
				missing = item
		elif raw [item] == None:
                        if no_values is not None:
				no_values = no_values + ', ' + item
                        else:
				no_values = item
	if missing:
		errors.append ('These required fields are missing: ' + \
			missing)
	if no_values:
		errors.append ( \
			'These required fields exist, but have no value: ' \
			+ no_values)

	# look for unrecognized field names

	bad_names = None
	for item in raw_keys:
		if item not in all_attributes:
                        if bad_names is not None:
				bad_names = bad_names + ', ' + item
                        else:
				bad_names = item
	if bad_names:
		errors.append ('Unrecognized field names: ' + bad_names)

	# note the controlled vocabulary fields and tables:  (each entry is
	# (field name, table name, 1-single value or 2-multi-valued)

	# (don't bother to check Status Staff, since it isn't filled in yet
	# for new tracking records)

	controlled_vocabs = [ ('Priority', 'CV_WTS_Priority', 1), \
		('Size', 'CV_WTS_Size', 1), ('Status', 'CV_WTS_Status', 1), \
		('Area', 'CV_WTS_Area', 2), ('Type', 'CV_WTS_Type', 2), \
		('Staff', 'CV_Staff', 2), ('Requested By', 'CV_Staff', 2) ]

	# go through each controlled vocabulary and clean it up

	SEP = ', '			# standard separator
	for item in controlled_vocabs:
		# get a list of values for this item

                if raw.has_key(item[0]) and (raw[item[0]] is not None):
			values = string.split (string.translate ( \
				raw [item[0]], \
				string.maketrans ('',''), ' '), ',')
                else:
			# Staff is an optional controlled vocabulary, so don't
                        # pester the user about that one.  Otherwise, remind
                        # the user that we need a value.

			if item[0] <> 'Staff':
				errors.append ('Could not find value for ' + \
					item[0])
			values = []

		clean_string = ''

		for key in values:
			if key[:4] == '----':
				pass		# skip selected divider lines

			elif CV[item[1]][key] == None:

				# the staff field may be blank.  if its value
				# is 'None', just ignore it.  (This could happen
				# when using the command-line interface.)  
				# Otherwise, we need to note the error.

				if not ((item[0] == 'Staff') and
					(key == 'None')):
					errors.append ( \
						'CV Error: could not find "' + \
						key + '" match for field "' + \
						item[0] + '"')
			elif (len (values) > 1) and (key == 'unknown'):

				# if we have multiple values and one is set for
				# 'unknown', we just ignore it, effectively
				# stripping it out.

				pass
			else:
				if clean_string == '':
					clean_string = key
				elif item[2] == 1:
					errors.append ('CV Error: found ' + \
						'multiple values for ' + \
						item[0] + ', a single-' + \
						'valued field.')
				else:
					clean_string = clean_string + SEP + key
		raw [item [0]] = clean_string

	# check (and clean up) the date fields

	date_fields = [ 'Status Date', 'Needs Attention By' ]
	for item in date_fields:
		# with new tracking records, it is possible for these fields to
		# not be filled in by the user.  If this is the case, disregard
		# it.
                if (item in raw_keys):
			date = raw [item]
			if date not in [ 'None', '' ]:
				(dt, err) = wtslib.parse_DateTime (date)
			else:
				dt = None
				err = None
			if err == None:
				# store cleaned-up datetime
				raw [item] = dt	
			else:
				# store the errors found
				for e in err:
					errors.append (item + ':  ' + e)
                else:
			pass

	# convert the "Depends On" field to be a Set of integer tracking record
	# keys.

	if raw.has_key ('Depends On') and \
			(type (raw ['Depends On']) == types.StringType):
		s = Set.Set ()
		string_keys = string.split (
			string.translate (raw ['Depends On'],
				string.maketrans ('',''), '()TRtr '), ',')
		for key in string_keys:
			if key != '':
				s.add (string.atoi (key))
		raw ['Depends On'] = s

	# if this is an existing node (has a TR number), then we need to
	# go through each dependency (dep) and look to see if there is a
	# transitive closure arc back to this node.  If so, that would create
	# a cycle, and we must disallow it:

	if raw.has_key ('TR Nr') and \
		(raw ['TR Nr'] is not None) and \
		(string.strip (str (raw ['TR Nr'])) != '') and \
		raw.has_key ('Depends On') and (not raw['Depends On'].empty ()):

		# be careful in case we have too many dependencies, that we
		# don't build a query that's too big.  Limit it to doing 100
		# at once.  (Hopefully there won't be any this big anyway...)

		cycles = []
		for sublist in wtslib.splitList (raw ['Depends On'].values (),
				100):
			sublist_cycles = wtslib.sql ('''
				select _TR_key, _Related_TR_key
				from WTS_Relationship
				where (_Related_TR_key = %s) and
					(relationship_type = %d) and
					(transitive_closure = 1) and
					(_TR_key in (%s))''' % \
				(raw ['TR Nr'], DEPENDS_ON,
					wtslib.list_To_String (sublist)))
			cycles = cycles + sublist_cycles
		if len (cycles) > 0:
			for row in cycles:
				errors.append ('Depends On: cannot have a ' + \
					'dependency on TR %d' % \
					row ['_TR_key'] + \
					' as it would create a cycle.')

	# Clean up the large text fields.  If they are non-empty and do not
	# contain any HTML tags, we should enclose the text in <PRE> and </PRE>
	# by default.  We should also strip out the extra "^M" sent by the
	# browser at the end of each line.

	text_fields = [ 'Project Definition', 'Progress Notes' ]
	for fieldname in text_fields:
		if raw.has_key (fieldname) and (raw [fieldname] is not None):

			# strip out the "^M" characters (/015) -- see Notes in
			# the function comments

			raw [fieldname] = regsub.gsub (chr (015), '',
				raw [fieldname])

			# if there are no HTML tags, then wrap the text in
			# <PRE> and </PRE>

			if not wtslib.isHTML (raw [fieldname]):
				raw [fieldname] = '<PRE>\n%s\n</PRE>' % \
					raw [fieldname]

	# now, either bail out by raising an exception (if there were errors),
	# or return the cleaned up dictionary of values (in raw)

	if len (errors) > 0:
		raise error, wtslib.list_To_String (errors, error_separator)
	else:
		return raw


def with_db_names (
	input_dict	# dictionary of tracking record data, with keys which
			# are object fieldnames
	):
	# Purpose: produce and return a dictionary parallel to "input_dict",
	#	which has the same values but with the keys converted to their
	#	equivalent database fieldname equivalents.
	# Returns: a dictionary with database fieldnames mapped to values (from
	#	input_dict)
	# Assumes: a proper mapping for each key in input_dict exists in
	#	the global NAME_TO_DB
	# Effects: returns a dictionary which has the user-readable object
	#	attribute names (from input_dict keys) mapped to the database
	#	fieldname equivalents, with the associated values from
	#	input_dict.
	# Throws: 1. KeyError if one of the keys in input_dict does not have
	#	a corresponding key in NAME_TO_DB.
	# Notes: see the top of this file for a discussion of the various
	#	field naming formats.

	global NAME_TO_DB

	dict = {}
	for key in input_dict.keys ():
		dict [ NAME_TO_DB [key] ] = input_dict [key]
	return dict


def with_nice_names (
	input_dict	# dictionary of tracking record data, with keys which
			# are database fieldnames
	):
	# Purpose: produce and return a dictionary parallel to "input_dict",
	#	which has the same values but with the keys converted to their
	#	equivalent object fieldname (formerly referred to as "nice"
	#	names) equivalents.
	# Returns: a dictionary with user-readable object attribute names
	#	mapped to values (from input_dict)
	# Assumes: a proper mapping for each key in input_dict exists in
	#	the global DB_TO_NAME
	# Effects: returns a dictionary which has the database fieldnames
	#	(from input_dict keys) mapped to the user-readable object
	#	attribute name equivalents, with the associated values from
	#	input_dict.
	# Throws: 1. KeyError if one of the keys in input_dict does not have
	#	a corresponding key in DB_TO_NAME.
	# Notes: see the top of this file for a discussion of the various
	#	field naming formats.

	global DB_TO_NAME

	dict = {}
	for key in input_dict.keys ():
		dict [ DB_TO_NAME [key] ] = input_dict [key]
	return dict


#-SUPPORTING FUNCTIONS FOR THE SAVE OPERATION-------------------------------

def save_WTS_TrackRec (
	values,		# dictionary of database fieldnames mapped to their
			# new values.
	method		# global TR_OLD (to save an existing tracking record)
			# or global TR_NEW (to save a new tracking record)
	):
	# Purpose: generate SQL statements needed to update the WTS_TrackRec
	#	table such that this tracking record will be saved there
	#	appropriately, based on the method.
	# Returns: a list of strings, each of which is a SQL statement to be
	#	executed in order for the values to save appropriately in
	#	WTS_TrackRec
	# Assumes: Parameter method will be TR_OLD or TR_NEW.  Controlled
	#	vocabulary objects are available from a dictionary at
	#	Controlled_Vocab.cv which is keyed by table name.
	# Effects: If method is TR_NEW then we generate a SQL insert statement
	#	to add the current contents of values to WTS_TrackRec.  If
	#	method is TR_OLD then we generate a SQL update statement to
	#	update this tracking record's current record in WTS_TrackRec.
	#	Return these SQL statements in a list of strings.
	# Throws: nothing
	# Notes: values may contain more data than is saved to WTS_TrackRec.
	#	In this function, we only extract the pieces we need to save to
	#	the WTS_TrackRec table.  This function is called by the TrackRec
	#	class's "save" method.

	global TR_OLD, TR_NEW			# types of tracking records

	CV = Controlled_Vocab.cv	# get a quick reference to cv info

	# first, try to extract just the parent project directory and project
	# directory from the directory variable.  (just the '100/103' type of
	# info, rather than the full HTML markup)

	if str (values ['directory_variable']) <> 'None':
		re = regex.compile (
			'[A-Za-z: "=<>/_]*'	# skip everything before we...
			'\([/0-9]+\)'		# get the numerical directories
			)
		re.match (values ['directory_variable'])
		proj_dir = re.group (1)		# get the project directory
	else:
		proj_dir = None			# no project directory

	if method == TR_NEW:
		# We have a new tracking record, so do an insert query.  use
		# the in-memory controlled vocab info to save unnecessary joins.

		qry = '''insert WTS_TrackRec (_TR_key, _Priority_key, _Size_key,
			_Status_key, _Status_Staff_key, status_set_date,
			tr_title, modification_date, creation_date,
			attention_by, directory_variable) values (''' + \
			str (values ['_TR_key']) + ', ' + \
			str (CV ['CV_WTS_Priority'][values ['priority_name']]) \
			+ ', ' + \
			str (CV ['CV_WTS_Size'][values ['size_name']]) + \
			', ' + \
			str (CV ['CV_WTS_Status'][values ['status_name']]) + \
			', ' + \
			str (CV ['CV_Staff'][values['status_staff_username']]) \
			+ ', "' + values ['status_set_date'] + '", "' + \
			wtslib.duplicated_DoubleQuotes (values ['tr_title']) \
			+ '", getdate(), getdate(), '

		if str (values ['attention_by']) <> 'None':
			qry = qry + '"' + values ['attention_by'] + '", '
		else:
			qry = qry + ' null, '

		if proj_dir is not None:
			qry = qry + '"' + proj_dir + '")'
		else:
			qry = qry + ' null)'
	else:
		# we need to update an existing tracking record, so we need to
		# do an update query.  use the in-memory controlled vocabulary
		# info to save unnecessary joins.

		qry = 'update WTS_TrackRec set _Priority_key = ' + \
			str (CV ['CV_WTS_Priority'][values ['priority_name']]) \
			+ ', _Size_key = ' + \
			str (CV ['CV_WTS_Size'][values ['size_name']]) + \
			', _Status_key = ' + \
			str (CV ['CV_WTS_Status'][values ['status_name']]) + \
			', _Status_Staff_key = ' + \
			str (CV ['CV_Staff'][values['status_staff_username']]) \
			+ ', status_set_date = "' + values['status_set_date'] \
			+ '", tr_title = "' + wtslib.duplicated_DoubleQuotes ( \
			values['tr_title']) + \
			'", modification_date = getdate()'

		# directory_variable is write-once, read-many.  If we don't have
		# a value specified, then don't bother with it.

		if proj_dir is not None:
			qry = qry + (', directory_variable = "%s"' % proj_dir)

		if str (values ['attention_by']) <> 'None':
			qry = qry + (', attention_by = "%s"' % \
					values ['attention_by'])
		else:
			qry = qry + ', attention_by = null'

		qry = qry + ' where (_TR_key = ' + str (values['_TR_key']) + ')'

	return [ qry ]


def save_Standard_M2M (
	values,		# dictionary of database fieldnames mapped to their
			# new values.
	old_values,	# dictionary of database fieldnames mapped to their
			# values as currently stored in the database.
	method		# global TR_OLD (to save an existing tracking record)
			# or global TR_NEW (to save a new tracking record)
	):
	# Purpose: generate SQL statements needed to update the database tables
	#	for the four standard many-to-many relationships included in a
	#	tracking record (Type, Area, Staff, and Requested By) so that
	#	the data for the tracking record info in values is correct.
	# Returns: a list of strings, each of which is a SQL statement to be
	#	executed in order for the values to save appropriately in
	#	the specified tables (see Notes).
	# Assumes: Parameter method will be TR_OLD or TR_NEW.  Controlled
	#	vocabulary objects are available from a dictionary at
	#	Controlled_Vocab.cv which is keyed by table name.
	# Effects: If method is TR_NEW then we generate SQL insert statements
	#	to add the current contents of values to the tables specified.
	#	If method is TR_OLD then we generate SQL delete and insert
	#	statements to delete old information and add new information
	#	for this tracking record.  Return these SQL commands in a list
	#	of strings.
	# Throws: nothing
	# Notes: values may contain more data than is saved to WTS_Area, 
	#	WTS_Type, WTS_Staff_Assignment, and WTS_Requested_By.  In this
	#	function, we only extract the pieces we need to save to these
	#	tables.  This function is called by the TrackRec class's "save"
	#	method.

	global TR_OLD, TR_NEW			# types of tracking records

	CV = Controlled_Vocab.cv	# get a quick reference to cv info

	# build a list with info for the four many-to-many relationships, with
	# item format: (key name in values, destination table name, CV source
	# table name, field name in destination table)

	MM = [ ('type', 'WTS_Type', 'CV_WTS_Type', '_Type_key'), \
		('area', 'WTS_Area', 'CV_WTS_Area', '_Area_key'), \
		('staff_list', 'WTS_Staff_Assignment', 'CV_Staff',
			'_Staff_key'), \
		('requested_by', 'WTS_Requested_By', 'CV_Staff', '_Staff_key') ]

	# no queries so far

	queries = []

	if method == TR_NEW:
		# we have a new tracking record, so do insert queries.  use
		# the in-memory controlled vocab info to save unnecessary joins.

		for item in MM:
			tmp_data = wtslib.string_To_List (values [item [0]])

			# build an insert query for each value

			for key in tmp_data:
				val = CV [item[2]][key]
				if val:
					queries.append ('insert ' + item [1] + \
						' (_TR_key, ' + item [3] + \
						') values (' + \
					str (values ['_TR_key']) + ', ' + \
					str (val) + ')')
	else:
		# we need to update an existing tracking record, so we need to
		# delete no-longer-current entries, and add new additions.  use
		# the in-memory controlled vocabulary info to save unnecessary
		# joins.

		for item in MM:

			# get a list of old and new values

                        if old_values.has_key (item [0]):
				tmp_old = wtslib.string_To_List ( \
					old_values [item[0]])
                        else:
				tmp_old = []
                        if values.has_key (item [0]):
				tmp_val = wtslib.string_To_List ( \
					values [item[0]])
                        else:
				tmp_val = []

			# now, collect a set of entries which were in the older
			# version yet not in the newer.

			del_set = ()		# set to be deleted
			for key in tmp_old:
				if key not in tmp_val:
					del_set = del_set + (CV[item[2]][key], )

			# now, build a delete query to remove the no-longer-
			# current items that we found. (if any)

			del_len = len (del_set)
			if del_len > 0:
				if (del_len > 1):
					# convert tuple to string

					del_str = str (del_set)
				else:
					# convert tuple to string, and remove
					# the trailing comma

					del_str = str (del_set) [:-2] + ')'

				queries.append ('''delete from %s
					where	(_TR_key = %s) and
						(%s in %s)''' % \
					(item [1], values ['_TR_key'], item [3],
					del_str))

			# we also need to look for entries which have been
			# added since we loaded in this tracking record, and
			# then produce queries to add them.

			for key in tmp_val:
				if key and (key not in tmp_old):
					queries.append ('insert ' + item[1] + \
						' (_TR_key, ' + item[3] + \
						') values (' + \
						str (values ['_TR_key']) + \
						', ' + str (CV [item[2]] \
						[key]) + ')')
	return queries


def save_Text_Fields (
	values,		# dictionary of database fieldnames mapped to their
			# new values.
	old_values,	# dictionary of database fieldnames mapped to their
			# values as currently stored in the database.
	method		# global TR_OLD (to save an existing tracking record)
			# or global TR_NEW (to save a new tracking record)
	):
	# Purpose: generate SQL statements needed to update WTS_Text table
	#	for the large text fields included in a tracking record
	#	(Project Definition, Progress Notes) so that the data for the
	#	tracking record info in values is correct.
	# Returns: a list of strings, each of which is a SQL statement to be
	#	executed in order for the values to save appropriately in
	#	the specified tables (see Notes).
	# Assumes: Parameter method will be TR_OLD or TR_NEW.
	# Effects: If method is TR_NEW then we generate SQL insert statements
	#	to add the current (non-blank) contents of values to the tables
	#	specified.  If method is TR_OLD then we generate:  SQL delete
	#	statements for text fields that have become blank, SQL insert
	#	statements for those which were blank but are now defined, and
	#	SQL update statements for those text fields which have had
	#	their values change.  Return these SQL commands in a list
	#	of strings.
	# Throws: nothing
	# Notes: values may contain more data than is saved to WTS_Text.  This
	#	function, we only extract the pieces we need to save to this
	#	table.  This function is called by the TrackRec class's "save"
	#	method.

	global TR_NEW, TR_OLD				# tracking record types
	global PROGRESS_NOTES, PROJECT_DEFINITION	# types of text fields

	# map the database fieldname of the field to the text_type

	text_fields = (('project_definition', PROJECT_DEFINITION),
		('progress_notes', PROGRESS_NOTES) )

	queries = []				# no queries so far

	# note that when including the text string inside the query string,
	# we need to make sure that all internal double quotes have been
	# repeated.  Otherwise, sybase think we're ending the string
	# prematurely.

	if method == TR_NEW:
		for item in text_fields:
			if not blank (values [item[0]]):
				queries.append ('''insert WTS_Text (text_block,
					_TR_key, text_type) values ("''' + \
					wtslib.duplicated_DoubleQuotes ( \
					values [item [0]]) + '", ' + \
					str (values ['_TR_key']) + ', ' + \
					str (item [1]) + ')'
					)
	else:
		# for editing, we really have four notable cases:
		#	both entries are blank, so we can ignore them
		#	the current entry is blank and there was an old entry,
		#		in which case we can just run a delete query to
		#		ensure that there is none in the database.
		#	there is a current entry, but there is no old entry, so
		#		we need to insert a new record
		#	the current entry differs from the old one, so we need
		#		to update it

		for item in text_fields:
			# new_blank = is the new entry blank?
			# old_blank = is the old entry blank?

			new_blank = blank (values [item[0]])
			old_blank = blank (old_values [item[0]])

			if new_blank and old_blank:
				pass
			elif new_blank and not old_blank:
				queries.append ('''delete from WTS_Text where
					((_TR_key = ''' + str (values \
					['_TR_key']) + ') and (text_type = ' + \
					str (item [1]) + '))')
			elif old_blank and not new_blank:
				queries.append ('''insert WTS_Text (text_block,
					_TR_key, text_type) values ("''' + \
					wtslib.duplicated_DoubleQuotes ( \
					values [item [0]]) + '", ' + \
					str (values ['_TR_key']) + ', ' + \
					str (item [1]) + ')'
					)

			# If we reach this point, then both old and new values
			# are non-blank.  If they are different, then we need
			# to use an update query.

			elif (old_values [item[0]] <> values [item[0]]):
				queries.append ('''update WTS_Text set
					text_block = "''' + \
					wtslib.duplicated_DoubleQuotes ( \
					values[item[0]]) + \
					'" where ((_TR_key = ' + \
					str (values ['_TR_key']) + \
					') and (text_type = ' + \
					str (item [1]) + '))'
					)
	return queries


def save_Relationships (
	values,		# dictionary of database fieldnames mapped to their
			# new values.
	old_values,	# dictionary of database fieldnames mapped to their
			# values as currently stored in the database.
	method		# global TR_OLD (to save an existing tracking record)
			# or global TR_NEW (to save a new tracking record)
	):
	# Purpose: generate SQL statements needed to update WTS_Relationship
	#	table for the inter-TR relationships included in the tracking
	#	record info specified in values.
	# Returns: a list of strings, each of which is a SQL statement to be
	#	executed in order for the values to save appropriately in
	#	WTS_Relationship.
	# Assumes: Parameter method will be TR_OLD or TR_NEW.
	# Effects: If method is TR_NEW then we generate SQL insert statements
	#	to add the current (non-blank) contents of values to the tables
	#	specified.  If method is TR_OLD then we generate:  SQL delete
	#	statements for relationships that no longer exist, and SQL
	#	insert statements for those relationships which have been added.
	#	Return these SQL commands in a list of strings.
	# Throws: nothing
	# Notes: values may contain more data than is saved to WTS_Relationship.
	#	This function, we only extract the pieces we need to save to
	#	this table.  This function is called by the TrackRec class's
	#	"save" method.

	global TR_OLD, TR_NEW			# types of tracking records

	queries = []				# no queries yet

	# if there were no changes, then just bail out.

	### HERE
	if old_values ['depends_on'].equals (values ['depends_on']):
		return queries

	if method == TR_NEW:
		# copy the set of keys we need to add, and then remove the
		# current tracking record from "tmp_val" so it can't depend on
		# itself

		tmp_val = values ['depends_on'].clone ()
		tmp_val.remove (string.atoi (values ['_TR_key']))

		# we have a new tracking record, so we just need to insert
		# the relevant records into WTS_Relationship

		for item in tmp_val.values ():
			queries.append ('''insert WTS_Relationship (_TR_key,
				_Related_TR_key, relationship_type,
				transitive_closure) values (%s, %s, %d, 0)''' \
				% (str (values['_TR_key']), str (item),
				DEPENDS_ON)
				)
	else:
		# we need to update the relationships for an existing tracking
		# record.  So, we need to go through and find old relation-
		# ships that no longer exist, and new relationships.  (and, of
		# course, produce the queries that will address them)

		# Collect a Set of entries which were in the older version yet
		# not in the newer.  And, if we found any, build a SQL Delete
		# statement to remove them from the database.

		to_be_deleted = old_values ['depends_on'].difference (
			values ['depends_on'])
		if not to_be_deleted.empty ():
			queries.append ('''
				delete from WTS_Relationship
				where	((_TR_key = %s) and
					(_Related_TR_key in (%s)) and
					(transitive_closure = 0) and
					(relationship_type = %d))''' % \
				(str (values ['_TR_key']), str (to_be_deleted),
				DEPENDS_ON))

		# we also need to look for entries which have been added since
		# we loaded in this tracking record, make sure that it does not
		# depend on itself, and then produce queries to add the other
		# new entries

		to_be_added = values ['depends_on'].difference (
			old_values ['depends_on'])
		to_be_added.remove (values ['_TR_key'])
		for key in to_be_added.values ():
			queries.append ('''
				insert WTS_Relationship (_TR_key,
					_Related_TR_key, relationship_type,
					transitive_closure)
				values (%s, %s, %d, 0)''' % \
					(str (values ['_TR_key']), str (key),
					DEPENDS_ON))
	return queries


#-OTHER SUPPORTING FUNCTIONS------------------------------------------------

def blank (
	s	# a string to examine to see if it is blank
	):
	# Purpose: To determine if string s should be considered to be blank.
	# Returns: (boolean) 1 if s is blank for the purposes of a text field,
	#	or 0 if not blank.  Blank is defined as None, '', 'None', or a
	#	string of all spaces.
	# Assumes: s is a string.
	# Effects: see Returns.
	# Throws: 1. TypeError if s is not a string.

	if s:
		short_s = string.strip (s)
		if not ((short_s == 'None') or (short_s == '')):
			return 0
	return 1


def expand_TR_Range (
	rng,	# a string specifying a range of tracking record numbers.
		# range is defined as:  lo..hi  Either lo or hi is optional,
		# but not both.
	key	# string name of the key for tracking records in the database
	):
	# Purpose: generate a string which is a clause suitable for inclusion
	#	in the 'where' part of a query, representing the range of
	#	tracking records specified in rng.
	# Returns: a string as defined above in Purpose.
	# Assumes: hi and lo (see explanation of rng) are both integers.
	# Effects: Extracts an integer from either side of the .. separator, if
	#	available.  If neither integer is included, raise an exception.
	#	If only the first value is specified, return a clause selecting
	#	tracking records after that one.  If only the second value is
	#	specified, return a clause selecting tracking records before
	#	that one.  If both values are specified, return a clause
	#	selecting values between them.
	# Throws: 1. ValueError if lo or hi (see explanation of rng) is not
	#	an integer.  2. TrackRec.error if we can't find anything on
	#	either side of the .. separator.
	# Examples:
	#	expand_TR_Range ('15..', '_TR_key')	==> '(_TR_key >= 15)'
	#	expand_TR_Range ('..15', '_TR_key')	==> '(_TR_key <= 15)'
	#	expand_TR_Range ('5..15', '_TR_key')  ==>
	#		'(_TR_key >= 5) and (_TR_key <= 15)'

	nums = string.split (rng, '..')
	if len (nums) <> 2:
		raise error, 'Could not interpret TR range'

	# if both sides of the - are blank, we have a problem

	blank_0 = (nums [0] == '')
	blank_1 = (nums [1] == '')
	if blank_0 and blank_1:
		raise error, 'Could not interpret TR range'
	
	# otherwise, build the string s to be returned

	s = ''					# string to be returned
	if not blank_0:
		temp = string.atoi (nums [0])
		s = s + ' and (' + key + ' >= ' + nums [0] + ')'
	if not blank_1:
		temp = string.atoi (nums [1])
		s = s + ' and (' + key + ' <= ' + nums [1] + ')'
	return s [5:]


def expand_TR (
	tr_numbers,	# string of tracking record numbers separated by commas
			# and possibly including ranges (open-ended or closed).
	key		# name of the key field for tracking records
	):
	# Purpose: To convert a string of tracking record numbers to a list of
	#	clauses which may be used to restrict a query to those tracking
	#	record numbers.
	# Returns: a list of strings, each of which is a single clause suitable
	#	for use (or-ed together) in the "where" section of a SQL select
	#	statement.
	# Assumes: Only the integer part of the tracking record number is
	#	specified in tr_numbers (not the 'TR', too).  This is typical
	#	for the query form.
	# Effects: Splits tr_numbers at the commas into separate pieces.  Each
	#	piece is analyzed to see if it is an integer tracking record
	#	number.  If so, it is added to a list of them for which we later
	#	build a SQL clause.  If not, it is analyzed as a tracking
	#	record range to build clauses.  Returns a list of these clauses.
	# Throws: may propagate from expand_TR_Range: 1. ValueError if low or
	#	high (parts of a range - see Notes) is not an integer. 
	#	2. TrackRec.error if we can't find anything on either side of
	#	the range separator.
	# Notes: Ranges of tracking records are of one of the forms:  (low...,
	#	...high, or low...high).  The separator may be ... (as shown),
	#	.. or -.
	# Example:
	#	expand_TR ('3, 4-6, 8, 10, 12-17', '_TR_key')
	#    results in:
	#	[ '((_TR_key >= 4) and (_TR_key <= 6))',
	#	  '((_TR_key >= 12) and (_TR_key <= 17))',
	#	  '(_TR_key in (3, 8, 10)' ]

	# compile a regular expression to confirm that a string consists of
	# just an integer, and then extract that number in a group

	find_int = regex.compile ( \
		'^[ \t]*'		# leading space at string beginning
		'\([0-9]+\)'		# group 1 = integer (at least one digit)
		'[ \t]*$')		# trailing space at string end

	# map all - and ... to be .. so the code can be simple afterwards

	modified_tr = regsub.sub ('\.\.\.', '..', tr_numbers)
	modified_tr = regsub.sub ('-', '..', modified_tr)

	items = string.split (string.translate (modified_tr, \
		string.maketrans ('', ''), ' '), ',')

	nrs = []			# list of single specified TR #'s
	clauses = []			# list of clauses so far

	for item in items:
		# see if it is a single tracking record number (if so, we just
		# convert it to an integer and add to nrs)

		if find_int.match (item) >= 0:
			nrs.append (string.atoi (find_int.group (1)))

		# otherwise, try to interpret item as a range of tracking
		# record numbers

		else:
			clauses.append (expand_TR_Range (item, key))

	# if we found any single tracking record numbers specified, add a
	# clause for them

	if len (nrs) > 0:
		clauses.append ('(' + key + ' in (' + \
			wtslib.list_To_String (nrs) + '))')
	return clauses


def opposite (
	input_item	# an integer or string for which we want an opposite
	):
	# Purpose: While sorting a list in python is easy, and reversing it is
	#	also easy, it is a little more difficult when you have a joint
	#	"sorting key".  For example, if you want to sort by a tuple of
	#	information, but you want to sort so that the first component
	#	is sorted in ascending order, but the second is in descending
	#	order.  (You want: [ (2, 3), (3, 4), (2, 1), (2, 2) ] to become
	#	[ (2, 3), (2, 2), (2, 1), (3, 4) ].  One way to accomplish this
	#	is to convert the item you want to sort in descending order to
	#	an item which is the "opposite" of the original one.  For the
	#	example above, if we make the second component of each tuple
	#	negative and then convert them back to positive, it sorts as
	#	intended.  This function will produce the correct "opposite"
	#	value for sorting strings and integers in descending order.
	# Returns: a string or integer (depending on the type of input_item)
	#	which will sort in reverse order of input_item.
	# Assumes: input_item is a lowercase string or an integer.
	# Effects: see Purpose and Examples.
	# Throws: 1. TypeError if input_item is not a string or an integer.
	# Examples:
	#	opposite (3)		==> -3
	#	opposite (-4)		==> 4
	#	opposite ('abc')	==> 'zyx'

	# for integers, the negation will sort in reverse order

	if type (input_item) == types.IntType:
		return -input_item
	else:

		# for strings, we use swap each letter at position x in the
		# alphabet, we swap it with the one at position (27-x).  The
		# resulting string will sort in reverse order.

		return string.translate (string.lower (input_item), \
			string.maketrans ( 'abcdefghijklmnopqrstuvwxyz', \
			'zyxwvutsrqponmlkjihgfedcba' ), '')


def remove (
	orig,		# list of items to be examined
	del_item	# item to be purged from orig
	):
	# Purpose: to remove all instances of del_item from the list orig.
	# Returns: a copy of orig which no longer contains any instances of
	#	del_item.
	# Assumes: nothing
	# Effects: generates and returns a lsit containing all items from orig
	#	(except del_item) in their original order.
	# Throws: nothing

	list = []
	for i in orig:
		if i <> del_item:
                        list.append (i)
	return list


def lockedTrackRecList ():
	# Purpose: get info about the currently locked tracking records
	# Returns: a list of tuples, each of which represents a single tracking
	#	record containing:
	#		(TR #, who locked it, when locked, abbreviated title)
	# Assumes: db's SQL routines have been initialized
	# Effects: see Returns
	# Throws: propagates wtslib.sqlError if any problems are encountered
	#	while executing the SQL statements

	results = wtslib.sql ('''
		select tr._TR_key, st.staff_username,
			convert (varchar (30), tr.tr_title) tr_title,
			convert (varchar, tr.locked_when, 100) locked_when
		from WTS_TrackRec tr, CV_Staff st
		where (tr._Locked_Staff_key = st._Staff_key) and
			(tr.locked_when != null)
		order by tr._TR_key asc''')
	list = []
	for row in results:
		datetime, error = wtslib.parse_DateTime (row ['locked_when'])
		list.append ( (row ['_TR_key'], row ['staff_username'],
				datetime, row ['tr_title']) )
	return list
		

def queryTitle (
	title		# string; value to look for in 'Title' field
	):
	# Purpose: return a string of comma-separated TR numbers which have
	#	'title' in their Title field
	# Returns: see Purpose
	# Assumes: nothing
	# Effects: queries the database
	# Throws: propagates any exceptions thrown by wtslib.sql

	results = wtslib.sql ('''
		select _TR_key
		from WTS_TrackRec
		where tr_title like "%s%s%s"
		order by _TR_key''' % ('%', title, '%'))
	trs = []
	for row in results:
		trs.append (str(row['_TR_key']))
	return string.join (trs, ',')

def directoryOf (
	tr_num	# integer; key of the tracking record whose directory we want
	):
	# Purpose: get the project directory string for the given "tr_num"
	# Returns: either None (if there is no defined project directory for
	#	"tr_num") or a string containing the parent project directory
	#	and the project directory
	# Assumes: db's sql routines have been initialized
	# Effects: queries the database to look up the right directory_variable
	# Throws: 1. IndexError if "tr_num" does not contain a valid tracking
	#	record key, 2. propagates wtslib.sqlError if errors occur in
	#	talking to the database

	result = wtslib.sql ('''select directory_variable dir
				from WTS_TrackRec
				where _TR_key = %d''' % tr_num)
	return result [0]['dir']


def directoryPath (
	dir	# the subdirectory for which we want the Unix path.  This will
		# have both the actual subdirectory, and its parent.
	):
	# Purpose: build and return a string with the full Unix path to dir
	# Returns: see Purpose
	# Assumes: "dir" does not begin with a forward slash '/'
	# Effects: see Returns
	# Throws: nothing

	return os.path.join (Configuration.config ['baseUnixPath'], dir)


def directoryURL (
	dir	# the subdirectory for which we want a URL.  This will have
		# both the actual subdirectory, and its parent.
	):
	# Purpose: build and return an HTML anchor for dir
	# Returns: a string containing the HTML anchor which links to dir, with
	#	the link going to the baseURL and the text showing the
	#	baseUnixPath, both specified in the Configuration
	# Assumes: "dir" does not begin with a forward slash '/'
	# Effects: see Returns
	# Throws: nothing
	# Notes: The anchor uses the (baseURL + dir + '/') in the Href and
	#	displays the (baseUnixPath + dir) as the link
	# Example: 
	#	Assume	baseURL = "http://kelso/WTS_Projects", and
	#		baseUnixPath = "/mgi/all/WTS_Projects"
	#	Then, directoryURL ('100/152')
	#		would return:
	#	'''<A HREF="http://kelso/WTS_Projects/100/152/">
	#	   /mgi/all/WTS_Projects/100/152
	#	   </A>'''

	link = os.path.join (Configuration.config ['baseURL'], dir)
	if link [-1] != os.sep:		# ensure link ends with '/'
		link = link + os.sep
	return '<A HREF="%s">%s</A>' % (link, directoryPath (dir))


def newBaseDirectoryPieces (
	tr_num		# integer tracking record key
	):
	# Purpose: generate names for the project directory (for the given
	#	"tr_num") and its parent directory
	# Returns: a tuple which contains two strings.  The second string is the
	#	project directory for the given tr_num.  The first string is its
	#	parent directory.
	# Assumes: nothing
	# Effects: see Returns
	# Throws: nothing
	# Notes: The name of the project directory is simply the string version
	#	of "tr_num".  Its parent directory is named for the lowest
	#	numbered project directory it will contain.  The number of
	#	project directories within each parent directory is determined
	#	by PROJECT_DIR_GROUPING, a global variable.  If it is set to 100
	#	then parent directory 0 will contain project directories 0-99,
	#	parent 100 will contain 100-199, etc.
	# Example:
	#	if PROJECT_DIR_GROUPING = 100, then:
	#		newBaseDirectoryPieces (172) returns: ( '100', '172' )

	global PROJECT_DIR_GROUPING

	return ( str ( (tr_num / PROJECT_DIR_GROUPING) * PROJECT_DIR_GROUPING),
		str (tr_num))


def getBaseDir (
	tr_num		# integer tracking record key
	):
	# Purpose: look up the base directory for the tracking record with the
	#	specified key
	# Returns: None if the specified tr_num does not have a defined
	#	directory, or a string containing that base directory if it
	#	has been defined.
	# Assumes: db's sql routines have been initialized
	# Effects: see Returns
	# Throws: nothing
	# Notes: This function will return None if either:  the tracking record
	#	with key "tr_num" has a null directory, or if there is no
	#	tracking record with key "tr_num".

	results = wtslib.sql ('''select directory_variable
				from WTS_TrackRec
				where _TR_key = %d''' % tr_num)

	if len (results) == 0:		# no tracking record with that "tr_key"
		return None
	return results [0]['directory_variable']


def rebuild_htaccess (
	tr_num	# integer number of a tracking record in the directory
		# which needs its .htaccess file rebuilt
	):
	# Purpose: rebuilds the .htaccess file for the parent project directory
	#	which would contain the project directory for "tr_num"
	# Returns: nothing
	# Assumes: the parent project directory of tr_num exists
	# Effects: If the parent directory of tr_num does not exist, we create
	#	it in this function.  We regenerate the .htaccess file in that
	#	directory.
	# Throws: propagates -- 1. wtslib.sqlError if a problem occurs in
	#	accessing the database, 2. others possible if a problem occurs
	#	in creating the directory or writing the file.

	global PROJECT_DIR_GROUPING

	# get the name of the project directory and its parent

	parentDirName, projectDirName = newBaseDirectoryPieces (tr_num)

	# build the full unix path to the parent directory

	directory = os.path.join (Configuration.config ['baseUnixPath'],
		parentDirName)

	# if the parent directory does not yet exist, create it, turn on its
	# its sticky bit, and set the group to 'mgi'

	if not os.path.exists (directory):
		os.mkdir (directory)
		os.chmod (directory, 0755)		# rwxr-xr-x

		# We need to do two system calls here, one because python only
		# uses octal mode for chmod and the sticky bit can't be set
		# using octal mode, and the other because python does not
		# provide a chgrp function.

		os.system ('%s g+s %s' % (CHMOD, directory))
		os.system ('%s mgi %s' % (CHGRP, directory))

	# get the lowest numbered directory stored in this parent directory,
	# then retrieve all TR #'s and keys which could have project directories
	# under that parent project directory.

	least_num = string.atoi (parentDirName)

	records = wtslib.sql ('''select _TR_key, tr_title
				from WTS_TrackRec
				where (_TR_key >= %s) and (_TR_key <= %s)
				order by _TR_key''' % \
			(least_num, least_num + PROJECT_DIR_GROUPING - 1) )

	# lastly we need to get a file pointer (fp) to the file we want to write

	htaccess = os.path.join (directory, '.htaccess')
	fp = open (htaccess, 'w')

	fp.write ('IndexOptions FancyIndexing SuppressSize\n')	# write header
	fp.write ('IndexIgnore SCCS .*\n')			# lines

	# and finally, write out a single AddDescription line for each
	# tracking record which could have a directory in this parent dir

	for rec in records:
		# convert any double-quotes in the title to be single-quotes,
		# as it otherwise causes an error when the server tries to
		# process the title.

		title = regsub.gsub ('"', "'", rec ['tr_title'])
		fp.write ('AddDescription "%s" /%s\n' % \
			(title, str (rec ['_TR_key'])))
	fp.close ()
	os.chmod (htaccess, 0666)				# rw-rw-rw-
	return


#-TRANSITIVE CLOSURE CODE---------------------------------------------------

def updateTransitiveClosure (
	tr_num,		# integer; key of the tracking record we're working with
	rel_type,	# integer; type of relationship for which to update t.c.
	):
	# Purpose: updates the transitive closure in the database for the given
	#	relationship type ("rel_type") for all nodes which are related
	#	to the specified "tr_num"
	# Returns: (ArcSet of added Arcs, ArcSet of deletedArcs)
	# Assumes: that the changes to the actual arcs in WTS_Relationship have
	#	already been made.
	# Effects: see Purpose.
	# Throws: 1. wtslib.sqlError if there is a problem in executing the SQL
	#	statements for some reason.
	# Notes: This function recomputes the transitive closure around the
	#	given "tr_num" and updates the database accordingly.  To do
	#	this, we:
	#		* look up and down the new dependency relationships to
	#			find all tracking records related to "tr_num"
	#		* load arcs among those tracking records
	#		* compute the new transitive closure based on those
	#			arcs and tracking records
	#		* load the old transitive closure
	#		* reconcile the differences (missing / new arcs)
	
	TC_LINK = 1		# constant; indicates this is t.c.-related
	NOT_TC_LINK = 0		# constant; indicates this is not t.c.-related

	to_add = ArcSet.ArcSet ()	# set of Arc objects to add to the
					# database to update the transitive
					# closure among tracking records.
	to_delete = ArcSet.ArcSet ()	# set of Arc objects to delete from the
					# database to update the transitive
					# closure among tracking records.

	to_do = Set.Set ()	# set of tracking record numbers yet
				# to be examined
	done = Set.Set ()	# set of tracking record numbers we have
				# already examined

	connected_component = ArcSet.ArcSet ()	# the set of dependencies (arcs)
						# which currently exists among
						# the tracking records numbers
						# in "done"

	to_do.add (tr_num)	# start with the specified tracking record

	# keep going until no more unexamined tracking records

	while not to_do.empty ():
		# get a list of tracking records left to examine, and
		# initialize a list of arcs among them:

		to_do_list = to_do.values ()
		arcs = []

		# because of a sybase limit of 250 ORs & ANDs in the WHERE
		# clause, we need to handle our to-do items in chunks of,
		# at most, 100:

		for sublist in wtslib.splitList (to_do_list, 100):
			to_do_string = wtslib.list_To_String (sublist)

			# get the arcs which either originate or terminate at
			# tracking records in "sublist"

			arc_sublist = wtslib.sql ('''
				select _TR_key, _Related_TR_key
				from WTS_Relationship
				where (relationship_type = %d) and
					(transitive_closure = %d) and
					((_TR_key in (%s)) or
					(_Related_TR_key in (%s)))''' % \
			(rel_type, NOT_TC_LINK, to_do_string, to_do_string))

			# now, add these arcs to the larger list we are
			# compiling for the entire "to_do_list":

			arcs = arcs + arc_sublist

		done = done.union (to_do)	# we have now queried on those
		to_do = Set.Set ()		# in "to_do", so move them to
						# be in "done"

		# and, go through the new arcs we found.  Add each to the
		# "connected_component", and remember new ones in "to_do" so
		# that we can look for their relatives on the next pass.

		for arc in arcs:
			start = arc ['_TR_key']
			stop = arc ['_Related_TR_key']
			connected_component.addArc (Arc.Arc (start, stop))
			if not done.contains (start):
				to_do.add (start)
			if not done.contains (stop):
				to_do.add (stop)

		# end of While loop

	# go through and get the old transitive closure (that which still
	# exists in the database) for this connected component.  We use an OR
	# between the last two clauses to catch arcs which go to/from nodes
	# which may have been removed from the dependencies.

	old_closure = []	# initialize a list to contain all old closure
				# records

	# again, because of a sybase limit of 250 ORs & ANDs in the WHERE
	# clause, we need to handle our to-do items in chunks of,
	# at most, 100:

	for sublist in wtslib.splitList (done.values (), 100):
		done_str = wtslib.list_To_String (sublist)
		if len(done_str) > 0:
			old_closure_sublist = wtslib.sql ('''
				select _TR_key, _Related_TR_key
				from WTS_Relationship
				where (relationship_type = %d) and
					(transitive_closure = %d) and
					((_TR_key in (%s)) or
					(_Related_TR_key in (%s)))''' % \
				(rel_type, TC_LINK, done_str, done_str))

			# now, add to the old_closure

			old_closure = old_closure + old_closure_sublist

	old_tc = ArcSet.ArcSet ()	# the old transitive closure
	for row in old_closure:
		old_tc.addArc (Arc.Arc (row ['_TR_key'],
			row ['_Related_TR_key']))

	# now, pass the connected_component on to the Digraph module which will
	# compute the new transitive closure and whether the digraph has a
	# cycle.  (We currently do not care about cycles.)

	digraph = Digraph.Digraph (connected_component)
	new_tc = digraph.getTransitiveClosure ()

	# Finally, we are ready to go through the old transitive closure
	# (old_tc) and the new transitive closure (new_tc) to find out what
	# has changed.

	# Go through the old transitive closure.  Any Arc which does not appear
	# in the new transitive closure must be deleted (it is no longer in
	# the transitive closure), except self-referential arcs.

	for arc in old_tc.getArcs ():
		if not new_tc.exists (arc):
			if arc.getFromNode () != arc.getToNode ():
				to_delete.addArc (arc)

	# And, go through the new transitive closure.  Any Arc which does not
	# appear in the old transitive closure must be added.  (They are now in
	# the transitive closure)

	for arc in new_tc.getArcs ():
		if not old_tc.exists (arc):
			to_add.addArc (arc)

	# Finally, we need to update the database to reflect the new transitive
	# closure.  To do that, we need to build a list of SQL statements to
	# delete arcs from and add arcs to the WTS_Relationship table.

	sql_statements = []		# list of sql statements to update the
					# WTS_Relationship table

	# generate insert statements for arcs we need to add to transitive
	# closure.

	for arc in to_add.getArcs ():
		sql_statements.append ('''
			insert WTS_Relationship (_TR_key, _Related_TR_key,
				relationship_type, transitive_closure)
			values (%d, %d, %d, %d)''' % \
				(arc.getFromNode (), arc.getToNode (),
				rel_type, TC_LINK))

	# generate delete statements for arcs we need to delete from the
	# transitive closure.

	for arc in to_delete.getArcs ():
		sql_statements.append ('''
			delete from WTS_Relationship
			where	(_TR_key = %d) and
				(_Related_TR_key = %d) and
				(relationship_type = %d) and
				(transitive_closure = %d)''' % \
			(arc.getFromNode (), arc.getToNode (),
				rel_type, TC_LINK))

	# Execute those sql statements to bring the database up to date.

	if len (sql_statements) > 0:
		wtslib.sql (sql_statements)
	return (to_add, to_delete)

#-Tree Generating Code------------------------------------------------------

# define two global variables for use in this section:
#	Child_Query = the query to find children of a given node
#	ChildrenOf = a dictionary which maps a node to its children

ChildQuery = '''select _Related_TR_key
		from WTS_Relationship
		where (_TR_key = %d) and
			(relationship_type = %d) and
			(transitive_closure = 0)
		order by _Related_TR_key'''
ChildrenOf = {}

def getChildrenOf (
	tr_num		# number of the tracking record we are investigating
	):
	# Purpose: return a list of tracking records on which "tr_num" depends
	# Returns: a list of integer tracking record numbers
	# Assumes: db's SQL routines have been initialized
	# Effects: queries the database to retrieve children of tr_num
	# Throws: propagates wtslib.sqlError if we have problems querying the
	#	database

	results = wtslib.sql (ChildQuery % (tr_num, DEPENDS_ON))
	kids = []
	for row in results:
		kids.append (row ['_Related_TR_key'])
	return kids

def subTreeOf (
	tr_num		# number of the tracking record we want to investigate
	):
	# Purpose: return a list with information about all tracking records on
	#	which "tr_num" depends
	# Returns: a list as described in Notes
	# Assumes: db's SQL routines have been initialized
	# Effects: queries the database to build the required list, adds entries
	#	to the ChildrenOf dictionary
	# Throws: propagates wtslib.sqlError if we have problems querying the
	#	database
	# Notes: We return a list with potentially multiple items.  The first
	#	item will be the integer "tr_num".  Each other item will be a
	#	list describing the subtree under one of its children.
	# Example:  If we have the following dependencies:
	#		1 on 2		2 on 3		2 on 4
	#		3 on 5		3 on 6
	#	Then, subTreeOf (3) would return:
	#		[ 3, [5], [6] ]
	#	And, subTreeOf (1) would return:
	#		[ 1, [2, [3, [5], [6]], [4]]]

	global ChildrenOf

	if not ChildrenOf.has_key (tr_num):
		ChildrenOf [tr_num] = getChildrenOf (tr_num)
	kids = ChildrenOf [tr_num]
	list = [ tr_num ]
	for kid in kids:
		list.append (subTreeOf (kid))
	return list

def graphSubTree (
	branch,		# the subtree to graph (as generated by subTreeOf () )
	titles,		# dictionary mapping TR number to TR title
	prefix = '',	# prefix used to indent this line
	showTitle = TRUE	# boolean; show the title beside each TR number?
	):
	# Purpose: return a list of strings which graph (textually) this
	#	"branch"
	# Returns: a list of strings
	# Assumes: nothing
	# Effects: builds the required list
	# Throws: nothing
	# Example:  If we have the following dependencies:
	#		1 on 2		2 on 3		2 on 4
	#		3 on 5		3 on 6
	#	Then, the lines returned by graphSubTree (3, {}, '', FALSE)
	#	would look like:
	#		3
	#		+-------5
	#		+-------6
	#	Then, the lines returned by graphSubTree (1, {}, '', FALSE)
	#	would look like:
	#		1
	#		+-------2
	#		|	+-------3
	#		|	|	+-------5
	#		|	|	+-------6
	#		|	+-------4

	# build the initial line for this branch, taking into account whether
	# we want to show the titles or not.

	if showTitle == TRUE:
		line = "%s%s : %s" % (prefix, branch [0], titles [branch[0]])
	else:
		line =  "%s%s" % (prefix, branch [0])

	lines = [ line [:79] ]		# the set of lines to return

	# now that we've used the prefix for this line, we should map the
	# '-' to ' ', and the '+' to '|' for a nicer visual effect.

	prefix = string.translate (prefix, string.maketrans ('-+', ' |'), '')

	# and, get the lines for all the children of this branch

	for subBranch in branch [1:]:
		lines = lines + graphSubTree (subBranch, titles,
			prefix + '+-------', showTitle)
	return lines

def graphTree (
	tr_num,			# "root" tracking record number we want to graph
	showTitle = TRUE	# show the titles beside the TR nubmers?
	):
	# Purpose: return a list of strings which graph (textually) the
	#	dependencies of "tr_num"
	# Returns: a list of strings
	# Assumes: nothing
	# Effects: builds the required list
	# Throws: propagates wtslib.sqlError if we have problems querying the
	#	database
	# Example: see the Examples of graphSubTree()

	tree = subTreeOf (tr_num)
	results = wtslib.sql ('select _TR_key, tr_title from WTS_TrackRec')
	titles = {}
	for row in results:
		titles [ row ['_TR_key'] ] = row ['tr_title']
	return graphSubTree (tree, titles, '', showTitle)


#-Code for handling building a table for query results----------------------

def getSqlForTempStatusTable (
	start,		# starting date, as a string, or ''
	stop		# stopping date, as a string, or ''
	):
	# Purpose: produces a temp table with TR info based on a range of
	#	Status Dates bounded by "start" and "stop".  The table includes
	#	info for TR's which had at least one change in Status in that
	#	time period.  The table has fields "_TR_key", "_Status_key",
	#	and "status_set_date".  Only the latest Status change is
	#	recorded in the table.
	# Returns: a tuple with (name of the table generated, list of SQL
	#	statements needed to generate the table)
	# Assumes: nothing
	# Effects: when the list of SQL statements is run, they produce a
	#	temporary table
	# Throws: nothing

	# returns (string name of table, list of query strings)

	misc_dates = ''
	tr_dates = ''
	if start != '':
		misc_dates = ' and (misc.set_date >= "%s")' % start
		tr_dates = ' and (tr.status_set_date >= "%s")' % start
	if stop != '':
		misc_dates = misc_dates + ' and (misc.set_date <= "%s")' % stop
		tr_dates = tr_dates + ' and (tr.status_set_date <= "%s")' % stop
	misc_dates = misc_dates [5:]
	tr_dates = tr_dates [5:]

	tbl_root = "#TMP_%s" % os.environ ['REMOTE_USER']
	tbl = "%s_Status" % tbl_root
	tbl_1 = "%s_1" % tbl_root
	tbl_2 = "%s_2" % tbl_root
	tbl_keymap = "%s_key_map" % tbl_root
	tbl_updates = "%s_update" % tbl_root
	tbl_inserts = "%s_insert" % tbl_root

	q1 = '''select _TR_key, status_set_date = max(set_date)
		into %s
		from WTS_Status_History misc
		where %s
		group by _TR_key''' % (tbl_1, misc_dates)

	q2 = '''select t1._TR_key, t1.status_set_date, sh._Status_key
		into %s
		from %s t1, WTS_Status_History sh
		where (t1._TR_key = sh._TR_key) and
			(t1.status_set_date = sh.set_date)''' % (tbl_2, tbl_1)

	q3 = '''select tr_TR_key = tr._TR_key, res_TR_key = res._TR_key
		into %s
		from WTS_TrackRec tr, %s res
		where (tr._TR_key *= res._TR_key)''' % (tbl_keymap, tbl_2)

	q4 = '''select tr._TR_key, tr.status_set_date, tr._Status_key
		into %s
		from %s km, WTS_TrackRec tr
		where (km.tr_TR_key = tr._TR_key) and (km.res_TR_key != null)
			and %s''' % (tbl_updates, tbl_keymap, tr_dates)

	q5 = '''select tr._TR_key, tr.status_set_date, tr._Status_key
		into %s
		from %s km, WTS_TrackRec tr
		where (km.tr_TR_key = tr._TR_key) and (km.res_TR_key = null)
			and %s''' % (tbl_inserts, tbl_keymap, tr_dates)

	q6 = '''update %s
		set _Status_key = upd._Status_key,
			status_set_date = upd.status_set_date
		from %s upd
		where (upd._TR_key = %s._TR_key)''' % (tbl_2, tbl_updates,
			tbl_2)

	q7 = '''insert into %s (_TR_key, _Status_key, status_set_date)
			select _TR_key, _Status_key, status_set_date
			from %s''' % (tbl_2, tbl_inserts)

	# In the case where a TR had two status changes in the same minute, it
	# is not possible to tell which was the latter.  So, we arbitrarily
	# choose the one with the highest key...

	q8 = '''select _TR_key, status_set_date, _Status_key = max (_Status_key)
		into %s
		from %s
		group by _TR_key''' % (tbl, tbl_2)

	q9 = 'drop table %s' % tbl_keymap
	q10 = 'drop table %s' % tbl_updates
	q11 = 'drop table %s' % tbl_inserts
	q12 = 'drop table %s' % tbl_1
	q13 = 'drop table %s' % tbl_2

	return (tbl, [ q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13 ])


def getStatusTable (
	row_type,	# string; either "Area" or "Type"
	date_range	# string; a valid date range (dates only, no times)
	):
	# Purpose: get an HTML representation of the (Area or Type) by Status
	#	grid, for the given "start" and "stop" dates
	# Returns: an HTMLgen.TableLite object
	# Assumes: 1. wtslib's SQL routines have been properly initialized;
	#	2. getSqlForTempStatusTable produces a table with these three
	#	fields:  _TR_key, _Status_key, status_set_date
	# Effects: nothing
	# Throws: propagates wtslib.sqlError if an error occurs while running
	#	the SQL statements; raises TrackRec.error if we encounter bad
	#	dates.

	# get the basic set of SQL commands, then add three:
	#	one to extract info from the temp table,
	#	one to extract the needed info for the given controlled vocab
	#		specified in "row_type", and
	#	one to remove the temp table (clean up)

	global error_separator

	(start, stop, err) = wtslib.parse_DateRange (date_range)
	if err is not None:
		raise error, wtslib.list_To_String (err, error_separator)

	tbl_name, statements = getSqlForTempStatusTable (start, stop)
	statements.append ('select * from %s' % tbl_name)
	statements.append ('''
			select res._TR_key, AreaOrType._%s_key
			from %s res, WTS_%s AreaOrType
			where (AreaOrType._TR_key = res._TR_key)''' % \
		(row_type, tbl_name, row_type))
	statements.append ('drop table %s' % tbl_name)

	results = wtslib.sql (statements)

	# extract info about each TR from the first query above, and build:
	#	TR_info [TR #] = (Status key, date status was set)

	TR_info = {}
	for rec in results [-3]:
		key = rec ['_TR_key']
		TR_info [key] = (rec ['_Status_key'], rec ['status_set_date'])

	# extract CV info from the second query above, and build:
	#	cv_info [cv_key][Status key] = Set of TR with that Status
	#		and cv key (only TRs from "tbl_name")

	cv_info = {}
	for row in results [-2]:
		cv_key = row ['_%s_key' % row_type]
		if not cv_info.has_key (cv_key):
			cv_info [cv_key] = {}
		status_key = TR_info [row['_TR_key']][0]
		if not cv_info [cv_key].has_key (status_key):
			cv_info [cv_key][status_key] = Set.Set ()
		cv_info [cv_key][status_key].add (row ['_TR_key'])

	# build:
	#	cv_info [cv_key]['total'] = count of all TRs with that cv key
	#		(only those TRs from "tbl_name")

	for cv_key in cv_info.keys ():
		total = 0
		for status_key in cv_info [cv_key].keys():
			total = total + cv_info [cv_key][status_key].count ()
		cv_info [cv_key]['total'] = total

	# build:
	#	all [status_key] = count of all TRs with that Status (only TRs
	#		from "tbl_name")

	all = {}
	for tr_key in TR_info.keys ():
		status_key = TR_info [tr_key][0]
		if not all.has_key (status_key):
			all [status_key] = 0
		all [status_key] = all [status_key] + 1

	# we want to get a list of the status keys, in order corresponding to
	# their status names, but we can ignore the standard error list and
	# flag (since we're using a known list of statuses):

	status_cv = Controlled_Vocab.cv ['CV_WTS_Status']
	status_keys, ignore_err_list, ignore_err_flag = status_cv.validate (
		wtslib.list_To_String (status_cv.ordered_names ()))

	# we want to get a list of the Type or Area keys, in order corresponding
	# to their names, but we can ignore the standard error list and
	# flag (since we're using a known list of types/areas):

	if row_type == 'Type':
		row_cv = Controlled_Vocab.cv ['CV_WTS_Type']
	else:
		row_cv = Controlled_Vocab.cv ['CV_WTS_Area']
	row_keys, ignore_err_list, ignore_err_flag = row_cv.validate (
		wtslib.list_To_String (row_cv.ordered_names ()))

	# now, build the HTMLgen table...

	tbl = HTMLgen.TableLite (border = 3, align = 'center')

	basicURL = 'tr.query.results.cgi?Status_Date=%s&Displays=%s' % (
		date_range, 'TR_Nr,Title,%s,Status,Status_Date' % row_type)

	# build the header row, with a blank cell followed by Status names:

	header_row = HTMLgen.TR ()
	header_row.append (HTMLgen.TH (HTMLgen.BR ()))
	for s in status_keys:
		status = status_cv.keyToName (s)
		header_row.append (HTMLgen.TH (HTMLgen.Href (basicURL + \
			"&Status=%s&Primary=%s" % (status, row_type),
			status[:3])))
	header_row.append (HTMLgen.TH (HTMLgen.Italic (HTMLgen.Href (basicURL +\
		'&Primary=%s&Secondary=Status' % row_type, 'total'))))
	tbl.append (header_row)

	# build the data rows, with the Type/Area name followed by the counts
	# for each Status column:

	for t in row_keys:
		row = HTMLgen.TR ()
		row_label = row_cv.keyToName (t)
		row.append (HTMLgen.TD (HTMLgen.Bold (HTMLgen.Href (basicURL + \
			"&%s=%s&Primary=Status" % (row_type, row_label),
			row_label))))
		for s in status_keys:
			if cv_info.has_key (t):
				if cv_info [t].has_key (s):
					row.append (HTMLgen.TD (HTMLgen.Href (
						basicURL + \
						'&%s=%s&Status=%s' % (row_type,
						row_label, status_cv.keyToName (
						s)), cv_info[t][s].count()),
						align="right"))
				else:
					row.append (HTMLgen.TD (HTMLgen.BR()))
			else:
				row.append (HTMLgen.TD (HTMLgen.BR()))
		if cv_info.has_key (t):
			row.append (HTMLgen.TD (HTMLgen.Italic (HTMLgen.Bold (
				cv_info [t]['total'])), align="right"))
		else:
			row.append (HTMLgen.TD (HTMLgen.BR ()))
		tbl.append (row)

	# build the "# Unique TRs" line at the bottom which totals the numbers
	# for each Status column:

	row = HTMLgen.TR ()
	row.append (HTMLgen.TD (HTMLgen.Bold (HTMLgen.Italic (HTMLgen.Href (
		basicURL + '&Primary=Status&Secondary=%s' % row_type,
		'# Unique TRs')))))
	total = 0
	for s in status_keys:
		if all.has_key (s):
			row.append (HTMLgen.TD (HTMLgen.Italic (
				HTMLgen.Bold (all [s])), align = "right"))
			total = total + all [s]
		else:
			row.append (HTMLgen.TD (HTMLgen.BR ()))
	row.append (HTMLgen.TD (HTMLgen.Italic (HTMLgen.Bold (total)),
		align = "right"))
	tbl.append (row)

	return tbl

def getTemplateControls (field, suffix, tr_nr):
	tmp = Template.TemplateSet(field)
	if len(tmp) == 0:
		return ''

	op = 'doWhat%s' % suffix
	tpl = 'whatTemplate%s' % suffix
	go = 'GoButton%s' % suffix
	undo = 'UndoButton%s' % suffix
	tpl_set = 'templates%s' % suffix

	list = [
		'<SCRIPT>%s</SCRIPT>' % tmp.getJavascript (tpl_set),

		'<SELECT NAME=%s>' % op,
			'<OPTION VALUE="append"> Append',
			'<OPTION VALUE="insert"> Insert at **',
			'</SELECT>',

		'Using Template',
		tmp.getSelect(tpl),

		'''<INPUT TYPE=button VALUE=Go NAME="%s"
		onClick="doNotes(%s.options[%s.selectedIndex].value,
			%s.options[%s.selectedIndex].value
			, %s, %s, %s, '%s')">''' % \
				(go,
				op, op,
				tpl, tpl, 
				tpl_set, field, undo, tr_nr),

		'''<INPUT TYPE=button VALUE=Undo NAME=%s
		onClick="undoNotes(%s, %s)">''' % (undo, field, undo),
		]
	return string.join (list, '\n')

def getTableWithTemplates (
	flabel,		# field label as displayed to user
	fname,		# name of field, as internal to HTML code
	fvalue,		# value of the field
	fsuffix,	# suffix to use when creating HTML objects
	frows,		# number of rows in the textarea
	fcols,		# number of columns in the textarea
	tr_nr		# TR number
	):
	tbl = HTMLgen.TableLite (border=0, width="100%")
	tbl.append (HTMLgen.TR (
		HTMLgen.TD (HTMLgen.Href (HELP_URL % flabel,
				'%s:' % flabel) ),
		Raw_TD (getTemplateControls( \
			fname, fsuffix, tr_nr),
			align='right')
		))
	tbl.append (HTMLgen.TR (
		HTMLgen.TD (HTMLgen.Textarea (fvalue,
				rows = frows, cols = fcols, name = fname),
			colspan = 2) ))
	return tbl


#-SELF TESTING CODE---------------------------------------------------------

def self_test ():
	# Purpose: Typically WTS modules may be self-tested by executing them
	#	from the unix command line.  The TrackRec module is so involved,
	#	however, that we just test it from the web interface.  So, we
	#	need to print a reminder message when someone attempts to test
	#	it from the command line.
	# Returns: nothing
	# Assumes: Someone has tested the latest changes using the web
	#	interface.
	# Effects: see Purpose.
	# Throws: nothing

	print "Tested manually via web interface."


if __name__ == '__main__':		# if executed from command line,
	self_test()			# do a self test
