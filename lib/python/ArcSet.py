#!/usr/local/bin/python

# Name:		ArcSet.py
# Author:	Jon Beal
# Purpose:	implements the ArcSet class for WTS

import Arc
import Set

class ArcSet:
	# Concept:
	#	IS:	a set of Arc objects to which Arcs may be added, and
	#		from which they may be removed.  (For now, we assume
	#		that the node at each end of an Arc is represented by
	#		an integer)
	#	HAS:	a set of Arc objects
	#	DOES:	an ArcSet may have Arcs added or deleted, a list of
	#		Arcs may be retrieved, and we may test for the existence
	#		of a specified Arc in the ArcSet
	# Implementation:
	#	Testing for the existence of a particular Arc in this ArcSet
	#	will likely be a very common operation, so we need to ensure
	#	that it happens fairly quickly.  To this end, we do not store
	#	a list of Arcs (which would involve an expensive list traversal
	#	for each Arc existence check).  We set up a dictionary which is
	#	keyed using the "from node" of each arc to reference a Set of
	#	the "to nodes".  Thus, for a given Arc existence check, we can
	#	use the "from node" (in a single memory access) to weed out
	#	all arcs that do not begin at that node.  The efficiency in
	#	looking at the Set of "to nodes" then depends on the
	#	implementation of a Set object, though it should be no worse
	#	than a list traversal on this much smaller set of items.
	# Methods:
	#	__init__ (self, optional list of Arcs)
	#	addArcs (self, list of Arcs)
	#	addArc (self, Arc)
	#	exists (self, Arc)
	#	removeArcs (self, list of Arcs)
	#	removeArc (self, Arc)
	#	getArcs (self)

	def __init__ (self,
		arcs = []	# optional list of Arc objects to add to this
				# ArcSet at initialization
		):
		# Purpose: initialize this ArcSet object
		# Returns: nothing
		# Assumes: nothing
		# Effects: initializes this ArcSet object, including starting
		#	with a blank set of arcs, and then adding any arcs
		#	which were passed in the parameter.
		# Throws: nothing

		self.arcs = {}		# arcs [from node] = Set of to_nodes,
					# further described in class comments
		self.addArcs (arcs)
		return

	def addArcs (self,
		arcs		# list of Arc objects to add to this ArcSet
		):
		# Purpose: add the specified "arcs" to this ArcSet object
		# Returns: nothing
		# Assumes: items in "arc" are Arc objects
		# Effects: see Purpose.
		# Throws: nothing

		for arc in arcs:
			self.addArc (arc)
		return

	def addArc (self,
		arc		# Arc object to add to this ArcSet object
		):
		# Purpose: adds a single "arc" to this ArcSet object
		# Returns: nothing
		# Assumes: "arc" is a valid "Arc" object
		# Effects: see Purpose.  updates the dictionary of arcs
		# Throws: nothing

		to_node = arc.getToNode ()	# arc's destination node
		from_node = arc.getFromNode ()	# arc's origin node

		# if there are not yet any arcs originating with this from_node,
		# then we need to create a new entry with a new set of to_nodes

		if not self.arcs.has_key (from_node):
			self.arcs [from_node] = Set.Set ()
		self.arcs [from_node].add (to_node)
		return

	def exists (self,
		arc		# Arc object to look for in this ArcSet object
		):
		# Purpose: return a boolean (0/1) indicating whether "arc" is
		#	contained in this ArcSet (1) or not (0)
		# Returns: see Purpose.
		# Assumes: arc is a valid Arc object
		# Effects: see Purpose
		# Throws: nothing

		to_node = arc.getToNode ()	# destination node of arc
		from_node = arc.getFromNode ()	# origin node of arc
		
		# first, see if any arcs start at this from_node.  If so, then
		# see if any of them go to the to_node.

		if self.arcs.has_key (from_node):
			if self.arcs [from_node].contains (to_node):
				return 1
		return 0

	def removeArcs (self,
		arcs		# list of Arc objects to remove from this ArcSet
		):
		# Purpose: remove each Arc in "arcs" from this ArcSet
		# Returns: nothing
		# Assumes: all items in "arcs" are valid Arc objects
		# Effects: see Purpose
		# Throws: nothing

		for arc in arcs:
			self.removeArc (arc)
		return

	def removeArc (self,
		arc		# Arc object to remove from this ArcSet
		):
		# Purpose: remove the given Arc ("arc") from this ArcSet
		# Returns: nothing
		# Assumes: "arc" is a valid Arc object
		# Effects: removes the specified "arc" from this ArcSet by
		#	removing it from the dictionary of arcs
		# Throws: nothing

		to_node = arc.getToNode ()	# destination node of arc
		from_node = arc.getFromNode ()	# origin node of arc

		# first, look to see if any arcs originated at this from_node.
		# If so, then delete the one going to to_node.  If there are
		# then no others originating at from_node, then delete the
		# entry for from_node.

		if self.arcs.has_key (from_node):
			self.arcs [from_node].remove (to_node)
			if self.arcs [from_node].empty():
				del self.arcs [from_node]
		return

	def getArcs (self):
		# Purpose: return a list of Arc objects in this ArcSet
		# Returns: see Purpose.
		# Assumes: nothing
		# Effects: see Purpose.
		# Throws: nothing

		arcs = []	# list of Arc objects to build and return

		# go through each from_node.  For each one, create (and append
		# to "arcs") an Arc from it to each of its to_nodes.

		for from_node in self.arcs.keys ():
			for to_node in self.arcs [from_node].values ():
				arcs.append (Arc.Arc (from_node, to_node))
		return arcs
