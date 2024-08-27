class Node:
	''' 
	Class for Nodes (i.e., routers are represented as single nodes). 
	A Node can own IP prefixes, have connections to other Nodes.
	In this class, there exist methods related to 

	class variables: 
        (a) RouterID:           interger(mandatory, given upon creation) - id of the node corresponding to its RouterID
		(b) ASN: 				integer (mandatory, given upon creation) - id of the node corresponding to its AS number
		(c) IPprefix: 			set (initially empty) - set of prefixes owned by the Node
		(d) neighbors: 		    dictionary (initially empty) - dictionary with (i) keys the RouterIDs of neighbors and (ii) values tuple (the objects of type Node, linkAttr)
        (e) type:               integer (initially 1) - type of the node {1, -1} means {intern, border}
	'''

	'''
	Contructor for object of the class Node. Creates the class variables from the given arguments, and defines the variable types for the initially epmty class variables.

	Input arguments:
        (a) RouterID:   integer
		(b) ASN:		integer
	'''
	def __init__(self, RouterID, ASN):
		self.RouterID = RouterID
		self.ASN = ASN
		self.IPprefix = set()
		self.neighbors = {}
		self.type = 1

	def set_RouterID(self, RouterID):
		self.RouterID = RouterID

	'''
	Checks if the Node exists in the "neighbors" dictionary.
	
	Returns:
		TRUE if it exists, FALSE otherwise
	'''
	def has_neighbor(self,RouterID):
		if RouterID in self.neighbors.keys():
			return True
		else:
			return False

	'''
	Adds the given Node to the dictionary ("neighbors" class variable) for the neighbors
	
	IF the given Node does not exist in the "neighbors" dictionary, 
	THEN 	(i) add the RouterID as the key to the "neighbors" dictionary, 
			(ii) IF the given Node is not of the same AS,
                 THEN   set type to border(-1)
            (iii) recall add_neighbor by the given Node to complete the relation

	Input arguments:
		(a) Node: the neighbor to be added
        (b) linkAttr: a tuple represent hops or delays etc. (currently only hops e.g. (1) means one hop away)
	'''
	def add_neighbor(self, Node, linkAttr):
		if not self.has_neighbor(Node.RouterID):
			self.neighbors[Node.RouterID] = (Node, linkAttr)
			if Node.ASN != self.ASN:
				self.type = -1
			Node.add_neighbor(self, linkAttr)

	'''
	Change the linkAttr of the given Node in the dictionary ("neighbors" class variable) for the neighbors
	'''
	def change_Attr(self, RouterID, linkAttr):
		if self.has_neighbor(RouterID):
			self.neighbors[RouterID] = (self.neighbors[RouterID][0], linkAttr)
		else:
			raise ValueError("The given Node does not exist in the neighbors dictionary")