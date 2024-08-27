from Topology import Topology
from GraphNN import LocalEdgeConv
from collections import defaultdict

class AStopology(Topology):

	''' 
	Class for network topology of ASes, where Routers are represented as single nodes (Nodes). 
	An AStopology contais its id and a list of the member nodes (objects of type Node).
	In this class, there exist methods related to (a) adding member nodes and links, 

	class variables: 
        (a) ASN:                interger(mandatory, given upon creation) - AS number of the AS
		(b) list_of_all_Nodes:	dictionary (initially empty) - dictionary with (i) keys the RouterID of member nodes and (ii) values the objects of type Node (corresponding to each member node)
	'''


	'''
	Contructor for object of the class BGPtopology. Creates the class variable "list_of_all_BGP_nodes" as an empty dictionary.
	'''
	def __init__(self, ASN=None):
		super().__init__()
		self.ASN = ASN
		self.ip_router = dict()
		self.router_id_str_to_int = dict()
		self.router_id_int_to_str = dict()
		self.ip_prefix_to_router_id_str = dict()

	'''
	AStopo message passing
	'''
	def message_passing(self):
		if len(self.list_of_all_Nodes) == 1:
			return self.transpose_torch_geometric_data()
		data, edge_to_node_index, edge_to_node = self.transpose_torch_geometric_data()
		conv = LocalEdgeConv()
		out = conv.forward(data.x, data.edge_index)
		data.x = out
		self.refresh_edge_attr(data, edge_to_node_index, edge_to_node)
		return data, edge_to_node_index, edge_to_node