#!/usr/local/bin/python

# Name: WriteLock.py
# Purpose: provides the WriteLock class, which provides a means to lock a file
#	the file system and write out a new copy
# On Import: seeds the random number generator in the "rand" module with the
#	current time
# Assumes: all writes to the specified file go through this module

import os
import time
import rand
import fcntl
import FCNTL

NONBLOCKING_WRITE = FCNTL.F_WRLCK | FCNTL.O_NDELAY	# constant indicating
							# a non-blocking write
							# operation

TRUE = 1				# define constants for booleans for
FALSE = 0				# readability

rand.srand (int (time.time ()))		# seed random number generator

class WriteLock:
	# Concept:
	#	IS: a padlock for a given file which will ensure that only one
	#		user of this module can write to the given file at any
	#		time
	#	HAS: a status about whether the given file is locked or not
	#	DOES: lets the user lock, unlock, test the lock status, and
	#		write to the locked file
	# Implementation:
	#	Methods:
	#		__init__ (filename to lock)
	#		lock (milliseconds to wait)
	#		unlock ()
	#		write ()

	def __init__ (self, filename):
		# Purpose: initialize this WriteLock object
		# Returns: None
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		self.filename = filename	# remember the filename
		self.fp = None			# (file ptr) not ready to write
		return


	def lock (self,
		wait_time = 3000	# integer; maximum number of
					# milliseconds to wait for lock.
					# default to 3 seconds.
		):
		# Purpose: lock the filename which we gave in the constructor
		# Returns: TRUE if we lock it successfully, or FALSE if the
		#	"wait_time" runs out before we can get it locked
		# Assumes: current user has permission to lock the file
		# Effects: If the lock become free before "wait_time" runs out,
		#	locks the file using the "fcntl" module.
		# Throws: propagates an IOError if the current user does not
		#	have permission to open "self.filename" for writing.
		# Notes: If you want to try to lock a file without waiting
		#	around if it is already locked, you may invoke this
		#	method with "wait_time" = 0.

		# get the time remaining...  set to at least 1 ms so we will
		# try the lock once even if we don't want to wait for it...
		# At worst, we waste 1 millisecond of time (or whatever the
		# smallest timeslice measured by the OS is)

		time_left = int (max (1, wait_time))

		# Get a temporary pointer to the specified file, opened for
		# writing.  Then get its file number.  If the file cannot be
		# opened for writing, this will raise an IOError.

		temp_fp = open (self.filename, 'w')		# file pointer
		temp_nr = temp_fp.fileno ()			# file number

		# Now, let's loop until the timer expires.  With each iteration,
		# see if it is locked.  If not, lock it and return TRUE.  If it
		# is locked, wait a random portion of the time left and try
		# again.

		while (time_left > 0):
			# if we try to lock the file and fail, it will
			# generate an IOError exception

			try:
				fcntl.flock (temp_nr, NONBLOCKING_WRITE)
				self.fp = temp_fp
				return TRUE
			except IOError:
				# The % operation will return a number in the
				# range 0..(time_left - 1).  Since we need a
				# range of 1..time_left to avoid an infinite
				# loop, add 1 ms.

				to_wait = (rand.rand () % time_left) + 1
				time.sleep (to_wait / 1000.0)
				time_left = time_left - to_wait
		temp_fp.close ()
		return FALSE


	def isLocked (self):
		# Purpose: test whether the file given in the constructor is
		#	locked
		# Returns: TRUE if it is locked, FALSE if it is not
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return (self.fp != None)


	def unlock (self):
		# Purpose: unlock and close the file given in the constructor
		# Returns: boolean -- TRUE if we unlocked the file, FALSE if not
		# Assumes: nothing
		# Effects: If the file specified in the constructor is locked,
		#	unlock it.
		# Throws: nothing

		if self.isLocked ():
			self.fp.close ()	# close the file (which also
						# unlocks it), then erase the
			self.fp = None		# file pointer
			return TRUE
		return FALSE


	def write (self,
		s	# string to be written to the locked file
		):
		# Purpose: write the string "s" to the locked file
		# Returns: boolean -- TRUE if we wrote "s" out okay, FALSE if
		#	we did not
		# Assumes: nothing
		# Effects: appends string "s" to the file we are building
		# Throws: nothing
		# Notes: A newline is not appended; if you want one, add it
		#	yourself.

		if self.isLocked ():
			self.fp.write (s)
			return TRUE
		return FALSE
