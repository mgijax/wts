#!/usr/local/bin/python

# Name:		HTGroup.py
# Purpose:	provides the HTGroup class which allows easy access to and
#		modification of htpasswd-compatible group files.  (from
#		within Python rather than shelling out to the OS)

import os
import regex
import rand
import crypt
import time
import string
import WriteLock
import Set

TRUE = 1	# define boolean constants to aid code readability
FALSE = 0

error = 'HTGroup.error'		# define the exception for this module
				# and its possible exception values:
exc_BadData = 'Error in group file %s'
exc_CannotLock = 'Cannot lock group file %s'
exc_CannotWriteLock = 'Cannot write lock file for group file %s'

#-------------------------------------------------------------------------
class HTGroup:
	# Concept:
	#	IS: a Python representation of a group file for use by .htaccess
	#		files.  This type of file is usually maintained by hand.
	#	HAS: a path, a Set of groups and their users
	#	DOES: provides operations to add and remove users from groups,
	#		add and remove groups, and get lists of groups and the
	#		users they contain.
	# Implementation:
	#	Each HTGroup object has four instance variables:
	#		path - name (and path, if needed) of the
	#			corresponding file in the file system
	#		padlock - WriteLock for the given "path" + '.lock'
	#		isOpen - boolean to indicate whether the file is
	#			currently open for writing (is locked and has
	#			not been closed)
	#		groups - dictionary which uses groups as keys and maps
	#			them to the Set of users each contains
	#	Methods:
	#		__init__ (path)
	#		addGroup (group)
	#		addUser (username, group)
	#		close ()
	#		getAllGroups ()
	#		getAllUsers (group)
	#		hasUser (username, group)
	#		isGroup (group)
	#		removeGroup (group)
	#		removeUserFromGroup (username, group)
	#		removeUserFromAllGroups (username)
	#
	#	Note that changes are not actually made to the group file in
	#	the file system until the "close()" method is called.

	def __init__ (self,
		path	# string; path to the group file to work with
		):
		# Purpose: initializes this HTGroup object
		# Returns: None
		# Assumes: nothing
		# Effects: Initializes self by creating the instance variables:
		#	"path", "groups", "isOpen", and "filelock".  If the file
		#	specified in self.path exists, we lock it, read it, and
		#	add the info to "groups".  Otherwise we just start with
		#	no groups.
		# Throws: 1. error.exc_BadData if a line in the file at the
		#	given "path" is not parseable, 2. error.exc_CannotLock
		#	if we cannot get a lock for the given "path",
		#	3. error.exc_CannotWriteLock if the current user does
		#	not have write permission for the lock file.
		# Notes: Each line of the data file consists of a group followed
		#	by a colon, followed by a space-separated set of users.
		#	If we need to work out of a home directory, we must
		#	specify the full path rather than using the '~'.

		self.path = path	# remember this path
		self.groups = {}	# no group info yet
		self.isOpen = FALSE	# not yet locked

		# the name of the lock file will just be the given path with
		# a ".lock" appended...

		self.padlock = WriteLock.WriteLock (path + ".lock")
		try:
			# If someone else has the lock and we can't get it,
			# then raise the exc_CannotLock message.  If we don't
			# have write permission on the lock file, that will
			# raise an IOError which we catch below...

			if not self.padlock.lock ():
				raise error, exc_CannotLock % path
		except IOError:
			raise error, exc_CannotWriteLock % path

		self.isOpen = TRUE	# lock succeeded, is not yet unlocked

		re = regex.compile ('\([A-Za-z0-9_]+\)'	# group
				'[ \t]*:'		# separator
				'\(.*\)')		# users
		try:
			fp = open (self.path, 'r')
			lines = fp.readlines ()		# read the file
			fp.close ()
		except IOError:
			return		# bail out with no users and groups -
					# the given file does not exist yet

		# now go through each line we read and add its info to
		# self.groups:

		for line in lines:
			if re.match (line) < 0:
				raise error, exc_BadData % self.path
			else:
				group, users = re.group (1,2)
				userlist = string.split (users)

				# If this is the first time we've seen this
				# group, add it to the dictionary of groups.
				# Then add each user.

				if not self.groups.has_key (group):
					self.groups [group] = Set.Set ()
				for user in userlist:
					self.groups [group].add (user)
		return


	def addGroup (self,
		group		# string; new group to add
		):
		# Purpose: add a new "group"
		# Returns: boolean -- FALSE if we fail to add it, or TRUE if it
		#	is added okay
		# Assumes: nothing
		# Effects: adds a new "group" to self.groups
		# Throws: nothing

		# if the "group" is already defined, or if we're not open for
		# writing, bail out

		if self.isGroup (group) or (not self.isOpen):
			return FALSE

		self.groups [group] = Set.Set ()
		return


	def addUser (self,
		username,	# string; name of the user to add
		group		# string; group to which to add "username"
		):
		# Purpose: add "username" to the given "group"
		# Returns: boolean -- FALSE if we fail to add it, or TRUE if it
		#	is added okay
		# Assumes: "username" is a valid user
		# Effects: adds "username" to the Set of users for "group"
		# Throws: nothing

		# if the "group" is not defined, or if we're not open for
		# writing, bail out

		if not self.isGroup (group) or (not self.isOpen):
			return FALSE
		self.groups [group].add (username)
		return TRUE


	def close (self):
		# Purpose: save the group & user data in self to a file,
		#	then unlock it.
		# Returns: boolean -- TRUE if we wrote the file, FALSE if not
		# Assumes: nothing
		# Effects: Writes a .htaccess-compatible group file out to
		#	self.path, then unlocks it.
		# Throws: IOError if we cannot open the file for writing.
		# Notes: Each line of the data file consists of the group
		#	followed by a colon followed by a space-separated set
		#	of usernames.

		if self.isOpen:
			fp = open (self.path, 'w')
			for group in self.groups.keys ():
				fp.write ('%s:' % group)
				for user in self.groups [group].values ():
					fp.write (' %s' % user)
				fp.write ('\n')
			fp.close ()
			self.padlock.unlock ()
			self.isOpen = FALSE	# file has been saved, so allow
						# no more changes
			return TRUE
		return FALSE


	def getAllGroups (self):
		# Purpose: return a list of all groups defined in this object
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.groups.keys ()


	def getAllUsers (self, group):
		# Purpose: return a list of strings, each of which is a user
		#	currently defined in the specified "group"
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		if self.isGroup (group):
			return self.groups [group].values ()
		else:
			return []


	def hasUser (self,
		username,	# string; name of the user we're looking for
		group		# string; group to look in for "username"
		):
		# Purpose: test to see if the given "username" is defined in
		#	the given "group"
		# Returns: boolean - FALSE if the user or the group is not
		#	defined, TRUE if the user is a member of the specified
		#	group
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		if self.isGroup (group):
			return self.groups [group].contains (username)
		else:
			return FALSE


	def isGroup (self,
		group		# string; name of the group we're looking for
		):
		# Purpose: test to see if the given "group" is defined in
		#	this object
		# Returns: boolean - FALSE if the group is not defined, TRUE if
		#	it is
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.groups.has_key (group)


	def removeGroup (self,
		group		# string; name of the group to be deleted
		):
		# Purpose: delete the given "group" from this object
		# Returns: boolean - FALSE if we did not delete the "group",
		#	or TRUE if we did
		# Assumes: nothing
		# Effects: deletes the specified "group" from this object
		# Throws: nothing

		if self.isOpen and self.isGroup (group):
			del self.groups [group]
			return TRUE
		return FALSE


	def removeUserFromGroup (self,
		username,	# string; name of the user to be deleted
		group		# string; group from which to delete that user
		):
		# Purpose: delete the given "username" from the given "group"
		# Returns: boolean - FALSE if we did not delete the "username",
		#	or TRUE if we did
		# Assumes: nothing
		# Effects: deletes the specified "username" from the given
		#	"group", if it is defined in that "group"
		# Throws: nothing

		if self.isOpen and self.hasUser (username, group):
			self.groups [group].remove (username)
			return TRUE
		return FALSE


	def removeUserFromAllGroups (self,
		username	# string; name of the user to be deleted from
				# all groups
		):
		# Purpose: delete "username" from all groups in this object
		# Returns: boolean - FALSE if the file is not currently open
		#	for writing, or TRUE if it is open and we eliminated
		#	all occurrences of "username"
		# Assumes: nothing
		# Effects: deletes the specified "username" from all groups in
		#	self
		# Throws: nothing

		if self.isOpen:
			for group in self.groups.keys ():
				# note that because of the way the remove()
				# method is defined in the Set.py module, we
				# don't have to test for membership first.  It
				# just ignores those that aren't there.

				self.groups [group].remove (username)
			return TRUE
		return FALSE
