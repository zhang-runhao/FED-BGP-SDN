from LocalController import LocalController
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

if __name__ == '__main__':
    
    # 构建本地拓扑结构，一下信息通过LLDP协议获取
    # 根据AS号初始化本地控制器
    local_controller = LocalController(2)
    # 构建网桥名-网桥ID(int)的映射，通过LLDP协议获取网桥名然后将其映射到int类型上作为唯一id
    local_controller.local_topology.router_id_str_to_int['2.1'] = 0
    local_controller.local_topology.router_id_int_to_str[0] = '2.1'
    local_controller.local_topology.router_id_str_to_int['2.2'] = 1
    local_controller.local_topology.router_id_int_to_str[1] = '2.2'
    local_controller.local_topology.router_id_str_to_int['2.3'] = 2
    local_controller.local_topology.router_id_int_to_str[2] = '2.3'
    # 以网桥ID为键，初始化所有网桥对象
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.1']] = Node(local_controller.local_topology.router_id_str_to_int['2.1'], 2)
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.2']] = Node(local_controller.local_topology.router_id_str_to_int['2.2'], 2)
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.3']] = Node(local_controller.local_topology.router_id_str_to_int['2.3'], 2)
    # 将所有网桥构建全连接关系(实际上为BGP peer关系)，其中1表示两个网桥之间的链路权重，应当根据域内协议(如ospf)计算的链路权重进行设置
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.1']].add_neighbor(local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.2']], 1)
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.1']].add_neighbor(local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.3']], 1)
    local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.2']].add_neighbor(local_controller.local_topology.list_of_all_Nodes[local_controller.local_topology.router_id_str_to_int['2.3']], 1)
    # 为所有主机指明所挂载的网桥
    local_controller.local_topology.ip_router['2.1.0.1'] = '2.1'
    local_controller.local_topology.ip_router['2.1.0.2'] = '2.1'
    local_controller.local_topology.ip_router['2.2.0.1'] = '2.2'
    local_controller.local_topology.ip_router['2.2.0.2'] = '2.2'
    
    # 构建全局拓扑结构
    local_controller.global_topology = GlobalTopology()
    
    # 本地拓扑变换
    local_controller.message_passing(3)
    
    # 将变换后的本地拓扑上传联邦控制器
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', 2101))
        s.sendall(pickle.dumps(local_controller.local_topology))
        data = s.recv(1024)
        print(f'Received: {data.decode()}')
        
    # 接收联邦控制器发送的全局拓扑
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 2211))
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
    
    # 监听BGP控制器发来的数据
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 2221))
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    print(f'Connected by {addr}')
                    data = conn.recv(1024)
                    data = pickle.loads(data)
                    src = local_controller.global_topology.router_id_str_to_int[data['Router_id']]
                    next_hop = local_controller.global_topology.router_id_str_to_int[data['next_hop']]
                    dst = local_controller.global_topology.router_id_str_to_int[local_controller.global_topology.ip_router[data['IP_prefix']]]
                    input_data = [src, next_hop, dst]
                    out = model(local_controller.global_topology, input_data)
                    out = out.item()
                    out = int(out)
                    out = 100 - out                                                            
                    print(f'Dataset received...')
                    conn.sendall(f'{out}'.encode())
            except Exception as e:
                print(f'Error: {e}')
    