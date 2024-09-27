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

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Local Controller')
    parser.add_argument('--config', type=str, default='./config/globalConfig.json')
    args = parser.parse_args()
    config_file = args.config
    config = json.load(open(config_file, 'r'))
    ASN = int(config['ASN'])
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
    print(f'Local topology transformed... Time: {end - start} ms')
    
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
            
    # 加载模型
    model = GraphNN.Net()
    model.eval()
    model.load_state_dict(torch.load('./model/4_Claranet_global_model_2.pth'))
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
                    print(f'Connected by {addr}')
                    data = conn.recv(1024)
                    print(f'data is {data!r}')
                    data = pickle.loads(data)
                    print(f'pickled data is {data}')
                    src = local_controller.global_topology.router_id_str_to_int[data['Router_id']]
                    next_hop = local_controller.global_topology.router_id_str_to_int[data['next_hop']]
                    dst = local_controller.global_topology.router_id_str_to_int[local_controller.global_topology.ip_router[data['IP_prefix']]]
                    input_data = [src, next_hop, dst]
                    print(f'input_data: {input_data}')
                    start = int(round(time.time() * 1000))
                    out = subModel2(input_data, embedding)
                    end = int(round(time.time() * 1000))
                    time_dict['inference_times'].append(end - start)
                    out = out.item()
                    out = int(out)
                    out = 200 - out                                                            
                    print(f'Dataset received...')
                    print(f'out: {out}')
                    print(f'Time: {end - start} ms')
                    conn.sendall(f'{out}'.encode())
                    count += 1
                    if count % 5 == 0:
                        time_dict['average_inference_time'] = sum(time_dict['inference_times']) / len(time_dict['inference_times'])
                        with open(f'./time_dict/{ASN}_time_dict.json', 'w') as f:
                            json.dump(time_dict, f)
            except Exception as e:
                print(f'Error: {e}')
    print('KeyboardInterrupt')