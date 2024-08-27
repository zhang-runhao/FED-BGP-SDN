import torch
import numpy as np
from torch_geometric.data import Data
from Node import Node


MAX_ROUTERS = 1000
class Topology:
	''' 
	Class for network topology of ASes, where Routers are represented as single nodes (Nodes). 
	An topology contais a list of the member nodes (objects of type Node).
	In this class, there exist methods related to (a) adding member nodes and links, 

	class variables: 

		(a) list_of_all_Nodes:	dictionary (initially empty) - dictionary with (i) keys the RouterID of member nodes and (ii) values the objects of type Node (corresponding to each member node)
	'''


	'''
	Contructor for object of the class BGPtopology. Creates the class variable "list_of_all_BGP_nodes" as an empty dictionary.
	'''
	def __init__(self):
		self.list_of_all_Nodes = {}
		self.routerID_to_edge_index = {}
		self.edge_index_to_routerID = {}

	'''
	construct dict for routerID to edge_index and edge_index to routerID
	'''
	def construct_ID_change_dict(self):
		count = 0
		for node in self.list_of_all_Nodes.values():
			self.routerID_to_edge_index[node.RouterID] = count
			self.edge_index_to_routerID[count] = node.RouterID
			count += 1
		

	def encode_routerID(self):
		for node in self.list_of_all_Nodes.values():
			node.set_RouterID(self.routerID_to_edge_index[node.RouterID])
			node.neighbors = {self.routerID_to_edge_index[k]: v for k, v in node.neighbors.items()}
		self.list_of_all_Nodes = {self.routerID_to_edge_index[k]: v for k, v in self.list_of_all_Nodes.items()}
		

	def decode_routerID(self):
		for node in self.list_of_all_Nodes.values():
			node.set_RouterID(self.edge_index_to_routerID[node.RouterID])
			node.neighbors = {self.edge_index_to_routerID[k]: v for k, v in node.neighbors.items()}
		self.list_of_all_Nodes = {self.edge_index_to_routerID[k]: v for k, v in self.list_of_all_Nodes.items()}

	'''
	Checks if the given node exists in the "list_of_all_Nodes" dictionary.
	
	Input argument:
		(a) RouterID: the RouterID of the node to be checked

	Returns:
		TRUE if it exists, FALSE otherwise
	'''
	def has_node(self, RouterID):
		if RouterID in self.list_of_all_Nodes.keys():
			return True
		else:
			return False

	'''
	Return a node (i.e. the Node object) belonging to the AS.
	
	IF the given node exists in the "list_of_all_Nodes" dictionary, 
	THEN return the node
	
	Input argument:
		(a) RouterID: the RouterID of the node to be returned

	Returns:
		A Node object corresponding to the given RouterID
	'''
	def get_node(self, RouterID):
		if self.has_node(RouterID):
			return self.list_of_all_Nodes[RouterID]

	'''
	Add a node to the AS, i.e., to the dictionary "list_of_all_Nodes".
	
	IF the given node does not exist in the "list_of_all_Nodes" dictionary, 
	THEN add the node

	Input argument:
		(a) RouterID: the RouterID of the node to be added
	'''
	def add_node(self, RouterID):
		if not self.has_node(RouterID):
			self.list_of_all_Nodes[RouterID] = Node(RouterID, self.ASN)

	'''
	change the topo to torch_geometric.data.Data
	'''
	def to_torch_geometric_data(self):

		edge_index = []
		edge_attr = []
		index_matrix = np.full((MAX_ROUTERS, MAX_ROUTERS), -1, dtype=int)
		count = 0
		for node in self.list_of_all_Nodes.values():
			for neighbor in node.neighbors.values():
				edge_index.append([node.RouterID, neighbor[0].RouterID])
				edge_attr.append(neighbor[1])
				if index_matrix[node.RouterID][neighbor[0].RouterID] == -1:
					index_matrix[node.RouterID][neighbor[0].RouterID] = index_matrix[neighbor[0].RouterID][node.RouterID] = count
					# print(f'index_matrix[{node.RouterID}][{neighbor[0].RouterID}] = {count}')
					count += 1
		edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
		edge_attr = torch.tensor(edge_attr, dtype=torch.float)
		x = torch.tensor([node.RouterID for node in self.list_of_all_Nodes.values()], dtype=torch.float)
		data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
		return data, index_matrix

	'''
	transpose topo of torch_geometric.data.Data which means exchange the nodes and edges
	'''
	def transpose_torch_geometric_data(self):
		original_data, index_matrix = self.to_torch_geometric_data()
		# print(f'index_matrix: {index_matrix}')
		edge_index = []
		x = []
		edge_to_node_index = []  # 按次序记录新图的节点来自原图的边序号
		edge_to_node = {} # 记录原图的边序号对应的原图的两个节点(key: edge_to_node_index, value: [RouterID1, RouterID2])
		# 遍历原始图中的每一条边
		# print(f'original_data.edge_index: {original_data.edge_index}')
		for i in range(original_data.edge_index.size(-1)):
			current_index = index_matrix[original_data.edge_index[0][i]][original_data.edge_index[1][i]]
			if current_index not in edge_to_node_index:
				edge_to_node_index.append(current_index)
				# 记录新图节点来自原图的哪条边(用连接的路由器标记)
				edge_to_node[current_index] = [original_data.edge_index[0][i].item(), original_data.edge_index[1][i].item()]
				# 为新图的节点添加属性
				x.append(original_data.edge_attr[i])
				# 为新图添加边
			# 查看原图中这个边对应的两个节点的所有邻居
			for node in self.list_of_all_Nodes[original_data.edge_index[0][i].item()].neighbors.values():
				next_index = index_matrix[original_data.edge_index[0][i]][node[0].RouterID]
				if next_index not in edge_to_node_index:
					# 添加节点
					edge_to_node_index.append(next_index)
					edge_to_node[next_index] = [original_data.edge_index[0][i].item(), node[0].RouterID]
					x.append(node[1])
				if [current_index, next_index] not in edge_index and current_index != next_index:
					# 添加边
					edge_index.append([current_index, next_index])
			for node in self.list_of_all_Nodes[original_data.edge_index[1][i].item()].neighbors.values():
				next_index = index_matrix[original_data.edge_index[1][i]][node[0].RouterID]
				if next_index not in edge_to_node_index:
					# 添加节点
					edge_to_node_index.append(next_index)
					edge_to_node[next_index] = [original_data.edge_index[1][i].item(), node[0].RouterID]
					x.append(node[1])
				if [current_index, next_index] not in edge_index and current_index != next_index:
					# 添加边
					edge_index.append([current_index, next_index])
		edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
		x = torch.tensor(x, dtype=torch.float)
		data = Data(x=x, edge_index=edge_index)
		return data, edge_to_node_index, edge_to_node

	'''
	refresh the Attr of the original graph
	'''
	def refresh_edge_attr(self, data, edge_to_node_index, edge_to_node):
		for index, edge_index in enumerate(edge_to_node_index):
			RouterID1 = edge_to_node[edge_index][0]
			RouterID2 = edge_to_node[edge_index][1]
			self.list_of_all_Nodes[RouterID1].change_Attr(RouterID2, data.x[index].item())
			self.list_of_all_Nodes[RouterID2].change_Attr(RouterID1, data.x[index].item())
		return self
