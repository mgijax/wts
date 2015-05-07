#!/usr/local/bin/python

# Name:		Category.py
# Purpose:	provides the Category class for Routing in WTS
# Assumes:	db's SQL routines have been initialized.
#		The controlled vocabularies are available at Controlled_Vocab.cv

import Configuration
import Controlled_Vocab
import wtslib
import Set
import regex

# ---------- globals: ----------
						# get cntrl vocab objects for:
STAFF_CV = Controlled_Vocab.cv ['CV_Staff']		# staff members
CATEGORY_CV = Controlled_Vocab.cv ['CV_WTS_Category']	# categories

TRUE = 1
FALSE = 0

# ---------- exceptions: ----------

error = "Category.error"

exc_BadCategory = "Unrecognized Category name: %s"	# %s = name of Category

# ---------- classes: ----------

class Category:
	# Concept:
	#	IS: a named group of staff members to which a tracking
	#		record may be routed
	#	HAS: a unique integer identifier (key), a unique name, a
	#		description, a string of e-mail addresses, and a
	#		string of staff members
	#	DOES: allows the user to get and set various attributes of the
	#		Category object, then save the changes to the database.
	# Implementation:
	#	The Category class has several instance variables, one for each
	#	attribute we need to track:
	#		self.key - integer; key into table CV_WTS_Category
	#		self.name - string; name of this category
	#		self.email - string; comma-separated set of e-mail
	#			addresses to be notified when a tracking
	#			record is routed to this category
	#		self.description - string; text description of this
	#			Category
	#		self.staff - Set; Set of staff member keys who should be
	#			added to the Staff list for a tracking
	#			record which is routed to this Category
	#		self.area - string; name of the default Area for
	#			tracking records routed to this category
	#		self.type - string; name of the default Type for
	#			tracking records routed to this Category
	#		self.status - string; name of the default Status for
	#			tracking records routed to this Category
	#	Methods:
	#		__init__ (self, category name)
	#		getEmail (self)
	#		getName (self)
	#		getArea (self)
	#		getStaff (self)
	#		getStatus (self)
	#		getType (self)
	#		getDescription ()
	#		sendNotification (self, from whom, TrackRec, special
	#			handling if emergency?)
	#		setEmail (self, comma-separated email string)
	#		setStaff (self, comma-separated staff string)
	#		save (self)

	def __init__ (self,
		category_name	# string; name of the Category to load
		):
		# Purpose: initialize this Category object by loading the info
		#	for the specified "category_name" from the database
		# Returns: nothing
		# Assumes: db's SQL routines have been initialized.
		# Effects: accesses the database to retrieve info from the
		#	WTS_Routing and CV_WTS_Category tables
		# Throws: 1. propagates db.sqlError if a problem occurs in
		#	querying the database.  2. error.exc_BadCategory if we
		#	do not recognize the specified "category_name"

		global CATEGORY_CV

		# use the Controlled_Vocab object's validate() method to see
		# if the specified "category_name" is valid.  And, if so, get
		# its key.  If not, raise an exception.

		([key], [ignore_errors], badName) = CATEGORY_CV.validate (
			category_name)
		if badName:
			raise error, exc_BadCategory % category_name

		# now, note the key we found, and use it to get the remaining
		# Category info from the database

		self.key = key
		self.name = category_name

		[ cat_info, staff_info ] = wtslib.sql ( [

			# get the description and email from CV_WTS_Category,
			# as well as the default Area, Type, and Status keys

			'''select category_description, category_email,
				_Area_key, _Type_key, _Status_key
			from CV_WTS_Category
			where (_Category_key = %d)''' % self.key,

			# get the staff info from WTS_Routing

			'''select _Staff_key
			from WTS_Routing
			where (_Category_key = %d)''' % self.key ] )

		# cat_info should have exactly one row, since we already
		# tested to see if the "category_name" was valid and then used
		# it to look up and use the exact key.  So, we can access
		# list element [0] directly.

		self.email = cat_info [0]['category_email']
		self.description = cat_info [0]['category_description']
		self.area = Controlled_Vocab.cv ['CV_WTS_Area'].keyToName (
			cat_info [0]['_area_key'] )
		self.type = Controlled_Vocab.cv ['CV_WTS_Type'].keyToName (
			cat_info [0]['_type_key'] )
		self.status = Controlled_Vocab.cv ['CV_WTS_Status'].keyToName (
			cat_info [0]['_status_key'] )

		# There can be any number of staff members assigned to this
		# Category.  Just collect them in a Set.

		self.staff = Set.Set ()
		for row in staff_info:
			self.staff.add (row ['_staff_key'])
		return


	def getEmail (self):
		# Purpose: see Returns
		# Returns: a string containing the comma-separated set of e-mail
		#	addresses who should be notified when a tracking
		#	record is routed to this category
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.email


	def getName (self):
		# Purpose: see Returns
		# Returns: a string containing the name of this category
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.name


	def getArea (self):
		# Purpose: see Returns
		# Returns: a string containing the default Area for a tracking
		#	record routed to this category (or None if no default)
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.area


	def getType (self):
		# Purpose: see Returns
		# Returns: a string containing the default Type for a tracking
		#	record routed to this category (or None if no default)
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.type


	def getStaff (self):
		# Purpose: see Returns
		# Returns: a string containing a comma-separated set of staff
		#	members who should be in the staff field when a 
		#	tracking record is routed to this category
		# Assumes: all keys in self.staff are valid (defined in
		#	CV_Staff)
		# Effects: maps from the staff keys contained in self.staff to
		#	their respective usernames using the STAFF_Cv object
		# Throws: nothing

		global STAFF_CV

		map = STAFF_CV.key_dict ()	# map [key] = staff username
		staff = ''
		for key in self.staff.values ():
			staff = staff + ', ' + map [key]
		return staff [2:]


	def getStatus (self):
		# Purpose: see Returns
		# Returns: a string containing the default Status for tracking
		#	records routed to this Category (or None if no default)
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.status


	def getDescription (self):
		# Purpose: see Returns
		# Returns: a string containing the text description of this
		#	Category
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.description


	def sendNotification (self,
		from_whom,		# string; who is the e-mail from?
		tr,			# TrackRec object; TR that was created
		emergency_chk = FALSE	# send special e-mail if "tr" is an
					# emergency
		):
		# Purpose: send e-mail to the addresses specified in this
		#	routing category (self) from the designated address
		#	("from_whom"), with info from the given "tr"
		# Returns: a string containing the subject line of the e-mail
		#	that was sent, or an empty string if none is sent
		# Assumes: the Configuration module has an entry for
		#	"Emergency_Email" which defines an e-mail address which
		#	should receive notification of emergency TRs
		# Effects: uses the wtslib module to send the e-mail
		# Throws: nothing
		# Notes: if this category has no defined e-mail addresses
		#	(a string of length 0) we don't bother trying to send
		#	the mail.

		# standard handling for Category-defined e-mails

		if self.getEmail () is not None:
			subject = Configuration.config['PREFIX'] + \
				": TR %s routed to: %s" % (tr.num (),
				self.getName ())
			wtslib.send_Mail (from_whom, self.getEmail (), subject,
				tr.getRoutingMessage ())
		else:
			subject = ""
		
		# special handling for TRs which are in an emergency state (if
		# requested -- it is disabled by default)

		if emergency_chk and tr.isEmergency ():
			subject = "WTS -- EMERGENCY -- TR %s routed to: %s" % \
				(tr.num (), self.getName ())
			wtslib.send_Mail (from_whom,
				Configuration.config ['Emergency_Email'],
				subject,
				tr.getRoutingMessage ())
		return subject


	def setEmail (self,
		email		# string; comma-separated string of e-mail
				# address(es) to notify when a tracking
				# record is routed to this Category
		):
		# Purpose: set the e-mail addresses in this Category object
		# Returns: boolean - TRUE if set okay, FALSE if not
		# Assumes: nothing
		# Effects: verifies the string by looking to ensure that all
		#	spaces are preceded by a comma.
		# Throws: nothing

		# if we find any spaces that are preceded by anything but a
		# comma, then we have an error -- the test will fail and we
		# bail out.

		if regex.search ('[^,][ ]', email) == -1:
			self.email = email
			return TRUE
		return FALSE


	def setStaff (self,
		staff_members	# string; comma-separated string of staff
				# members who should be in the Staff field of
				# a tracking record routed to this Category
		):
		# Purpose: set the staff field of this Category
		# Returns: a two-item tuple.  The first item is a boolean which
		#	indicates whether the staff members were set okay (TRUE
		#	= yes, FALSE = no), and a list containing any error
		#	strings.
		# Assumes: nothing
		# Effects: verifies that each staff member named in the
		#	"staff_members" parameter is a valid staff member in
		#	the CV_Staff controlled vocbulary.  If all are okay,
		#	then set self's staff field.
		# Throws: nothing
		# Notes: we treat the empty string "" as a special case which
		#	indicates that we should remove all staff members.

		global STAFF_CV

		# treat a blank string as a special case where we should
		# remove all staff members

		if len (staff_members) == 0:
			self.staff = Set.Set ()
			return (TRUE, [])

		# otherwise, parse the string and update staff appropriately

		(keys, errors, anyErrors) = STAFF_CV.validate (staff_members)
		if not anyErrors:
			self.staff = Set.Set ()
			for key in keys:
				self.staff.add (key)
			return (TRUE, [])
		else:
			error_strings = []
			for item in errors:
				if item is not None:
					error_strings.append (item)
			return (FALSE, error_strings)


	def save (self):
		# Purpose: save the contents of self to the database
		# Returns: None
		# Assumes: db's SQL routines have been initialized
		# Effects: updates the WTS_Routing and CV_WTS_Category tables
		#	in the database
		# Throws: propagates wtslib.sqlError if we have problems
		#	running the SQL update statements

		sql_statements = [

			# update the e-mail field

			'''update CV_WTS_Category
			set category_email = "%s"
			where _Category_key = %d''' % (self.email, self.key),

			# then delete the old staff members

			'''delete from WTS_Routing
			where _Category_key = %d''' % self.key ]

		# and add the new staff members

		for staff_key in self.staff.values ():
			sql_statements.append ('''insert WTS_Routing
				(_Category_key, _Staff_key)
				values (%d, %d)''' % (self.key, staff_key))

		wtslib.sql (sql_statements)		# do the updates
		return
