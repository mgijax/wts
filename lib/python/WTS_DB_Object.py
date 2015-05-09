#!/usr/local/bin/python

# Name:		WTS_DB_Object.py
# Author:	Jon Beal
# Purpose:	Implements the WTS_DB_Object class for WTS

import copy
import wtslib
import Configuration

#--GLOBAL VARIABLE (constant)----------------------------------------

# "error" exception is the standard exception raised by this module:

error = "WTS_DB_Object.error"
	# when "error" is raised, the value string returned will be a text
	# explanation of the problem encountered.  Currently there are two
	# possible problems for which this exception is raised:
	# 	'Cannot allocate new key because no key name was specified.'
	# and:
	#	'Current object already has a key.'

#--CLASSES-----------------------------------------------------------

class WTS_DB_Object:
	# Concept:
	#	IS:	A WTS_DB_Object is one conceptual type of record stored
	#		in WTS database.  (currently tracking records and
	#		requests)  This class concentrates on the concept,
	#		rather than on the implementation.  (A WTS_DB_Object is
	#		a single conceptual record, regardless of how many
	#		physical tables and how many records in each table
	#		actually contain its data.)
	#	HAS:	five fields including:
	#			* a dictionary of its data
	#			* an ordered list of its attributes (the same
	#			  as the keys of the data dictionary, but in
	#			  the order they should appear in a text file)
	#			* a list of which attributes are required to
	#			  have values
	#			* an integer key value
	#			* the name used to look up the next such key in
	#			  the database.
	#	DOES:	methods are provided to return a dictionary of the
	#		keys and values in this object, to allocate a new key
	#		from the database and set the appropriate object
	#		attribute, to list either all the attribute names or
	#		only those which are required, and to set values of
	#		attributes in the object's data
	# Implementation:
	#	The data for the conceptual object (the WTS_DB_Object) is all
	#	stored in self.data, a dictionary of object attribute names and
	#	values.  The other self.* instance variables give information
	#	about that data and about the object itself, including the
	#	lists of attribute names (all or required), key value, and key
	#	name.
	#	The WTS_DB_Object class is abstract.  It was designed to provide
	#	a few very basic methods which would be common to all conceptual
	#	record types in the database.  Subclasses should provide their
	#	own __init__ method which first calls the WTS_DB_Object's
	#	__init__ and then proceeds with whatever customization of the
	#	object is needed, including defining values for self.key_name,
	#	self.attributes, self.required_attributes, and possibly
	#	self.key_value if the key is known.  They should also override
	# 	the set_Defaults method to call the WTS_DB_Object one and then
	#	set any subclass-specific defaults.  Almost certainly a
	#	subclass will want to define "save" and "load" methods to put
	#	their information in the database and get it back out again.
	#	Subclasses may also find it useful to define methods for
	#	displaying themselves and for validating their contents.
	#	Methods:
	#		__init__ ()		required_Attributes ()
	#		all_Attributes ()	set_Defaults ()
	#		allocate_Key ()		set_Values (dict)
	#		dict ()

	def __init__ (self):
		# Purpose: create and initialize a new WTS_DB_Object object
		# Returns: nothing
		# Assumes: a subclass of WTS_DB_Object will fill in the pieces
		#	of data described above in the class comments.
		# Effects: see Purpose.
		# Throws: nothing

		self.data = {}		# the actual data in the database
					# object -- maps fieldnames to field
					# values.

		self.attributes = []	# list of fieldnames in the database
					# object (same as self.data.keys ()),
					# but in the order they should appear
					# when saved to an external file.

		self.required_attributes = []	# list of fieldnames which must
						# have values for this database
						# object to be valid.

		self.key_name = ''	# name of the _Config_Name key  to use
					# when looking up the last key value
					# assigned for database objects from the
					# WTS_Config table in the database.

		self.key_value = None	# current integer database key for this
					# database object.

		# inheriting classes should call this __init__ routine from
		# within their own, and then do any class-specific setup there
		# (for instance, setting up the five items above)
		return


	def all_Attributes (self):
		# Purpose: get a list of fieldnames in this object
		# Returns: a list of strings, each of which is the name of one
		#	field in this object.  The list is in the order in which
		#	the fields should be displayed, if displayed in a
		#	sequential list.
		# Assumes: nothing
		# Effects: returns a copy of the "attributes" list in self
		# Throws: nothing
		# Notes: These object fieldnames do not specify instance
		#	variables of the object.  They are the fieldnames of
		#	data contained in the object's "data" dictionary.

		return copy.deepcopy (self.attributes)


	def allocate_Key (self):
		# Purpose: allocate and store a new key for the current object
		# Returns: nothing
		# Assumes: The last key value assigned for this type of object
		#	is found in the WTS_Config table.  The _Config_Name
		#	field which matches self.key_name specifies which record
		#	in the table, and the last key assigned is stored in
		#	the int_value column.
		# Effects: Increments the entry for self.key_name in WTS_Config,
		#	and stores the new key value in self.key_value.
		# Throws: 1. WTS_DB_Object.error if self.key_name has not been
		#	set.  2. WTS_DB_Object.error if self.key_value already
		#	has a value (so this object already has a key)
		#	3. IndexError if self.key_name does not appear in the
		#	_Config_Name field of WTS_Config.
		# Notes: Goes to the WTS_Config table in the database, reads
		#	the last key value assigned to the given key name
		#	(self.key_name), increments it, stores it back in the
		#	table and in self.key_value.

		# if we don't have a key name, then bail out

		if len (self.key_name) == 0:
			raise error, 'Cannot allocate new key ' + \
				'because no key name was specified.'

		# if we already have a key value defined for this object,
		# then bail out

		if self.key_value <> None:
			raise error, 'Current object already has a key.'

		# otherwise, we need to get the last assigned key, increment
		# it, store it, and save it back to the database.  All this
		# should be done in one step, rather than the current three,
		# if we are to ensure that unique key values are assigned to
		# objects.  (in case two people are saving the same type of
		# object at the same moment)

		qry = '''select int_value
			from WTS_Config
			where _Config_Name='%s' ''' % self.key_name
		result = wtslib.sql (qry)

		self.key_value = result[0]['int_value'] + 1

		qry = '''update WTS_Config
			set int_value = %d
			where _Config_Name = '%s' ''' % (self.key_value,
				self.key_name)
		result = wtslib.sql (qry)

		# sub-classes may call this method in the parent class, and
		# then use self.key_value to form a key that the user can
		# see (and to put in self.data)
		return


	def dict (self):
		# Purpose: get the current dictionary of object fieldnames and
		#	their associated values
		# Returns: a dictionary with object fieldnames as keys which
		#	reference their associated values
		# Assumes: nothing
		# Effects: creates and returns a copy of self.data, the actual
		#	dictionary in which object fieldnames are stored
		# Throws: nothing

		return copy.deepcopy (self.data)


	def required_Attributes (self):
		# Purpose: get a list of the object fieldnames which are
		#	required to have values for this to be considered a
		#	complete valid object
		# Returns: a list of strings, each of which is the name of an
		#	object fieldname which is required to have a value
		# Assumes: nothing
		# Effects: makes and returns a copy of the list
		#	self.required_attributes
		# Throws: nothing

		return copy.deepcopy (self.required_attributes)


	def set_Defaults (self):
		# Purpose: reset the default values for this object
		# Returns: nothing
		# Assumes: nothing
		# Effects: resets self.data and self.key_value to effectively
		#	erase the object's data and its key.
		# Throws: nothing

		self.data = {}			# no data
		self.key_value = None		# no key

		# subclasses should define a set_Defaults method which calls
		# this one to set the basic WTS_DB_Object defaults, and then 
		# it can set those specific to the subclass type.
		return


	def set_Values (self,
		dict		# dictionary with object fieldnames as keys
				# which refer to the values we would like to
				# set for those fieldnames in this object
		):
		# Purpose: sets the data values for this object to be those
		#	specified in dict.
		# Returns: nothing
		# Assumes: nothing
		# Effects: For each key of dict, get its value from dict.  Set
		#	that value for the corresponding object fieldname (in
		#	the WTS_DB_Object)
		# Throws: nothing
		# Notes: This method only changes values in the object itself,
		#	not in the database.
		# Example: Say A is a WTS_DB_Object and
		#		A.dict () = { 'field1' : 23, 'field2' : 'val' }
		#	If we then do:
		#		A.set_Values ({'field1' : 43, 'field3' : 4})
		#	Then:
		#		A.dict () = { 'field1' : 43, 'field2' : 'val',
		#				'field3' : 4 }

		for key in dict.keys():
			self.data [key] = dict[key]

### End of Class: WTS_DB_Object ###

#-SELF TESTING CODE---------------------------------------------------------

# This module cannot be self-tested from the command-line, as it is only meant
# to be an abstract class.  We should not instantiate WTS_DB_Objects, but
# rather objects of classes which derive from it.
