#!/usr/local/bin/python

# Name:		Set.py
# Author:	Jon Beal
# Purpose:	Implements the Set class, a flexible implementation of a
#		mathematical set, with the common operations associated with a
#		set.  (union, intersection, difference, etc.)

import copy
import types

IN_SET = 1	# global flag used to indicate that an item is in the Set.
		# (Since our items are keys in a dictionary, IN_SET will be
		# the dictionary value referenced by each.)

class Set:
	# Concept:
	#	IS:	A Set object is an unordered collection of items.  Each
	#		item in the Set is unique.  This class represents the
	#		typical mathematical set.
	#	HAS:	A Set has an unordered collection of items.  These
	#		items may be of various types and may be objects or
	#		simple values.
	#	DOES:	Common set operations include adding and removing items;
	#		computing intersection, union, and difference; and
	#		testing for membership, equality, and superset and
	#		subset relationships.
	# Implementation:
	#	The Set object stores its items as the keys in a dictionary for
	#	quick lookups.  This also ensures that we have, at most, one
	#	copy of each item in the Set.  Instance variables include:
	#		elements - the above-mentioned dictionary of items
	# Methods:
	#	__init__ (self, *val)	intersection (self, S)
	#	__str__ (self)		union (self, S)
	#	add (self, *val)	difference (self, S)
	#	contains (self, val)	subset (self, S)
	#	values (self)		superset (self, S)
	#	remove (self, *val)	equals (self, S)
	#	empty (self)		clone (self)
	#	containsAll (self, *val)
	#	count (self)

	def __init__ (self,
		*val		# initial items to put in the Set
		):
		# Purpose: initialize a new, empty Set object, and add any
		#	items from val to it.
		# Returns: nothing
		# Assumes: nothing
		# Effects: initializes self to be an empty Set and then adds
		#	any items from val to it.
		# Throws: nothing

		self.elements = {}
		for item in val:
			self.add (item)
		return

	def __str__ (self):
		# Purpose: return a comma-separated string of items in this Set
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		s = ''					# string we're building
		for item in self.elements.keys ():	# concatenate the string
			s = s + ', ' + str (item)	# rep of each item to s
		return '%s' % s[2:]			# skip the leading
							# comma and space

	def add (self,
		*val		# items to add to the Set
		):
		# Purpose: to add the items in val to the Set, if they are not
		#	already there
		# Returns: nothing
		# Assumes: nothing
		# Effects: go through items in val, and add each to the Set.
		# Throws: nothing

		for item in val:
			self.elements [item] = IN_SET
		return

	def clone (self):
		# Purpose: return a Set which is an exact copy of self
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		return copy.deepcopy (self)

	def contains (self,
		val		# item to look for in the Set
		):
		# Purpose: determine whether "val" is in this Set
		# Returns: boolean (0/1) which indicates whether "val" is in 
		#	this Set (0 = no, 1 = yes)
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing
		# Notes: This is for testing a single item, while containsAll
		#	is useful for testing multiple items.

		return self.elements.has_key (val)

	def containsAll (self,
		*val		# items to look for in the Set
		):
		# Purpose: determine whether all the items in val are in this
		#	Set
		# Returns: boolean (0/1) which indicates whether all the items
		#	in val are in this Set (0 = no, 1 = yes)
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		for item in val:			# test each item
			if not self.elements.has_key (item):
				return 0		# found one missing
		return 1

	def values (self):
		# Purpose: return a list containing the items in this Set
		# Returns: a list with one value per item in this Set
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		return self.elements.keys ()

	def remove (self,
		*val		# items to remove from the Set
		):
		# Purpose: remove all items in val from the current Set
		# Returns: nothing
		# Assumes: nothing
		# Effects: Go through each item in val and remove from self
		#	if it is there.  If an item is not in self, then just
		#	ignore it.
		# Throws: nothing

		for item in val:
			if self.elements.has_key (item):
				del self.elements [item]
		return

	def empty (self):
		# Purpose: test whether this Set is empty
		# Returns: boolean (0/1) which indicates whether the Set is
		#	empty (1) or not (0)
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return (self.elements == {})

	def intersection (self,
		S			# the Set to intersect with self
		):
		# Purpose: return a Set which is the intersection of S and self
		# Returns: see Purpose
		# Assumes: S is a Set
		# Effects: builds a new Set object from items which are in both
		#	S and self, then returns it.
		# Throws: nothing

		result_set = Set ()
		for item in self.elements.keys ():
			if S.contains (item):
				result_set.add (item)
		return result_set

	def union (self,
		S			# the Set to union with self
		):
		# Purpose: return a Set which is the union of S and self
		# Returns: see Purpose
		# Assumes: S is a Set
		# Effects: builds a new Set object from items which are in
		#	either S or self (or both), then returns it.
		# Throws: nothing

		result_set = S.clone ()			# make a copy of S
		for item in self.elements.keys ():	# then add the items
			result_set.add (item)		# from self to it.
		return result_set

	def difference (self,
		S			# the Set to use for self - S
		):
		# Purpose: return a Set which is the difference of self - S
		# Returns: see Purpose
		# Assumes: S is a Set
		# Effects: builds a new Set object from items which are in
		#	self but not in S, then returns it.
		# Throws: nothing

		result_set = Set ()
		for item in self.elements.keys ():
			if not S.contains (item):
				result_set.add (item)
		return result_set

	def subset (self,
		S			# Set to test to see if self is a
					# subset of it
		):
		# Purpose: test and see if self is a subset of S
		# Returns: boolean (0/1) to indicate if self is a subset of
		#	S (1) or not (0)
		# Assumes: S is a Set
		# Effects: checks each item in self to see if it is also an
		#	item of S, and remembers if we find one that is not
		#	(thus indicating that self is not a subset of S)
		# Throws: nothing

		is_a_subset = 1				# assume it is
		for item in self.elements.keys ():
			if not S.contains (item):
				is_a_subset = 0		# it is not
				break			# skip rest of loop
		return is_a_subset

	def superset (self,
		S			# Set to test to see if self is a
					# superset of it
		):
		# Purpose: test and see if self is a superset of S
		# Returns: boolean (0/1) to indicate if self is a superset of
		#	S (1) or not (0)
		# Assumes: S is a Set
		# Effects: looks to see if S is a subset of self.  If so, then
		#	self is a superset of S.  (why rewrite the wheel?)
		# Throws: nothing

		return S.subset (self)

	def equals (self,
		S			# Set to test to see if it and self
					# contain the same items
		):
		# Purpose: test and see if self and S contain the same items
		# Returns: boolean (0/1) to indicate if self and S contain (1)
		#	all the same items, or not (0)
		# Assumes: S is a Set
		# Effects: looks to see if S is a subset of self, and if self
		#	is a subset of S.  If this is true, then we are assured
		#	that they contain the same items.  (why rewrite the
		#	wheel?)
		# Throws: nothing

		return S.subset (self) and self.subset (S)

	def count (self):
		# Purpose: see how many items are in the set
		# Returns: integer number of items in the set
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return len (self.values ())
