#!/usr/local/bin/python

# Name:		Digraph.py
# Author:	Jon Beal
# Purpose:	implement the Digraph class for WTS, which (in WTS) allows us
#		to compute the transitive closure for dependency relationships
#		between tracking records.

import ArcSet
import Arc
import Set
import copy

import sys

# global declarations for boolean values

TRUE = 1
FALSE = 0

# When discussing the transitive closure, there are really two notions to
# resolve.  Consider the following Digraph with arcs:
#	Arc (1,2), Arc (2,3), Arc (3,4), and Arc (4,5)
#
#	1 ---> 2 ---> 3 ---> 4 ---> 5
#
# The transitive closure from node 2 includes Arcs from 2 to all nodes to which
# there is a path.  In this case, that would be the set of Arcs:
#	Arc (2,2), Arc (2,3), Arc (2,4), and Arc (2,5)
# This is not what we mean by the transitive closure in the WTS system.
#
# In the WTS system, we look at the transitive closure of the Digraph as a
# whole.  That is, we consider a Digraph's transitive closure to be the set of
# Arcs which have the starting and stopping points of all paths in the Digraph.
# In the above example, this would be:
#	Arc (1,1), Arc (1,2), Arc (1,3), Arc (1,4), Arc (1,5), Arc (2,2),
#	Arc (2,3), Arc (2,4), Arc (2,5), Arc (3,3), Arc (3,4), Arc (3,5),
#	Arc (4,4), Arc (4,5), Arc (5,5)

class Digraph:
	# Concept:
	#	IS:	a collection of Arcs among various integer-identified
	#		nodes.
	#	HAS:	a set of Arcs, a transitive closure (which is just
	#		another set of Arcs which make up the transitive
	#		closure), a Set of nodes (assumed to be integers for
	#		now), and a flag that indicates if the Arcs or nodes
	#		have changed (to let us know when we need to recompute
	#		the transitive closure)
	#	DOES:	a Digraph object lets you add and remove Arcs, add and
	#		remove nodes, get a list of nodes, get a list of Arcs
	#		in the Digraph, get a list of Arcs in the transitive
	#		closure of the Digraph
	# Implementation:
	#	A Digraph object contains five instance variables: one ArcSet
	#	contains the current set of Arcs in the Digraph, another ArcSet
	#	contains the Arcs resulting from the last computed transitive
	#	closure of the Digraph, a Set contains the nodes in the Digraph,
	#	a boolean flag lets us know when the current transitive
	#	closure is out-of-date (due to the addition or deletion of an
	#	Arc or node from the Digraph), and another boolean flag tells
	#	us whether we have found a cycle in the Digraph or not.
	# Methods:
	#	__init__ (self, optional ArcSet)
	#	addArcs (self, ArcSet)
	#	addArc (self, Arc)
	#	addNodes (self, *nodes)
	#	removeArcs (self, ArcSet)
	#	removeArc (self, Arc)
	#	removeNodes (self, *nodes)
	#	getArcs (self)
	#	getNodes (self)
	#	getTransitiveClosure (self)

	def __init__ (self,
		arc_set = None	# optional ArcSet object which contains the
				# initial set of Arcs for the Digraph
		):
		# Purpose: initialize this Digraph object to be empty and then,
		#	if specified, add the given arc_set
		# Returns: nothing
		# Assumes: arc_set is either None or is a valid ArcSet object
		# Effects: see Purpose.
		# Throws: nothing

		self.changed = FALSE		# no added/deleted Arcs yet
		self.closure = ArcSet.ArcSet ()	# set of Arcs in the transitive
						# closure
		self.arcs = ArcSet.ArcSet ()	# set of Arcs in the Digraph
		self.nodes = Set.Set ()		# set of nodes in the Digraph
		self.hasCycle = FALSE		# no cycles found yet

		# now, if an initial ArcSet was specified, then add it to the
		# Digraph

		if arc_set is not None:
			self.addArcs (arc_set)
		return

	def addArcs (self,
		arc_set		# ArcSet object which contains a set of Arcs to
				# add to the Digraph
		):
		# Purpose: add all the Arcs in arc_set to the Digraph
		# Returns: nothing
		# Assumes: nothing
		# Effects: Adds each Arc in arc_set to the Digraph object and
		#	notes that the Digraph has changed (so the transitive
		#	closure is out of date)
		# Throws: nothing

		for arc in arc_set.getArcs ():
			self.addArc (arc)
		return

	def addArc (self,
		arc		# Arc object to add to the Digraph
		):
		# Purpose: adds "arc" to the Digraph and notes that the Digraph
		#	has changed
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose.  If the node at either end of the "arc"
		#	does not yet exist in the Digraph, we add it to the Set
		#	of nodes.
		# Throws: nothing

		# add the Arc to the Digraph's ArcSet, and add each node to the
		# Set of nodes

		self.arcs.addArc (arc)
		self.nodes.add (arc.getFromNode(), arc.getToNode())
		self.changed = TRUE		# the Digraph has changed
		return

	def addNodes (self,
		*nodes		# nodes to add to the Digraph
		):
		# Purpose: add the given "nodes" to the Digraph
		# Returns: nothing
		# Assumes: (for now) that "nodes" are integers
		# Effects: adds "nodes" to the Set of nodes in the Digraph,
		#	and notes that the Digraph has changed
		# Throws: nothing

		for node in nodes:
			self.nodes.add (node)
		self.changed = TRUE		# the Digraph has changed
		return

	def removeArcs (self,
		arc_set		# ArcSet of Arcs to be removed from the Digraph
		):
		# Purpose: remove the Arcs in arc_set from this Digraph
		# Returns: nothing
		# Assumes: nothing
		# Effects: removes each Arc in arc_set from this Digraph, and
		#	notes that the Digraph has changed.
		# Throws: nothing

		for arc in arc_set.getArcs ():
			self.removeArc (arc)
		return

	def removeArc (self,
		arc		# Arc to remove from this Digraph
		):
		# Purpose: remove this "arc" from the Digraph and note that the
		#	Digraph has changed.
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		self.arcs.removeArc (arc)
		self.changed = TRUE
		return

	def removeNodes (self,
		*nodes		# nodes to remove from the Digraph
		):
		# Purpose: remove the given "nodes" from the Digraph
		# Returns: nothing
		# Assumes: (for now) that "nodes" are integers
		# Effects: removes "nodes" from the Set of nodes in the Digraph.
		#	If an Arcs in the Digraph began or ended at the given
		#	"nodes", we also remove those Arcs.  Note that the
		#	Digraph has changed.
		# Throws: nothing

		to_delete = ArcSet.ArcSet ()	# set of arcs to be deleted
		all_arcs = self.arcs.getArcs ()	# set of arcs in the Digraph

		for node in nodes:
			# for each node, remove it from the Set of nodes, and
			# then look for any Arcs which begin or end there,
			# because we'll need to delete them

			self.nodes.remove (node)
			for arc in all_arcs:
				if (arc.getFromNode() == node) or \
					(arc.getToNode() == node):
						to_delete.addArc (arc)
		self.arcs.removeArcs (to_delete.getArcs ())
		self.changed = TRUE		# the Digraph has changed
		return

	def getArcs (self):
		# Purpose: return a list of the Arc objects in this Digraph
		# Returns: see Purpose
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		return self.arcs.getArcs ()

	def getNodes (self):
		# Purpose: return a list of the nodes in this Digraph
		# Returns: a list of (integer, for now) nodes in this Digraph
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.nodes.values ()


	def getTransitiveClosure (self):
		# Purpose: return an ArcSet containing Arcs in the transitive
		#	closure of this Digraph
		# Returns: see Purpose
		# Assumes: The Digraph is acyclic.  Otherwise, this method will
		#	yield incorrect results.
		# Effects: Since the transitive closure can be an expensive
		#	operation, we don't want to compute it any more often
		#	than we have to.  First, we check to see if the Digraph
		#	has changed.  If not, then the currently stored
		#	transitive closure is still valid, so just return it.
		#	Otherwise, we do need to recompute (and store) the
		#	transitive closure and note that no changes have been
		#	made since recomputing.
		# Throws: nothing
		# Notes: Joel came up with this algorithm, based on a depth-
		#	first search.  It has much better performance in our
		#	domain than the more general Warshall's algorithm,
		#	although we need to be careful to disallow cycles
		#	during data entry.

		# if there have been no changes since last computing the
		# transitive closure, then just return the currently stored one

		if self.changed == FALSE:
			return self.closure

		# Otherwise, we need to go about analyzing the nodes and arcs
		# to construct a performance-optimized representation of this
		# digraph...

		# children [i] = [ nodes reached by an arc from node i ]

		children = {}

		# add self-referential arcs: (an arc can get to itself)

		for node in self.nodes.values ():
			children [node] = [node]

		# add other arcs by noting in "children" and monitoring which
		# ones have incoming arcs.

		orphans = self.nodes.clone ()	# Set of nodes which have no
						# parents (no incoming arcs)

		for arc in self.arcs.getArcs ():
			aFrom = arc.getFromNode ()
			aTo = arc.getToNode ()

			children [aFrom].append (aTo)
			orphans.remove (aTo)

		# build the dag

		# dag = [ [], [], [], ... ]
		#	where dag[0] = [ nodes with no incoming arcs ]
		#	and, for i > 0:
		#		dag[i] = [ nodes reached by an arc from node i ]

		dag = []
		for i in range (0, max (self.nodes.values ()) + 1):
			if children.has_key (i):
				dag.append ( children [i] )
			else:
				dag.append ( [] )
		dag [0] = orphans.values ()

		# compute the closure.  returns { TR : [ descendants ] }

		dict_closure = tc (dag)

		del dict_closure[0]	# delete arcs from the bogus node 0
					# (which we added above for bookkeeping)

		# turn into an ArcSet

		closure = ArcSet.ArcSet ()
		for aFrom in dict_closure.keys ():
			for aTo in dict_closure [aFrom]:
				closure.addArc (Arc.Arc (aFrom, aTo))

		self.closure = closure		# preserve it
		self.changed = FALSE		# no changes since recompute
		return closure


# Supporting Functions: -------------------------------------------------

def tc (
	dag	# a digraph, represented as a list of lists, where:
		#	dag[0] = [ nodes with no incoming arcs ]
		#	and, for i > 0:
		#		dag[i] = [ nodes reached by an arc from node i ]
	):
	# Purpose: build the full transitive closure for the given digraph, dag
	# Returns: a dictionary of lists, where:
	#	{ i : [ all descendants of (nodes reachable from) node i ] }
	# Assumes: "dag" is an acyclic digraph.  If there are any cycles, then
	#	this function will yield incorrect results.
	# Effects: nothing
	# Throws: nothing

	start = 0	# we will start at the 0 position in "dag", since that
			# is where we note all the nodes with no incoming arcs.
	closure = {}
	getClosure (dag, start, closure)
	return closure


def getClosure (
	dag,	# a digraph, represented as a list of lists, where:
		#	dag[0] = [ nodes with no incoming arcs ]
		#	and, for i > 0:
		#		dag[i] = [ nodes reached by an arc from node i ]
	i,	# integer identifying the node whose closure we should compute.
	closure	# the transitive closure as it has been built so far, in the
		#	form:  { TR : [ descendants ] }
	):
	# Purpose: compute the transitive closure for node "i" and all its
	#	descendants
	# Returns: nothing
	# Assumes: "dag" has no cycles, otherwise we generate bad results.
	# Effects: updates "closure" for node "i" and all its descendants
	# Throws: nothing

	if closure.has_key (i):		# if we've already computed this node,
		return			# then we don't need to do it again
	else:
		# copy the children of i, then compute and store the closure
		# for each of them.  The transitive closure of node i is the
		# union of the transitive closures of all its children.

		closure [i] = dag[i][:]
		for child in dag[i]:
			getClosure (dag, child, closure)
			for descendant in closure [child]:
				if not descendant in closure[i]:
					closure[i].append (descendant)
	return

# -Archive:---------------------------------------------------------------

# These methods are no longer used, but are retained here for now in case
# we need them again in the near future.  It should be safe to delete them
# in the next WTS iteration.

#	def old_getTransitiveClosure (self):
		# Purpose: return a tuple with two items: first, an ArcSet
		#	containing Arcs in the transitive closure of this
		#	Digraph; and second, a boolean flag which indicates
		#	whether (1) or not (0) we found a cycle in the Digraph.
		# Returns: see Purpose
		# Assumes: The Digraph has no actual arcs from a node to itself
		#	(these will not be recognized as a cycle, but the t.c.
		#	should still work okay).
		# Effects: Since the transitive closure is an expensive O(n^3)
		#	operation, we don't want to compute it any more often
		#	than we have to.  First, we check to see if the Digraph
		#	has changed.  If not, then the currently stored
		#	transitive closure is still valid, so just return it.
		#	Otherwise, we do need to recompute (and store) the
		#	transitive closure and note that no changes have been
		#	made since recomputing.
		# Throws: nothing
		# Notes: We use a standard Warshall's algorithm to compute the
		#	transitive closure of this Digraph, as documented in:
		#		pg 213 - Aho, Hopcroft, & Ullman (black book)
		#		pg 563 - Cormen, Leiserson, & Rivest (white bk)

		# if there have been no changes since last computing the
		# transitive closure, then just return the currently stored one

#		if self.changed == FALSE:
#			return (self.closure, self.hasCycle)

		# otherwise, we need to recompute the transitive closure.

#		self.old_seedClosure ()	# reset the t.c. to be known arcs

#		nodes = self.nodes.values ()	# get the list of all nodes in
						# this Digraph

#		self.hasCycle = FALSE		# assume there are no cycles

		# this is the standard Warshall's algorithm for computing t.c.

#		for mid_node in nodes:
#		    for from_node in nodes:
#			for to_node in nodes:

#			    if (from_node != to_node):

				# if there's not an Arc directly from
				#	from_node to to_node,
				# but there are Arcs from
				#	from_node to mid_node, and
				#	mid_node to to_node...

#				if self.closure.exists (
#					Arc.Arc (from_node, mid_node)) \
#				and self.closure.exists (
#					Arc.Arc (mid_node, to_node)) \
#				and not self.closure.exists (
#					Arc.Arc (from_node, to_node)):

						# then we know that there is a
						# path from:
						#	from_node to to_node,
						# so add an Arc to the
						# transitive closure to
						# represent it

#						self.closure.addArc (
#						Arc.Arc (from_node, to_node))
#			    else:
				# we need to see if we have a cycle.  Note that
				# we know that (from_node == to_node).

#				if (mid_node != from_node) \
#				and self.closure.exists (
#				    Arc.Arc (from_node, mid_node)) \
#				and self.closure.exists (
#				    Arc.Arc (mid_node, to_node)):
					# we have found a cycle
#					self.hasCycle = TRUE

#		self.changed = FALSE		# no changes since recompute
#		return (self.closure, self.hasCycle)

#	def old_seedClosure (self):		### internal only ###
		# Purpose: to seed the Digraph's transitive closure ArcSet with
		#	the known Arcs and with a self-referential Arc for each
		#	node in the Digraph
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		# reset the transitive closure to only contain the ArcSet of
		# known Arcs in the Digraph.  Then, add a self-referential Arc
		# for each node in the Digraph.

#		self.closure = copy.deepcopy (self.arcs)
#		for node in self.nodes.values ():
#			self.closure.addArc (Arc.Arc (node, node))
#		return

