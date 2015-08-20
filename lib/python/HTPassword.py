#!/usr/local/bin/python

# Name:		HTPassword.py
# Purpose:	provides the HTPassword class which allows easy access to and
#		modification of htpasswd-maintained password files.  (from
#		within Python rather than shelling out to the OS)

import os
import regex
import random
import crypt
import time
import WriteLock

TRUE = 1	# define boolean constants to aid code readability
FALSE = 0

DISABLED_PW = '*'	# value in the password file which represents a
			# password that has been disabled

error = 'HTPassword.error'		# define the exception for this module
					# and its possible exception values:
exc_BadData = 'Error in password file %s'
exc_CannotLock = 'Cannot lock password file %s'
exc_CannotWriteLock = 'No permission to create lock file for password file %s'

#-------------------------------------------------------------------------
# supporting code adapted from htpasswd.c by Rob McCool (which itself
# referenced local_passwd.c (C) Regents of University of California)

itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

def to64 (v,	# integer to use in generating the returned string
	n	# integer number of characters to include in the returned string
	):
	# Purpose: return a string as described in Returns (for use as a salt
	#	value by the HTPassword class, in this case)
	# Returns: a string with length "n" containing characters produced by
	#	manipulating the input "v".
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: This function is adapted from htpasswd.c by Rob McCool.  His
	#	code came from local_passwd.c (C) Regents of Univ. of
	#	California.  We essentially build a string by mapping six-bit
	#	chunks of "v" onto the characters defined in "itoa64".
	# Example: to64 (92, 2) ==> 'Q/'	(itoa64 [28] + itoa64 [1])

	global itoa64

	s = ''					# string to return
	for i in range (0,n):
		s = s + itoa64 [ v & 0x3f ]	# v & 0x3f == v % 64
		v = v >> 6			# v >> 6   == v / 64
	return s

#-------------------------------------------------------------------------
class HTPassword:
	# Concept:
	#	IS: a Python representation of a password file for use by
	#		.htaccess files.  This type of file is usually
	#		maintained by the Unix utility "htpasswd".
	#	HAS: a path, and a set of users and their encrypted
	#		passwords
	#	DOES: provides operations to add users, remove users, change
	#		passwords, and list all users.
	# Implementation:
	#	Each HTPassword object has four instance variables:
	#		path - name (and path, if needed) of the
	#			corresponding file in the file system
	#		padlock - WriteLock for the given "path" + '.lock'
	#		isOpen - boolean to indicate whether the file is
	#			currently open for writing (is locked and has
	#			not been closed)
	#		users - dictionary which uses usernames as keys and
	#			maps them to their respective encrypted
	#			passwords
	#	Methods:
	#		__init__ (path)
	#		addUser (username, password)
	#		close ()
	#		getAllUsers ()
	#		isUser (username)
	#		removeUser (username)
	#		setPassword (username, password)
	#		unsetPassword (username)
	#
	#	Note that changes are not actually made to the password file in
	#	the file system until the "close()" method is called.

	def __init__ (self,
		path	# string; path to the password file to work with
		):
		# Purpose: initializes this HTPassword object
		# Returns: None
		# Assumes: nothing
		# Effects: Initializes self by creating the instance variables:
		#	"path", "users", "padlock", and "isOpen".  If the file
		#	specified in self.path exists, we lock it, read it and
		#	add the passwords and values to the dictionary
		#	self.users.  Otherwise, we just start with an empty
		#	self.users.
		# Throws: 1. error.exc_BadData if a line in the file at the
		#	given "path" is not parseable, 2. error.exc_CannotLock
		#	if we cannot get a lock for the given "path",
		#	3. error.exc_CannotWriteLock if the current user does
		#	not have write permission for the lock file.
		# Notes: Each line of the data file consists of the username
		#	followed by a colon followed by the encrypted password
		#	(which is composed of characters from "itoa64").
		#	If we need to work with files in a home diretory, we
		#	need to specify the full path rather than using the '~'.

		self.path = path	# remember this path
		self.users = {}		# no users & passwords yet
		self.isOpen = FALSE	# not yet locked

		# the name of the lock file will just be the given path with
		# a ".lock" appended

		self.padlock = WriteLock.WriteLock (path + '.lock')

		try:
			# If someone else has the lock and we can't get it,
			# then raise the exc_CannotLock message.  If we don't
			# have write permission on the lock file, that will
			# raise an IOError which we catch below...

			if not self.padlock.lock ():
				# if we waited the full time limit and it's
				# still locked, there's some kind of problem,
				# so try to force it open

				self.padlock.unlock(force=True)
				if not self.padlock.lock():
					raise error, exc_CannotLock % path
		except IOError:
			raise error, exc_CannotWriteLock % path

		self.isOpen = TRUE	# lock succeeded, is not yet unlocked

		re = regex.compile ('\([A-Za-z0-9_]+\)'		# username
				':'				# separator
				'\([/\.0-9A-Za-z*]+\)')		# encrypted pwd
		try:
			fp = open (self.path, 'r')
			lines = fp.readlines ()		# read the file
			fp.close ()
		except IOError:
			return		# bail out with an empty data set - the
					# given file does not exist yet

		# now go through each line we read and add its info to
		# self.users:

		for line in lines:
			if re.match (line) < 0:
				raise error, exc_BadData % self.path
			else:
				user, pwd = re.group (1,2)
				self.users [ user ] = pwd
		return


	def addUser (self,
		username,	# string; name of the user to add
		password	# string; non-encrypted password for "user"
		):
		# Purpose: add a new username and password to this object
		# Returns: boolean -- FALSE if we fail because "username", or
		#	TRUE if it is added okay
		# Assumes: nothing
		# Effects: if "username" is not already defined, we store it and
		#	an encrypted version of its password in self.users
		# Throws: nothing
		# Notes: Rather than duplicate the code from the setPassword()
		#	method, we simply define a user with DISABLED_PW as a
		#	password and then call setPassword() to do the
		#	encryption and password setting.  This allows us to
		#	keep one point of maintenance for that code.  Also note
		#	that this only adds the user to this object (and the
		#	user password file when it is closed); you'll need to
		#	take care of changes to the group file separately.

		# if the "username" is already defined, or if we're not open
		# for writing, bail out

		if self.isUser (username) or (not self.isOpen):
			return FALSE

		self.users [username] = DISABLED_PW	# no password set yet
		self.setPassword (username, password)	# set the password
		return TRUE


	def close (self):
		# Purpose: save the user & password data in self to a file,
		#	then unlock it.
		# Returns: boolean -- TRUE if we wrote the file, FALSE if not
		# Assumes: nothing
		# Effects: Writes a .htaccess-compatible password file out to
		#	self.path, then unlocks it.
		# Throws: IOError if we cannot open the file for writing.
		# Notes: Each line of the data file consists of the username
		#	followed by a colon followed by the encrypted password.

		if self.isOpen:
			fp = open (self.path, 'w')
			for user in self.users.keys ():
				fp.write ('%s:%s\n' % (user, self.users [user]))
			fp.close ()
			self.padlock.unlock ()
			self.isOpen = FALSE
			return TRUE
		return FALSE


	def getAllUsers (self):
		# Purpose: return a list of all users currently defined in this
		#	HTPassword object
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.users.keys ()


	def isUser (self,
		username	# string; name of the user we're looking for
		):
		# Purpose: test to see if the given "username" is defined in
		#	this object
		# Returns: boolean - FALSE if the user is not defined, TRUE if
		#	it is
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.users.has_key (username)


	def removeUser (self,
		username	# string; name of the user to be deleted
		):
		# Purpose: delete the name & password for the specified
		#	"username" from this object
		# Returns: boolean - FALSE if we did not delete the "username",
		#	or TRUE if we did
		# Assumes: nothing
		# Effects: deletes the specified "username" from self, if it
		#	is defined in self.
		# Throws: nothing

		if self.isOpen and self.isUser (username):
			del self.users [username]
			return TRUE
		return FALSE


	def setPassword (self,
		username,	# string; name of the user whose password to set
		password	# string; non-encrypted new password for "user"
		):
		# Purpose: set "password" to be the new password for "user" in
		#	this object
		# Returns: boolean -- FALSE if we fail to set the "password"
		#	for "username", or TRUE if we succeed
		# Assumes: nothing
		# Effects: encrypts "password" and stores the result in self as
		#	the password for "username"
		# Throws: nothing
		# Notes: We re-seed the random number generator using the
		#	current time whenever this method is invoked.  This
		#	should provide a more random sequence of numbers, and
		#	is the method used by "htpasswd.c".  In fact, this
		#	method is modeled after the add_password() function in
		#	"htpasswd.c".

		if not (self.isUser (username) and self.isOpen):
			return FALSE

		# seed the random number generator.  encrypt the password and
		# store it in "cpw".  Then set "cpw", the encrypted password,
		# as the password for "username".

		random.seed (int (time.time ()))
		cpw = crypt.crypt (password, to64 (random.randint (0,500), 2))
		self.users [username] = cpw
		return TRUE


	def unsetPassword (self,
		username		# string; name of the user for whom
					# we should unset the password
		):
		# Purpose: unset the password for the specified "username",
		#	effectively disabling it
		# Returns: boolean -- TRUE if we unset the password, FALSE if
		#	we fail to do so
		# Assumes: nothing
		# Effects: sets the password for "username" to be DISABLED_PW
		# Throws: nothing

		if self.isUser (username) and self.isOpen:
			self.users [username] = DISABLED_PW
			return TRUE
		return FALSE
