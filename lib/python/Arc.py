#!/usr/local/bin/python

# Name:		Arc.py
# Purpose:	implements the Arc class for WTS

class Arc:
	# Concept:
	#	IS:	An Arc is an edge in a directed graph.  For now, we
	#		assume that the nodes are represented by integers.
	#		Note that in WTS, those integers are tracking record
	#		numbers.
	#	HAS:	Two integer keys, one for the from_node and one for the
	#		to_node.  (In the WTS system, both of these are 
	#		tracking record keys, where the from_node has some
	#		relationship to the to_node.)
	#	DOES:	One can ask the Arc to return the integer key of either
	#		tracking record.  (from_node or to_node)
	# Implementation:
	#	This class is very straightforward.  It merely serves as an
	#	abstraction for a single arc in a digraph of tracking record
	#	relationships.  Each object stores a "from node" and a "to node"
	#	which may be retrieved.
	# Methods:
	#	__init__ (self, from node, to node)
	#	getFromNode (self)
	#	getToNode (self)


	def __init__ (self,
		from_node,	# integer node number for arc's origin
		to_node		# integer node number for arc's destination
		):
		# Purpose: initialize this Arc object
		# Returns: nothing
		# Assumes: nothing
		# Effects: stores from_node and to_node in this Arc object
		# Throws: nothing

		self.from_node = from_node
		self.to_node = to_node
		return

	def getFromNode (self):
		# Purpose: retrieve the value stored for the "from node", the
		#	one which is the origin of this Arc
		# Returns: an integer which identifies the origin node of this
		#	Arc
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.from_node

	def getToNode (self):
		# Purpose: retrieve the value stored for the "to node", the
		#	one which is the destination of this Arc
		# Returns: an integer which identifies the destination node of
		#	this Arc
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.to_node
