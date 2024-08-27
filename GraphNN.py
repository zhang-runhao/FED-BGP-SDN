from torch_geometric.nn import MessagePassing
from torch_geometric.utils import add_self_loops, degree
from torch_geometric.nn import SAGEConv
from torch_geometric.nn import global_mean_pool as gap, global_max_pool as gmp
import torch.nn.functional as F
import torch.nn as nn
import torch


# 本地拓扑变换信息传递单元
class LocalEdgeConv(MessagePassing):
    def __init__(self):
        super(LocalEdgeConv, self).__init__(aggr='mean', node_dim=-1)  # "add" aggregation.

    def forward(self, x, edge_index):
        # x has shape [N, in_channels]
        # edge_index has shape [2, E]

        # Step 1: Add self-loops to the adjacency matrix.
        edge_index, _ = add_self_loops(edge_index, num_nodes=x.size(0))
        # print(f'edge_index: {edge_index}')
        # Step 2: Start propagating messages.
        return self.propagate(edge_index, size=(x.size(0), x.size(0)), x=x)

    def message(self, x_i, x_j):
        # x_j has shape [E, in_channels]
        return (x_i * 10 + x_j) / 10  # Normalize node features.
        

NODE_FEATURE_EMBED_DIM = 1
NODE_NUM_DIM = 64
class Net(torch.nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = SAGEConv(NODE_FEATURE_EMBED_DIM, 16)
        self.conv2 = SAGEConv(16, NODE_NUM_DIM)
        self.lstm_cell = nn.LSTMCell(NODE_NUM_DIM * 3, NODE_NUM_DIM)
        self.linear0 = nn.Linear(6 * NODE_NUM_DIM, 32)
        self.linear1 = nn.Linear(32, 16)
        self.linear2 = nn.Linear(16, 8)
        self.linear3 = nn.Linear(8, 1)


    def forward(self, global_topology, routing_table_item):
        data, edge_to_node_index, edge_to_node = global_topology.transpose_torch_geometric_data()
        x, edge_index = data.x, data.edge_index
        # print(f'x.shape: {x.shape}')
        x = x.unsqueeze(1)
        # print(f'x.shape: {x.shape}')
        x = F.relu(self.conv1(x, edge_index))
        # print(f'x.shape: {x.shape}')
        # x_g1 = gap(x, torch.zeros(1, dtype=torch.long))
        # print(f'x_g1.shape: {x_g1.shape}')
        x = F.relu(self.conv2(x, edge_index))
        # print(f'x.shape: {x.shape}')
        x_g = gap(x, torch.zeros(1, dtype=torch.long))
        x_g = x_g.squeeze(0)
        # print(f'x_g.shape: {x_g.shape}')
        original_edge_index_source, original_edge_index_target = self.one_hot_encode(data, edge_to_node_index, edge_to_node)
        # print(f'original_edge_index_source.shape: {original_edge_index_source.shape}')
        # print(f'original_edge_index_target.shape: {original_edge_index_target.shape}')

        x = torch.cat([x, original_edge_index_source, original_edge_index_target], dim=-1)
        # print(f'x.shape: {x.shape}')
        hx = torch.randn(NODE_NUM_DIM)
        cx = torch.randn(NODE_NUM_DIM)
        for i in range(len(data.x)):
            hx, cx = self.lstm_cell(x[i], (hx, cx))
        # print(f'hx.shape: {hx.shape}')
        # print(f'cx.shape: {cx.shape}')

        src = torch.eye(NODE_NUM_DIM)[routing_table_item[0]]
        path = torch.eye(NODE_NUM_DIM)[routing_table_item[1]]
        dst = torch.eye(NODE_NUM_DIM)[routing_table_item[2]]
        x = torch.cat([cx, hx, x_g, src, path, dst], dim=-1)
        # print(f'x.shape: {x.shape}')
        x = F.relu(self.linear0(x))
        # print(f'x.shape: {x.shape}')
        x = F.relu(self.linear1(x))
        # print(f'x.shape: {x.shape}')
        x = F.relu(self.linear2(x))
        # print(f'x.shape: {x.shape}')
        x = F.relu(self.linear3(x))
        # print(f'x.shape: {x.shape}')
        # print(f'x: {x}')
        return x

    # 对边的源节点和目标节点进行one-hot编码，返回源节点和目标节点的one-hot编码组
    def one_hot_encode(self, data, edge_to_node_index, edge_to_node):
        original_edge_index_source = []
        original_edge_index_target = []
        for i in range(len(data.x)):
            original_edge_index_source.append(edge_to_node[edge_to_node_index[i]][0])
            original_edge_index_target.append(edge_to_node[edge_to_node_index[i]][1])
        for index, value in enumerate(original_edge_index_source):
            original_edge_index_source[index] = torch.eye(NODE_NUM_DIM)[value]
        for index, value in enumerate(original_edge_index_target):
            original_edge_index_target[index] = torch.eye(NODE_NUM_DIM)[value]
        original_edge_index_source = torch.stack(original_edge_index_source)
        original_edge_index_target = torch.stack(original_edge_index_target)
        return original_edge_index_source, original_edge_index_target
        


if __name__ == '__main__':
    from GlobalTopology import GlobalTopology
    from GlobalController import GlobalController
    from FileLoader import TopoFromFile
    from LocalController import LocalController
    topo = TopoFromFile('NSFnet.xml')
    global_controller = GlobalController(topo)
    for ASN in global_controller.ASes:
        global_controller.global_topology.list_of_ASes[ASN] = LocalController(ASN, topo).local_topology
    global_controller.global_topology.generate_global_topology()
    model = Net()
    model(global_controller.global_topology, [1,2,3])