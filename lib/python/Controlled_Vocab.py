#!/usr/local/bin/python

# Name: Controlled_Vocab.py
# Purpose: implements the Controlled_Vocab class for WTS, a class which provides
#	a standard mechanism for working with controlled vocabulary fields.
# On Import, this is what happens...
#	initializes a global dictionary named 'cv' which is accessible by other
#	modules.  Its keys are the names of the WTS controlled vocabulary
#	tables.  The values stored in the dictionary are Controlled_Vocab
#	objects.  (This arrangement allows all the controlled vocabularies to be
#	loaded once.  Each module doesn't need to load its own copies as needed.
#	And, multiple modules can share a single copy)  Thus, we can look up the
#	key for 'Small' in the Size controlled vocabulary table by using:
#		Controlled_Vocab.cv ['CV_WTS_Size']['Small']
# Assumptions:
#	* REMOTE_USER environment variable identifies the current user
#	* Configuration has been imported
#	* Configuration.config is a dictionary which has keys for the
#	  controlled vocabulary table names which reference integer default
#	  key values (or if not a dictionary, has a __getitem__ method which
#	  provides this functionality)
#	* All WTS controlled vocabulary tables have the following format:
#		vocab name: initial uppercase letter, no spaces
#		table name: 'CV_WTS_' + vocab name
#		fields:
#			'_' + vocab name + '_key' --> integer key
#			vocab name (lowercase) + '_name' --> varchar(30)
#			vocab name (lowercase) + '_description' --> varchar(255)
#			vocab name (lowercase) + '_order' --> int
#	* The only exception to the above setup is CV_Staff, which has its
#	  differences hard-coded in this module.  (It needed to be different
#	  to handle a different ordering scheme.)
# Functions:
#	getCVtables (table name)
#	get_Controlled_Vocabs (table names)
#	self_test ()

import os
import copy
import wtslib
import Configuration
import string
import screenlib
import HTMLgen

## import Category -- loaded in the getCVtables() function to ease
##			dependencies (Category imports this module which
##			imports Category)

# Define:  When we use the term "string name" in this module, we are talking
#	about a string which has the name of an item in the controlled
#	vocabulary.  For example, in the 'CV_WTS_Size' controlled vocabulary,
#	some strings names would be:  'Small', 'Medium', 'Large'

# Classes and methods:

class Controlled_Vocab:
	# Concept:
	#	IS: a mapping of string names to database keys and vice versa,
	#		with one of the keys set as the default
	#	HAS: a set of string names mapped to database keys and vice
	#		versa, and a default key for this controlled vocabulary
	#	DOES: Operations are provided whereby a user of this class may
	#		look up the key for a string name, get a dictionary of
	#		keys mapped to strings, get a dictionary of string names
	#		mapped to keys, get a list of the string names in order,
	#		and validate a string of comma-separated string names.
	# Implementation:
	#	Methods:
	#		__init__ (table name)
	#		__getitem__ (item name)
	#               keyToName (key)
	#		default_key ()
	#		key_dict ()
	#		name_dict ()
	#		ordered_map ()
	#		ordered_names ()
	#		validate (string of string names)

	def __init__ (self,
		table_name	# name of the controlled vocabulary table (in
				# the database) which this Controlled_Vocab
				# object represents
		):
		# Purpose: create a new Controlled_Vocab object and load its
		#	corresponding info from the database
		# Returns: nothing
		# Assumes: db's SQL routines have been initialized, and
		#	that the REMOTE_USER environment variable has been
		#	defined
		# Effects: sets self.def_key to be the default key, and sets
		#	self.vocab and self.retired to be lists of tuples
		#	(each with a string name and its corresponding key).
		#	Initializes (to None) four object attributes which
		#	are computed only as needed (pc == pre-computed):
		#	self.pc_key_dict, self.pc_name_dict, and
		#	self.pc_ordered_names, self.pc_ordered_retired.
		# Throws: propagates wtslib.sqlError if there is a problem in
		#	executing the database queries
		# Example: CV = Controlled_Vocab ('CV_WTS_Size')

		# prepare a query to load in the information for the
		# specified controlled vocabulary.  Provide special handling
		# for CV_Staff, since it has a non-standard ordering and a
		# non-standard format.

		if table_name == 'CV_Staff':
			# get the table's default key from the environment

			self.def_key = os.environ ['REMOTE_USER']

			# sort by rough grouping (SA, SE, PI, editors, etc),
			# then alphabetically within each group.

			qry = '''select _Staff_key kee, staff_username txt,
					active
				from CV_Staff order by staff_username'''
		else:
			# get the table's default key from the system
			# configuration

			self.def_key = Configuration.config [table_name]

			# the field prefix is whatever is after the 'CV_WTS_'
			# in the table name, but with the first letter in
			# lowercase.  (except for the key field)

			field_prefix = string.lower (table_name[7]) + \
				table_name[8:]
			qry = 'select _' + table_name[7:] + '_key kee, ' + \
				field_prefix + '_name txt, active from ' + \
				table_name + ' order by ' + field_prefix + \
				'_order'

		# now, query the database.

		results = wtslib.sql (qry)

		# compile the results into two lists of tuples.  Each tuple
		# represents a single controlled vocabulary item:
		#	(string name value, integer key value)

		self.vocab = []		# active vocab terms
		self.retired = []	# retired vocab terms
		for row in results:
			if row['active']:
				self.vocab.append ( (row['txt'], row['kee']) )
			else:
				self.retired.append ((row['txt'], row['kee']))

		# These three fields are only computed if they are needed.  The
		# first two are dictionaries which provide a quick-access way
		# to map from names to keys and back.  The third is the list
		# of names, in the order specified in the database.

		self.pc_name_dict = None	# dict [names] --> keys
		self.pc_key_dict = None		# dict [keys] --> names
		self.pc_ordered_names = None	# ordered list of names
		self.pc_ordered_retired = None	# ordered list of retired names
		return


	def __getitem__ (self,
		item		# string; string name for which we are trying
				# to find a corresponding key
		):
		# Purpose: get the key corresponding to "item"
		# Returns: return the key corresponding to "item", or None if
		#	no key is defined for "item"
		# Assumes: nothing
		# Effects: see Returns.  If we haven't already computed the
		#	name-to-key dictionary (self.pc_name_dict), then
		#	we do so now.
		# Throws: nothing

		# if we haven't already computed the name to key dictionary,
		# then do it now...

		if self.pc_name_dict is None:
			self.name_dict ()	# computes and stores it

		lowercase_item = string.lower (item)
		if self.pc_name_dict.has_key (lowercase_item):
			return self.pc_name_dict [lowercase_item]
		else:
			return None


	def keyToName (self, key):
		# Purpose: see Returns
		# Returns: If key is found in this CV, return a string with the
		#       name (item) which corresponds to it.  Otherwise, just
		#       return None.
		# Assumes: nothing
		# Effects: causes self.pc_key_dict to be computed if it
		#       has not been already
		# Throws: nothing
		# Notes: nothing

		# if we haven't already computed the key to name dictionary,
		# then do it now...

		if self.pc_key_dict is None:
			self.key_dict ()        # computes and stores it

		if self.pc_key_dict.has_key (key):
			return self.pc_key_dict [key]
		else:
			return None


	def default_key (self):
		# Purpose: get the default key for this Controlled_Vocab object
		# Returns: the default key for this Controlled_Vocab object, or
		#	None if there is not one defined
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.def_key


	def key_dict (self):
		# Purpose: get a dictionary of keys mapped to string names
		# Returns: a dictionary of key -> string name pairs
		# Assumes: nothing
		# Effects: ensures that "self.pc_key_dict" contains a
		#	dictionary of keys mapped to string names, and then
		#	returns a copy of that dictionary.
		# Throws: nothing
		# Notes: The key_dict is only computed once, and then is
		#	remembered in "self.pc_key_dict".

		# if we have not yet computed the key to name dictionary,
		# then we need to compute it before we can return it.

		if self.pc_key_dict is None:
			self.pc_key_dict = {}
			for tuple in self.vocab + self.retired:
				self.pc_key_dict [tuple[1]] = tuple[0]
		return copy.deepcopy (self.pc_key_dict)


	def name_dict (self):
		# Purpose: get a dictionary of lowercase string names mapped
		#	to keys
		# Returns: a dictionary of lowercase string name -> key pairs
		# Assumes: nothing
		# Effects: ensures that "self.pc_name_dict" contains a
		#	dictionary of lowercase string names mapped to keys,
		#	and then returns a copy of that dictionary.
		# Throws: nothing
		# Notes: The name_dict is only computed once, and then is
		#	remembered in "self.pc_name_dict".

		# if we have not yet computed the name to key dictionary,
		# then we need to compute it before we can return it.

		if self.pc_name_dict is None:
			self.pc_name_dict = {}
			for tuple in self.vocab + self.retired:
				self.pc_name_dict [ \
					string.lower (tuple[0]) ] = tuple[1]
		return copy.deepcopy (self.pc_name_dict)


	def ordered_map (self, get_retired = 0):
		# Purpose: get a list of (key, string name) tuples in order
		# Returns: set of active vocab items if get_retired == 0,
		#	or a set of retired vocab items otherwise
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		if get_retired:
			return copy.deepcopy (self.retired)
		return copy.deepcopy (self.vocab)


	def ordered_names (self, get_retired = 0):
		# Purpose: get a list of string names in proper order
		# Returns: set of active vocab items if get_retired == 0,
		#	or a set of retired vocab items otherwise
		# Assumes: nothing
		# Effects: Builds self.pc_ordered_name or
		#	self.pc_ordered_retired as needed
		# Throws: nothing
		# Notes: We only compute the lists of string names once, and
		#	then remember them for use later.

		if get_retired:
			if self.pc_ordered_retired is None:
				self.pc_ordered_retired = []
				for (item, key) in self.ordered_map(1):
					self.pc_ordered_retired.append (item)
			return copy.deepcopy (self.pc_ordered_retired)
		else:
			if self.pc_ordered_names is None:
				self.pc_ordered_names = []
				for (item, key) in self.ordered_map (0):
					self.pc_ordered_names.append (item)
			return copy.deepcopy (self.pc_ordered_names)


	def validate (self,
		names		# string; comma-separated set of string names
		):
		# Purpose: look up the corresponding key for each string name
		#	in "names"
		# Returns: a tuple containing two parallel lists and a boolean
		#	flag indicating whether any errors were found.  This
		#	tuple can be defined as follows:
		#		(key list, error list, error flag)
		#	where:
		#		for the i-th string name in "names":
		#			if we can find a key for names [i]:
		#				key list [i] = the key
		#				error list [i] = None
		#			else:
		#				key list [i] = None
		#				error list [i] = error message
		#		The error flag is 0 if no errors were found, or
		#		1 if at least one error was found.
		# Assumes: nothing
		# Effects: Tries to match the string names in "names" to keys
		#	in this Controlled_Vocab object.  Returns a tuple of
		#	information as defined in the Returns section above.
		# Throws: nothing

		keys = []		# list of keys
		errors = []		# list of error messages
		error_flag = 0		# assume no errors yet

		# split the names string into a list of separate lowercase
		# names

		name_list = string.split (string.lower (names), ',')

		# get a dictionary of name -> key mappings and a list of the
		# valid names

		mapping = self.name_dict()

		# try to look up each name.  fill in keys and errors as
		# described in the comments above.

		for name in name_list:
			no_spaces = string.strip(name)
			if mapping.has_key (no_spaces):
				keys.append (mapping [no_spaces])
				errors.append (None)
			else:
				keys.append (None)
				errors.append (no_spaces + \
					' was not recognized.')
				error_flag = 1
		return (keys, errors, error_flag)


	def pickList (self, selectedTerms = [], showAll = 0):
		# Purpose: build a list of strings for use in a selection box
		# Returns: list of strings
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing
		# Notes: puts all active terms for this CV in order in the
		#	list.  If any selectedTerms are retired, then we also
		#	include a divider line and those terms in proper
		#	order, or if showAll is non-zero then we include all
		#	retired CV terms below a divider line.

		active = self.ordered_names(0)
		retired = []
		if showAll:
			retired = self.ordered_names(1)
		elif len(selectedTerms) > 0:
			for term in self.ordered_names(1):
				if term in selectedTerms:
					retired.append (term)
		if len(retired) > 0:
			active = active + [ '----------' ] + retired
		return active

### End of Class: Controlled_Vocab ###

#-MODULE FUNCTIONS-------------------------------------------------

def getCVtables (
	table_name	# string; name of the ctrl vocabulary table in the db
	):
	# Purpose: create and return an HTML table to represent the controlled
	#	vocabulary specified by 'table_name'
	# Returns: string
	# Assumes: the wtslib.sql() function can query the wts database okay
	# Effects: queries the database
	# Throws: propagates any exceptions raised by wtslib.sql()

	columns = []	# list of strings, each is a column heading
	results = []	# list of dictionaries, each has info for one CV term

	# we need special handling for the CV_Staff table since it
	# has a non-standard ordering and a non-standard format

	if table_name == 'CV_Staff':
		columns = [ 'UserName' ]
		qry = '''select staff_username UserName, active
			from CV_Staff
			order by staff_username'''
		results = wtslib.sql (qry)		# do the query

	# We also need special handling for the CV_WTS_Category table, since
	# we need to display a couple of extra columns.

	elif table_name == 'CV_WTS_Category':
		import Category

		columns = [ 'Value', 'Description', 'E-Mail', 'Staff',
				'Area', 'Type' ]
		qry = '''select category_name Value, category_description
				Description, active
			from CV_WTS_Category
			order by category_order'''
		results = wtslib.sql (qry)		# do the query

		# now, load the extra information for each Category, so we can
		# add the e-mail and staff info to each row...

		for row in results:
			cat = Category.Category (row ['Value'])
			row ['E-Mail'] = cat.getEmail ()
			row ['Staff'] = cat.getStaff ()
			row ['Area'] = cat.getArea ()
			row ['Type'] = cat.getType ()
			for field in [ 'E-Mail', 'Staff', 'Area', 'Type']:
				if row [field] == '':
					row [field] = 'None'	# cell filler
	else:
		# the field prefix (for all except the key field) is
		# a lowercase version of whatever is after the
		# 'CV_WTS_' in the table name.

		field_prefix = string.lower (table_name[7]) + \
			table_name[8:]
		qry = '''select %s_name Value, %s_description Description,
				active
			from %s
			order by %s_order''' % (field_prefix, field_prefix,
				table_name, field_prefix)
		columns = [ 'Value', 'Description' ]
		results = wtslib.sql (qry)		# do the query
	
	# build a table of active terms followed by a table of retired terms

	cvTbl = HTMLgen.TableLite (border=0)
	cvRow = HTMLgen.TR(valign="top")

	table_str = ''
	for (is_active, table_title) in \
			[ (1, 'Current Terms'), (0, 'Retired Terms') ]:

		tbl = HTMLgen.TableLite (border = 1, cell_padding = 5)

		header_row = HTMLgen.TR ()
		for col in columns:
			header_row.append (HTMLgen.TH (col))
		tbl.append (header_row)

		empty = 1
		for row in results:
			if row['active'] == is_active:
				empty = 0
				data_row = HTMLgen.TR ()
				for col in columns:
					data_row.append(HTMLgen.TD (row[col]))
				tbl.append (data_row)
		if empty == 0:
			cvRow.append (HTMLgen.TD (HTMLgen.BR(),
					HTMLgen.Italic (table_title),
					HTMLgen.P(),
					tbl))
			cvRow.append (HTMLgen.TD (width=10))
	cvTbl.append (cvRow)
	return str(cvTbl)


def get_Controlled_Vocabs (
	table_names	# list of strings, each of which is the name of a
			# controlled vocabulary table for which we want to
			# build a Controlled_Vocab object
	):
	# Purpose: get a dictionary which maps each table name to its
	#	Controlled_Vocab object
	# Returns: return the dictionary described in Purpose
	# Assumes: each string in "table_names" is a valid controlled vocabulary
	#	table name in the database
	# Effects: see Purpose
	# Throws: propagates wtslib.sqlError if there is a problem in
	#	executing the database queries
	# Example: doing get_Controlled_Vocabs (['CV_WTS_Size', 'CV_WTS_Type'])
	#	yields:
	#		{ 'CV_WTS_Size' : Controlled_Vocab object for sizes,
	#		  'CV_WTS_Type' : Controlled_Vocab object for types }

	dict = {}

	# this should probably be speeded up by doing all the queries in
	# one batch, rather than a sequence of independent ones.  If it does
	# not turn out to be a real bottleneck, though, let's wait for now.

	for table_name in table_names:
		dict [table_name] = Controlled_Vocab (table_name)
	return dict


#-GLOBALLY AVAILABLE CONTROLLED VOCABULARY INFO-----------------------------

# The dictionary "cv" will contain a mapping from each controlled vocabulary
# table name to its associated Controlled_Vocab object.  This will be global
# and can be accessed by other modules importing this one.

cv = get_Controlled_Vocabs ( [ 'CV_WTS_Area', 'CV_WTS_Type', 'CV_Staff', \
	'CV_WTS_Size', 'CV_WTS_Status', 'CV_WTS_Priority', 'CV_WTS_Category' ] )


#-SELF TESTING CODE---------------------------------------------------------

def self_test ():
	# Purpose: test this module
	# Returns: nothing
	# Assumes: nothing
	# Effects: sends to stdout the results of creating a Controlled_Vocab
	#	object and invoking each method, and of calling the various
	#	module functions.
	# Throws: whatever exceptions propagate from the various methods and
	#	functions in this module.

	global cv
	create_Include_File ('CV_WTS_Status', 'CV_WTS_Status.html', 'Status')
	cv1 = Controlled_Vocab ('CV_WTS_Size')
	print 'Size:'
	print 'default key = ', cv1.default_key()
	print 'name_dict   = ', cv1.name_dict()
	print 'ordered map = ', cv1.ordered_map()
	print 'ordered name= ', cv1.ordered_names()
	print "validate... ['small', 'medium', 'large', 'huge', 'mega', 'tiny']"
	print cv1.validate ('small, medium, large, huge, mega, tiny')
	print 'Area key dict    = ', cv ['CV_WTS_Area'].key_dict()
	print 'Size key dict    = ', cv ['CV_WTS_Size'].key_dict()

if __name__ == '__main__':		# if executed from command line,
	self_test()			# do a self test
