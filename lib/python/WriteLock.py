#!/usr/local/bin/python

# Name: WriteLock.py
# Purpose: provides the WriteLock class, which provides a means to use the
#	presence of one file to indicate that another file is "locked" for
#	writing and should not be opened by a second process for writing.
# On Import: seeds the random number generator in the "random" module with the
#	current time
# Assumes: all writes to the specified file go through this module
# Notes: This module was simplified in August 2015 to avoid use of fcntl, as
#	that was an unnecessary (and not necessarily portable) complication.
#	Now, if the lock file exists, it's locked.  If it doesn't exist, it's
#	not locked.  The chance of two users locking it in the exact same
#	second is remote enough that we'll ignore it.

import os
import time
import random

random.seed (int (time.time ()))		# seed random number generator

class WriteLock:
	# Concept:
	#	IS: a padlock for a given file which will ensure that only one
	#		user of this module can write to the given file at any
	#		time
	#	HAS: a status about whether the given file is locked or not
	#	DOES: lets the user lock, unlock, test the lock status
	# Implementation:
	#	Methods:
	#		__init__ (filename to lock)
	#		lock (milliseconds to wait)
	#		unlock ()

	def __init__ (self, filename):
		# Purpose: initialize this WriteLock object
		# Returns: None
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		self.filename = filename	# remember the filename
		self.haveLock = False		# do we have the lock?
		return


	def lock (self,
		wait_time = 5000	# integer; maximum number of
					# milliseconds to wait for lock.
					# default to 5 seconds.
		):
		# Purpose: lock the filename which we gave in the constructor
		# Returns: True if we lock it successfully, or False if the
		#	"wait_time" runs out before we can get it locked
		# Assumes: current user has permission to lock the file
		# Effects: If the lock become free before "wait_time" runs out,
		#	creates and "locks" the file
		# Throws: propagates an IOError if the current user does not
		#	have permission to open "self.filename" for writing.
		# Notes: If you want to try to lock a file without waiting
		#	around if it is already locked, you may invoke this
		#	method with "wait_time" = 0.

		# if this process tries to lock the file twice, skip it
		if self.haveLock:
			return

		# get the time remaining...  set to at least 1 ms so we will
		# try the lock once even if we don't want to wait for it...
		# At worst, we waste 1 millisecond of time (or whatever the
		# smallest timeslice measured by the OS is)

		time_left = int (max (1, wait_time))

		while time_left > 0:
			# if the file is already locked (by someone else),
			# then we need to wait a little and try again

			if self.isLocked():
				# wait up to a half second before trying again
				to_wait = random.randint(1, min(time_left,500))
				time.sleep (to_wait / 1000.0)
				time_left = time_left - to_wait
			else:
				fp = open(self.filename, 'w')
				fp.write('locked\n')
				fp.close()

				os.chmod(self.filename, 0x666)
				
				self.haveLock = True
				return True
		return False


	def isLocked (self):
		# Purpose: test whether the file given in the constructor is
		#	locked
		# Returns: True if it is locked, False if it is not
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return os.path.exists(self.filename)


	def unlock (self, force=False):
		# Purpose: unlock (remove) the file given in the constructor
		# Returns: boolean -- True if we unlocked the file, False if not
		# Assumes: nothing
		# Effects: If the file specified in the constructor is locked,
		#	unlock it.
		# Throws: nothing
		# Notes: if 'force' is True, then we unlock it regardless of
		#	whether we own the lock or not.

		if self.isLocked():
			if force or self.haveLock:
				os.remove(self.filename)
				self.haveLock = False
				return True
		return False
