# Name:		wtsWrap.py
# Purpose:	provide classes as a wrapper over a WTS instance, making
#		certain pieces of its command-line interface available from
#		Python

import os
import string
import tempfile
import runCommand

error = 'wtsWrap.error'		# standard exception for the module

class WTS:
	# IS:	an instance of the WTS product
	# HAS:	a unix path, denoting where the WTS product is installed
	# DOES:	sets and gets values for fields of tracking records, provides
	#	simple querying by Title
	# Public Methods:
	#	__init__ (self, wts_cmd, environ)
	#	addNote (self, TR, note)
	#	addNoteFromFile (self, TR, path)
	#	newMinimal (self, title, status)
	#	getField (self, TR, fieldname)
	#	getProjectDir (self, TR)
	#	getStaff (self, TR)
	#	getStatus (self, TR)
	#	queryByTitle (self, query_string)
	#	setField (self, TR, fieldname, fieldvalue)
	# Notes:
	#	Each time we expect a TR as a parameter, we only want the
	#	integer portion.  (Do not include the 'TR' prefix.)  In the
	#	event that the caller specifies a TR which does not exist in
	#	the database, we raise 'error' with the value 'Cannot find
	#	TR in database'.
	# Example:
	#	wts = WTS ('/mgi/all/wts/admin/wts')
	#	try:
	#		trs = wts.queryByTitle ('schema')
	#		for tr in trs:
	#			print tr, tr.getField (tr, 'Title')
	#	except error, message:
	#		print 'An error occurred: %s' % error
	#		print message
	#		sys.exit(-1)

	def __init__ (self,
		wts_cmd,	# string; path to the WTS cmd line executable
		environ = {}	# dictionary of environment variables to be
				# defined when the WTS command-line is
				# executed
		):
		# Purpose: constructor
		# Returns: nothing
		# Assumes: nothing
		# Effects: instantiates a WTS object
		# Throws: 'error' if 'wts_cmd' does not exist

		self.command = wts_cmd
		self.environ = environ
		if not os.path.exists (self.command):
			self.raiseException (error,
				'%s does not exist' % self.command)
		return

	def addNote (self,
		TR,		# string or integer; TR number
		note		# string; the note to add to TR's Prog Notes
		):
		# Purpose: add the given 'note' new Progress Note for the
		#	specified 'TR'
		# Returns: contents of stdout produced by the WTS command-line
		#	in response to that action
		# Assumes: we can write to a temp file
		# Effects: updates the tracking record with the given 'TR'
		#	number
		# Throws: propagates IOError if we cannot write a temp file;
		#	propagates 'error' with the contents of stderr as
		#	its value if the WTS command line fails

		path = tempfile.mktemp()
		fp = open (path, 'w')				# create file
		fp.write (note)
		fp.close ()
		stdout = self.addNoteFromFile (TR, path)	# add note
		os.remove (path)				# remove file
		return stdout

	def addNoteFromFile (self,
		TR,		# string or integer; TR number
		path		# string; full path to the file
		):
		# Purpose: add the contents of the file at 'path' as a new
		#	Progress Note for the specified 'TR'
		# Returns: contents of stdout produced by the WTS command-line
		#	in response to that action
		# Assumes: 'path' is readable
		# Effects: updates the tracking record with the given 'TR'
		#	number
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		stdout = self.execute ('--addNoteFromFile %s %s' % (TR, path))
		return stdout

	def newMinimal (self,
		title,		# string; value for the Title field
		status		# string; value for the Status field
		):
		# Purpose: create a new TR with the given 'title' and
		#	'status', with defaults for all other fields
		# Returns: contents of stdout produced by the WTS command-line
		#	in response to that action
		# Assumes: 'path' is readable
		# Effects: updates the database by creating a new TR
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		stdout = self.execute ('--newMinimal "%s" "%s"' % (title,
			status))
		return stdout

	def getField (self,
		TR,		# string or integer; TR number
		fieldname	# string; name of the field
		):
		# Purpose: get the contents of the specified 'fieldname' for
		#	the specified 'TR'
		# Returns: contents of stdout produced by the WTS command-line
		#	(this will be the value of the specified field)
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails
		# Notes: For valid fieldnames, look at the keys of the 
		#	NAME_TO_DB dictionary in WTS's TrackRec.py module

		stdout = self.execute ('--getField %s "%s"' % (TR, fieldname))
		return stdout

	def getProjectDir (self,
		TR		# string or integer; TR number
		):
		# Purpose: get the path to the project directory for the
		#	specified 'TR'
		# Returns: contents of stdout produced by the WTS command-line
		#	(this will be the desired path), with any leading and
		#	trailing whitespace removed
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		stdout = self.execute ('--dir %s' % TR)
		return string.strip(stdout)

	def getStaff (self,
		TR		# string or integer; TR number
		):
		# Purpose: get the contents of the Staff field for the
		#	specified 'TR'
		# Returns: string; a comma-separated set of staff members
		#	currently assigned to the specified 'TR'
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		return self.getField (TR, 'Staff')

	def getStatus (self,
		TR		# string or integer; TR number
		):
		# Purpose: get the contents of the Status field for the
		#	specified 'TR'
		# Returns: string; the Status which is currently assigned to
		#	the specified 'TR'
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		return self.getField (TR, 'Status')

	def queryByTitle (self,
		inTitle		# string to look for in the Title field
		):
		# Purpose: get a set of TR numbers which contain the string
		#	specified in 'inTitle' as part of the Title field
		# Returns: list of strings, each of which is the TR number
		#	of a tracking record with 'inTitle' in the Title field
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		stdout = self.execute ('--queryTitle %s' % inTitle)
		return string.split(stdout, ',')

	def setField (self,
		TR,		# string or integer; TR number
		fieldname,	# string; name of the field
		fieldvalue	# string; new value of the field
		):
		# Purpose: set the value of the specified 'fieldname' for
		#	the specified 'TR' to be the given 'fieldvalue'
		# Returns: contents of stdout produced by the WTS command-line
		# Assumes: nothing
		# Effects: nothing
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails.  For example, if the
		#	TR has already been locked for editing by someone
		#	else, we effectively execute:
		#		raise error, 'Tracking Record TR<TR #> was ' +
		#		'already locked by <user> on <datetime>'

		stdout = self.execute ("--setField %s '%s' '%s'" % (TR,
			fieldname, fieldvalue))
		return string.strip(stdout)

	###--- Private Methods ---###

	def execute (self,
		args		# string; any command-line arguments for wts
		):
		# Purpose: PRIVATE method, used by other methods to invoke the
		#	WTS command-line interface
		# Returns: contents of stdout generated when the command-line
		#	interface is run with the given 'args'
		# Assumes: nothing
		# Effects: vary depending on 'args' -- may query or update the
		#	database instance associated with the WTS instance
		# Throws: propagates 'error' with the contents of stderr as
		#	its value if the command fails

		stdout, stderr, exitcode = runCommand.runCommand (
			'%s %s' % (self.command, args),
			self.environ
			)
		if exitcode:
			self.raiseException (error, stderr)
		return stdout

	def raiseException (self,
		exception,	# string; the exception to raise
		message		# string; the message to pass back with it
		):
		# Purpose: raise the given 'exception' and pass back the
		#	given 'message' with it
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: 'exception'
		# Notes: Subclasses can override this as needed to map
		#	wtsWrap.error to their own exceptions

		raise exception, message

###--- END class WTS ---###
