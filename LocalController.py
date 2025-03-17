from AStopology import AStopology
from GlobalTopology import GlobalTopology
from Node import Node
from torch_geometric.data import Data
import json
import csv
import torch
import torch.nn.functional as F
import warnings
from tqdm import tqdm
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import socket
import pickle
import GraphNN
import argparse
import time
import keyboard
import math
import numpy as np
import networkx as nx

class LocalController:
    def __init__(self, ASN):
        self.local_topology = AStopology(ASN)
        self.global_topology = GlobalTopology()
        self.ip_router = dict()

    '''
    本地拓扑变换,rounds为迭代次数
    '''
    def message_passing(self, rounds=1):
        for _ in range(rounds):
            data, edge_to_node_index, edge_to_node = self.local_topology.message_passing()
        return data, edge_to_node_index, edge_to_node

    '''
    上传本地拓扑,返回本地的topology对象
    '''
    def upload_local_topology(self):
        return self.local_topology

    '''
    下载全局拓扑
    '''
    def download_global_topology(global_topology):
        self.global_topology = global_topology
        
    def print_local_topology_edge_links(self, router_distance_dict):
        # get edge nodes in str (same to config file)
        print('Local topology edge links:')
        edge_nodes = self.global_topology.get_edge_nodes()
        for node in router_distance_dict.keys():
            if node in edge_nodes:
                for neighbor in router_distance_dict[node].keys():
                    if neighbor in edge_nodes:
                        print(f'{node} -> {neighbor} : {router_distance_dict[node][neighbor]}')
        print('-----------------------------------')
            
    def print_global_topology_edge_links(self):
        edge_nodes = self.global_topology.get_edge_nodes()
        for AS in self.global_topology.list_of_ASes.values():
            print(f'AS {AS.ASN}')
            for node in AS.list_of_all_Nodes.values():
                router_name = self.global_topology.router_id_int_to_str[node.RouterID]
                if router_name in edge_nodes:
                    # print(f'Node {router_name}')
                    for neighbor in node.neighbors.keys():
                        neighbor_name = self.global_topology.router_id_int_to_str[neighbor]
                        # if neighbor in AS.router_id_int_to_str.keys():
                        #     neighbor_name = AS.router_id_int_to_str[neighbor]
                        #     # print(f'neighbor: {neighbor_name}')
                        if neighbor_name in edge_nodes and neighbor_name in AS.router_id_int_to_str.values():
                            print(f'{router_name} -> {neighbor_name} : {node.neighbors[neighbor][1]}')
            print('-----------------------------------')
            
    def local_topology_to_dict(self):
        local_topology_dict = dict()
        # print(f'local_topology.router_id_str_to_int: {self.local_topology.router_id_str_to_int}')
        # print(f'local_topology.router_id_int_to_str: {self.local_topology.router_id_int_to_str}')
        for node in self.local_topology.router_id_str_to_int.keys():
            local_topology_dict[node] = dict()
            for neighbor in self.local_topology.list_of_all_Nodes[self.local_topology.router_id_str_to_int[node]].neighbors.keys():
                if neighbor in self.local_topology.router_id_int_to_str.keys():
                    local_topology_dict[node][self.local_topology.router_id_int_to_str[neighbor]] = self.local_topology.list_of_all_Nodes[self.local_topology.router_id_str_to_int[node]].neighbors[neighbor][1]
        return local_topology_dict
    
    def local_topology_in_global_topology_to_dict(self):
        local_topology_in_global_topology_dict = dict()
        local_topology_in_global_topology = self.global_topology.list_of_ASes[self.local_topology.ASN]
        for node in local_topology_in_global_topology.router_id_str_to_int.keys():
            local_topology_in_global_topology_dict[node] = dict()
            for neighbor in local_topology_in_global_topology.list_of_all_Nodes[local_topology_in_global_topology.router_id_str_to_int[node]].neighbors.keys():
                if neighbor in local_topology_in_global_topology.router_id_int_to_str.keys():
                    local_topology_in_global_topology_dict[node][local_topology_in_global_topology.router_id_int_to_str[neighbor]] = local_topology_in_global_topology.list_of_all_Nodes[local_topology_in_global_topology.router_id_str_to_int[node]].neighbors[neighbor][1]
        return local_topology_in_global_topology_dict

def topo_dict_to_adj(topo_dict):
    # 初始化邻接矩阵
    adj = np.zeros((len(topo_dict), len(topo_dict)))
    node_index = dict()
    for i, key in enumerate(topo_dict.keys()):
        node_index[key] = i
    for key in topo_dict.keys():
        for neighbor in topo_dict[key].keys():
            adj[node_index[key]][node_index[neighbor]] = topo_dict[key][neighbor]
    return adj
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Local Controller')
    parser.add_argument('--config', type=str, default='./config/globalConfig.json')
    args = parser.parse_args()
    config_file = args.config
    config = json.load(open(config_file, 'r'))
    original_config_file = config_file[:-5] + '_ori.json'
    original_config = json.load(open(original_config_file, 'r'))
    original_router_distance_dict = original_config['router_distance_dict']
    ASN = int(config['ASN'])
    torch.manual_seed(1000)
    print(f"This is Local Controller {ASN}")
    router_name_set = config['router_name_set']
    router_distance_dict = config['router_distance_dict']
    ip_router = config['ip_router']
    global_controller_addr = config['global_controller_address']
    global_controller_listen_port = config['global_controller_listen_port']
    input_listening_port = config['input_listening_port']
    # 时间字典（用于记录每个事件的时间）
    time_dict = dict()
    time_dict['inference_times'] = list()
    # 构建本地拓扑结构
    # 根据AS号初始化本地控制器
    local_controller = LocalController(ASN)
    # 构建网桥名-网桥ID(int)的映射，通过LLDP协议获取网桥名然后将其映射到int类型上作为唯一id
    # router_name_set = ['1.1', '1.2', '1.3']
    for i in range(len(router_name_set)):
        local_controller.local_topology.router_id_str_to_int[router_name_set[i]] = i
        local_controller.local_topology.router_id_int_to_str[i] = router_name_set[i]
    # 以网桥ID为键，初始化所有网桥对象
    for key in local_controller.local_topology.router_id_str_to_int.keys():
        local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int[key]] = Node(local_controller.local_topology.router_id_str_to_int[key], local_controller.local_topology.ASN)
    # 将所有网桥构建全连接关系(实际上为BGP peer关系)，其中1表示两个网桥之间的链路权重，应当根据域内协议(如ospf)计算的链路权重进行设置
    # router_distance_dict = {'1.1': {'1.2': 1, '1.3': 1}, '1.2': {'1.1': 1, '1.3': 1}, '1.3': {'1.1': 1, '1.2': 1}}
    for key in router_distance_dict.keys():
        for neighbor in router_distance_dict[key].keys():
            local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int[key]].add_neighbor(local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int[neighbor]], router_distance_dict[key][neighbor])
    # 为所有主机指明所挂载的网桥
    for key, value in ip_router.items():
        local_controller.local_topology.ip_router[key] = value
    # local_controller.local_topology.ip_router['1.1.0.1'] = '1.1'
    # local_controller.local_topology.ip_router['1.1.0.2'] = '1.1'
    # local_controller.local_topology.ip_router['1.2.0.1'] = '1.2'
    # local_controller.local_topology.ip_router['1.2.0.2'] = '1.2'
    
    # 初始化全局拓扑结构
    local_controller.global_topology = GlobalTopology()
    
    # 本地拓扑变换
    start = int(round(time.time() * 1000))
    local_controller.message_passing(3)
    end = int(round(time.time() * 1000))
    time_dict['local_topo_trans'] = end - start
    print(f'Local topology transformed.')
    # print(f'Local topology transformed... Time: {end - start} ms')
    
    # 将变换后的本地拓扑上传联邦控制器
    global_controller_ip = global_controller_addr['ip']
    global_controller_port = global_controller_addr['port']
    # global_controller_ip = 'localhost'
    # global_controller_port = 2101
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((global_controller_ip, global_controller_port))
        s.sendall(pickle.dumps(local_controller.local_topology))
        data = s.recv(1024)
        print(f'Received: {data.decode()}')
        
    # 接收联邦控制器发送的全局拓扑
    # global_controller_listen_port = 2111
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', global_controller_listen_port))
        s.listen()
        count = 0
        try:
            conn, addr = s.accept()
            with conn:
                print(f'Connected by {addr}')
                data_size = int.from_bytes(conn.recv(4), 'big')
                # Now read exactly that amount of data
                data = conn.recv(data_size)
                while len(data) < data_size:
                    data += conn.recv(data_size - len(data))
                local_controller.global_topology = pickle.loads(data)
                print(f'Global topology received...')
                conn.sendall(f'{local_controller.local_topology.ASN} Controller: Global topology received...'.encode())
        except Exception as e:
            print(f'Error: {e}')
            
    # 打印本地拓扑的边链路
    # local_controller.print_local_topology_edge_links(router_distance_dict)
    # 打印全局拓扑的边链路
    # local_controller.print_global_topology_edge_links()
    # 打印本地拓扑字典
    # print(f"local_topology_dict: {router_distance_dict}")
    local_topology_dict = local_controller.local_topology_to_dict()
    # print(f'local_topology_in_global_topology_dict: {local_topology_dict}')
    ori_topo_dict = original_router_distance_dict
    # 将本地拓扑字典转换为邻接矩阵
    local_adj = topo_dict_to_adj(router_distance_dict)
    # print(f'local_adj: {local_adj}')
    local_in_global_adj = topo_dict_to_adj(local_topology_dict)
    # print(f'local_in_global_adj: {local_in_global_adj}')
    ori_adj = topo_dict_to_adj(ori_topo_dict)
    # matrix to nx graph
    local_G = nx.from_numpy_array(local_adj)
    local_in_global_G = nx.from_numpy_array(local_in_global_adj)
    ori_G = nx.from_numpy_array(ori_adj)
    # 计算矩阵余弦相似度
    # cos_sim = np.dot(local_adj.flatten(), local_in_global_adj.flatten()) / (np.linalg.norm(local_adj.flatten()) * np.linalg.norm(local_in_global_adj.flatten))
    # print(f'cosine similarity: {cos_sim}')
    # cos_sim_ori = np.dot(local_in_global_adj.flatten(), ori_adj.flatten()) / (np.linalg.norm(local_in_global_adj.flatten()) * np.linalg.norm(ori_adj.flatten))
    # print(f'cosine similarity with original: {cos_sim_ori}')
    # 计算欧式距离
    euclidean_distance = np.linalg.norm(local_adj - local_in_global_adj)
    print(f'euclidean distance: {euclidean_distance}')
    euclidean_distance_ori = np.linalg.norm(local_in_global_adj - ori_adj)
    print(f'euclidean distance with original: {euclidean_distance_ori}')
    # 计算皮尔逊相关系数
    pearson_correlation, _ = np.corrcoef(local_adj.flatten(), local_in_global_adj.flatten())
    print(f'pearson correlation: {pearson_correlation[1]}')
    pearson_correlation_ori, _ = np.corrcoef(local_in_global_adj.flatten(), ori_adj.flatten())
    print(f'pearson correlation with original: {pearson_correlation_ori[1]}')
    # 计算最大共同子图比例
    max_common_subgraph = nx.graph_edit_distance(local_G, local_in_global_G)
    max_size = max(len(local_G.nodes) + len(local_G.edges), len(local_in_global_G.nodes) + len(local_in_global_G.edges))
    max_common_subgraph_ratio = 1 - max_common_subgraph / max_size 
    print(f'max common subgraph ratio: {max_common_subgraph_ratio}')
    max_common_subgraph_ori = nx.graph_edit_distance(local_in_global_G, ori_G)
    max_size_ori = max(len(local_in_global_G.nodes) + len(local_in_global_G.edges), len(ori_G.nodes) + len(ori_G.edges))
    max_common_subgraph_ratio_ori = 1 - max_common_subgraph_ori / max_size_ori
    print(f'max common subgraph ratio with original: {max_common_subgraph_ratio_ori}')
    # 计算SVD相似度
    u, s, vh = np.linalg.svd(local_adj)
    u_in_global, s_in_global, vh_in_global = np.linalg.svd(local_in_global_adj)
    svd_similarity = np.dot(u.flatten(), u_in_global.flatten()) / (np.linalg.norm(u) * np.linalg.norm(u_in_global))
    print(f'SVD similarity: {svd_similarity}')
    u_ori, s_ori, vh_ori = np.linalg.svd(ori_adj)
    svd_similarity_ori = np.dot(u_in_global.flatten(), u_ori.flatten()) / (np.linalg.norm(u_in_global) * np.linalg.norm(u_ori))
    print(f'SVD similarity with original: {svd_similarity_ori}')
    
    # 将全局拓扑中的本地拓扑转换为字典
    # local_topology_in_global_topology_dict = local_controller.local_topology_in_global_topology_to_dict()
    # print(f'local_topology_in_global_topology_dict: {local_topology_in_global_topology_dict}')
    # 加载模型
    model = GraphNN.Net()
    model.eval()
    model.load_state_dict(torch.load('./model/global_model_9.pth'))
    subModel1 = GraphNN.subNet1()
    subModel1.eval()
    subModel1.conv1 = model.conv1
    subModel1.conv2 = model.conv2
    subModel1.lstm_cell = model.lstm_cell
    
    subModel2 = GraphNN.subNet2()
    subModel2.eval()
    subModel2.linear0 = model.linear0
    subModel2.linear1 = model.linear1
    subModel2.linear2 = model.linear2
    subModel2.linear3 = model.linear3
    
    embedding = subModel1(local_controller.global_topology)
    # 监听BGP控制器发来的数据
    # input_listening_port = 2121
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', input_listening_port))
        s.listen()
        count = 0
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    # print(f'Connected by {addr}')
                    data = conn.recv(1024)
                    # print(f'data is {data!r}')
                    data = pickle.loads(data)
                    # print(f'pickled data is {data}')
                    print(f"received prefix: {data['IP_prefix']}")
                    src = local_controller.global_topology.router_id_str_to_int[data['Router_id']]
                    next_hop = local_controller.global_topology.router_id_str_to_int[data['next_hop']]
                    dst = local_controller.global_topology.router_id_str_to_int[local_controller.global_topology.ip_router[data['IP_prefix']]]
                    input_data = [src, next_hop, dst]
                    # print(f'input_data: {input_data}')
                    start = int(round(time.time() * 1000))
                    out = subModel2(input_data, embedding)
                    end = int(round(time.time() * 1000))
                    # time_dict['inference_times'].append(end - start)
                    out = out.item()
                    out = int(out)
                    # out = 300 - out
                    if out < 0:
                        out = 0                                          
                    # print(f'Data received...')
                    print(f'start time: {start}')
                    print(f'local preference: {out}')
                    print(f'end time: {end}')
                    print(f'Time: {end - start} ms')
                    print(f'--------------------------------------------------')
                    # 输出日志到文件
                    with open(f'./logs/{ASN}_local_controller.log', 'a') as f:
                        f.write(f'received prefix: {data["IP_prefix"]}\n')
                        f.write(f'start time: {start}\n')
                        f.write(f'local preference: {out}\n')
                        f.write(f'end time: {end}\n')
                        f.write(f'Time: {end - start} ms\n')
                        f.write(f'--------------------------------------------------\n')
                    conn.sendall(f'{out}'.encode())
                    # count += 1
                    # if count % 5 == 0:
                    #     time_dict['average_inference_time'] = sum(time_dict['inference_times']) / len(time_dict['inference_times'])
                    #     with open(f'./time_dict/{ASN}_time_dict.json', 'w') as f:
                    #         json.dump(time_dict, f)
            except Exception as e:
                print(f'Error: {e}')
    print('KeyboardInterrupt')