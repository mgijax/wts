#!/usr/local/bin/python

# Name:		Configuration.py
# Purpose:	implements the Configuration class for WTS.  This class provides
#		a standard mechanism for getting system configuration info, such
#		as database login information, etc.
# On Import:
#	* initializes db's SQL routines
#	* instantiates a Configuration object named "config" which all
#	  modules can access for config info (saves reloading the info each
#	  time we need it).  Note that this object is global.  If a module
#	  needs to ensure a static Configuration object, it can instantiate
#	  its own separate one.
#	* reads basic (bootstrap) configuration info from a text file named
#	  wts.cfg by default, then contacts the database and gets the rest
#	  from the WTS_Config table.
#	* adds the WTS library directory to the python path
# Notes:
#	* The main wts directory is the parent directory for a single WTS
#	  installation.  Several other directories such as bin, cgi, html,
#	  and lib exist under the main wts directory.
#
#	* The configuration file is assumed to be named wts.cfg.  We begin
#	  looking in the current directory for it, and continue searching
#	  upward into parent directories until we find it.
#
#	* The configuration file may contain blank lines and may contain
#	  comments (lines on which the first non-blank character is #).  Other
#	  lines should define a fieldname followed by a value.  Any amount
#	  of blank space is allowed before the fieldname, between it and the
#	  value, and after the value.  For readability, it is recommended that
#	  you put the fieldname as the first item on the line, then a single
#	  tab, then the value.  Neither fieldname nor value may contain
#	  whitespace.
#
#	* The configuration file must define the following fields to allow
#	  database access:  DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD.
#	  The configuration file must also define the diagnostics directory:
#	  DIAG_DIR.
#
#	* After reading the database-related parameters from the configuration
#	  file, WTS will access the WTS_Config table in the database to get
#	  the remaining configuration parameters.  (list in the class header)
#
#	* Four fields must be present in WTS_Config:
#		_Config_Name	varchar(20)	name of the parameter
#		int_value	int		optional integer value
#		string_value	varchar(255)	optional string value
#		date_value	datetime	optional datetime value
#	  In each record, exactly one of the above value fields must be
#	  filled in.

import os
import regex
import string
import sys
# import db	(imported below, in the refresh() method)

#--GLOBAL VARIABLE (treat as a constant)---------------------------------

error = "Configuration.error"		# standard exception to be raised by
					# this module

#--FUNCTIONS------------------------------------------------------------

def getWtsPath ():
	fp = os.popen ('pwd')
	current_dir = fp.readline()
	fp.close()
	pos = string.find (current_dir, '/wts')
	return current_dir[:pos+4]

#--CLASSES AND METHODS---------------------------------------------------

class Configuration:
	# Concept:
	#	IS: a set of parameters used to configure WTS program files
	#	HAS: several keys which are mapped to values, namely:
	#		Key		Value
	#		----------	-----
	#		_TR_key		last assigned integer TR key
	#		baseUnixPath	string path to project directory
	#				hierarchy
	#		baseURL		string for HTTP pointer to baseUnixPath
	#		CV_WTS_Area	default integer key for Area ctrl vocab
	#		CV_WTS_Category	default integerkey for Categories
	#		CV_WTS_Priority	default integer key for Priority ctrl
	#				vocab
	#		CV_WTS_Size	default integer key for Size ctrl vocab
	#		CV_WTS_Status	default integer key for Status ctrl
	#				vocab
	#		CV_WTS_Type	default integer key for Type ctrl vocab
	#	DOES: values for the various keys may be looked up dictionary-
	#		style (using []), also provides a method to refresh ()
	#		the current configuration
	# Implementation:
	#	Methods:
	#		__init__ () 	__getitem__ (parameter name)
	#		keys () 	refresh ()

	def __init__ (self):
		# Purpose: create and initialize a new Configuration object
		# Returns: nothing
		# Assumes: see module Notes above for a discussion of file
		#	format, location, and specification
		# Effects: Creates and initializes a new Configuration object
		#	with values from the configuration file and then from
		#	the WTS_Config table in the database.  Since this
		#	method calls refresh(), it also ensures that db's
		#	SQL routines have been initialized.
		# Throws: propagates from the refresh() method:
		#	1. Configuration.error if we cannot find the
		#	configuration file, or if we find it but cannot parse
		#	a line in it; 2. sybase.connection if something goes
		#	wrong in initializing db's SQL routines;
		#	3. sybase.error if there is a problem with the SQL
		#	statements we try to execute.

		# self.pathname is a string which identifies the path to the
		# configuration file.  Look up through the directory levels
		# until we find the right file.

		self.pathname = 'wts.cfg'
		while not os.path.exists (self.pathname):
			self.pathname = '../' + self.pathname

		# initialize the configuration

		self.configuration = {}		# maps configurable item name
						# (string) to its current value
						# (string or int)

		# now, pass control to the refresh method which will fill
		# in the configuration values

		self.refresh ()
		return


	def __getitem__ (self,
		parm_name	# string name of the configuration parameter
				# whose value we should return
		):
		# Purpose: get the value corresponding to the given parm_name
		# Returns: the value corresponding to parm_name, which may be
		#	either an integer or string, depending on the parameter
		# Assumes: nothing
		# Effects: see Returns
		# Throws: a KeyError exception if parm_name is not a valid
		#	parameter name in this Configuration object.

		# try to look up the value of the requested parameter

		try:
			return self.configuration [parm_name]
		except:
			# the standard Python exception KeyError is perfectly
			# appropriate for this situation.  We just provide a
			# cleaner explanation in the return value.

			raise KeyError, 'Config could not find: ' + parm_name


	def keys (self):
		# Purpose: get a list of the keys (parameter names) defined in
		#	this object
		# Returns: a list of strings, each of which is a key (parameter
		#	name) with a value defined in this Configuration object
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.configuration.keys ()


	def refresh (self):
		# Purpose: clear all current parameters in this Configuration
		#	object and reload them.
		# Returns: nothing
		# Assumes: see module's Notes comments regarding configuration
		#	file format, location, and specifications
		# Effects: clears all current configuration parameters and
		#	reloads the config information from the configuration
		#	file and then from the WTS_Config table in the database
		# Throws: 1. Configuration.error if we cannot find the
		#	configuration file, or if we find it but cannot parse
		#	a line in it; 2. sybase.connection if something goes
		#	wrong in initializing db's SQL routines;
		#	3. sybase.error if there is a problem with the SQL
		#	statements we try to execute.

		# (re-) initialize the configuration

		self.configuration = {}

		# read the configuration file

		try:
			fp = open (self.pathname, 'r')
			lines = fp.readlines()
			fp.close ()
		except:
			raise error, 'Config could not find: %s' % self.pathname

		# set up regular expressions to look for blanks, comments, and
		# to parse the standard line format:

		blank = regex.compile (
			'^[ \t]*$')		# full line of spaces & tabs
		comment = regex.compile (
			'^[ \t]*'		# only spaces & tabs before a...
			'#')			# comment indicator
		standard = regex.compile (
			'^[ \t]*'	# any number of leading spaces & tabs
			'\([^ \t]*\)'	# group 1 = any non-blanks for name
			'[ \t]*'	# any number of separating spaces & tabs
			'\([^ \t\n]*\)'	# group 2 = any non-blanks for value
			'[ \t]*$')	# any trailing blanks are okay

		# parse the lines we read to get & store the config parameters

		for line in lines:
			if (blank.match (line) >= 0) or \
				(comment.match (line) >= 0):
				# skip blanks & comments
				continue
			elif standard.match (line) >= 0:
				name, value = standard.group (1, 2)
				self.configuration [name] = value
			else:
				raise error, 'Cannot parse config line: %s' % \
					line

		# add the library directories to the path:

		dirs = string.split (self.configuration['LIBDIRS'], ':')
		dirs.reverse()
		for dir in dirs:
			if dir not in sys.path:
				sys.path.insert (0, dir)

		# get the database module

		import db

		# now, contact the database to get the rest of the
		# configuration information.  each of the DB fields below must
		# have been defined in the configuration text file.  If an
		# exception occurs in login, just let it propagate.  (We want
		# to have it be as specific as possible, which it already is
		# when it comes from db)

		db.set_sqlLogin (self.configuration ['DB_USER'],
			self.configuration ['DB_PASSWORD'],
			self.configuration ['DB_SERVER'],
			self.configuration ['DB_DATABASE'])

		# run a query to get the configuration info

		qry = '''select _Config_Name, int_value, string_value,
			date_value from WTS_Config'''
		results = db.sql (qry, 'auto')

		# now, go through and assign whichever value is filled
		# in for the corresponding _Config_Name.

		for row in results:
			if (row ['int_value'] is not None):
				self.configuration [ row ['_Config_Name'] ] = \
					row ['int_value']
			elif (row ['string_value'] is not None):
				self.configuration [ row ['_Config_Name'] ] = \
					row ['string_value']
			elif (row ['date_value'] is not None):
				self.configuration [ row ['_Config_Name'] ] = \
					row ['date_value']
			else:
				self.configuration [ row ['_Config_Name'] ] = \
					None
		return

### End of Class: Configuration ###

#--CODE EXECUTED ON IMPORT-----------------------------------------------

config = Configuration ()		# instantiate a config object
