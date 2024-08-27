from GlobalTopology import GlobalTopology
from LocalController import LocalController
from AStopology import AStopology
import socket
import pickle

class GlobalController:
    '''
    Class for Global Controller. 
    '''
    
    '''
    Contructor for object of the class GlobalController. Creates the class variable "list_of_ASes" as an empty dictionary.
    '''
    def __init__(self):
        self.ASes = []
        self.global_topology = GlobalTopology()
        self.ASController_ip = dict()
        # self.load_global_info(TopoFromFile)
        # self.ip_router = TopoFromFile.ip_router
    
    def listen_local_topology(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            print(f'Listening on {host}:{port}')
            count = 0
            while count < len(self.ASes):
                try:
                    conn, addr = s.accept()
                    with conn:
                        print(f'Connected by {addr}')
                        data = conn.recv(1024)
                        received_data = AStopology()
                        received_data = pickle.loads(data)
                        self.global_topology.list_of_ASes[received_data.ASN] = received_data
                        print(f'Local topology of AS {received_data.ASN} received...')
                        count += 1
                        conn.sendall(f'Local topology of AS {received_data.ASN} received...'.encode())
                except Exception as e:
                    print(f'Error: {e}')
                    break
    





if __name__ == '__main__':
    
    # 构建全局拓扑基本信息
    global_controller = GlobalController()
    
    # 添加所有AS号
    global_controller.ASes.append(1)
    global_controller.ASes.append(2)
    
    # 添加域间链路信息(须手动逐个添加)
    global_controller.global_topology.cross_domain_links.append(['1.3', '2.3'])
    
    # 等待各个本地控制器上传本地拓扑信息
    global_controller.listen_local_topology('localhost', 2101)
    
    # 重构字符串id到整数id的映射
    router_count = 0
    for local_topology in global_controller.global_topology.list_of_ASes.values():
        print(f'local_topology.router_id_str_to_int: {local_topology.router_id_str_to_int}')
        for key, value in local_topology.router_id_str_to_int.items():
            print(f'key: {key}, value: {value}')
            local_topology.list_of_all_Nodes[value].RouterID = router_count
            global_controller.global_topology.router_id_str_to_int[key] = router_count
            global_controller.global_topology.router_id_int_to_str[router_count] = key
            
            router_count += 1
            
    # 初始化各个本地控制器ip
    global_controller.ASController_ip[1] = ['localhost', 2111]
    global_controller.ASController_ip[2] = ['localhost', 2211]

    # 生成全局拓扑
    global_controller.global_topology.generate_global_topology()
    print(f'Global topology generated...   done!')
    
    # 分发全局拓扑信息
    for key, value in global_controller.ASController_ip.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            while True:
                try:
                    s.connect((value[0], value[1]))
                    data = pickle.dumps(global_controller.global_topology)
                    # Send the size of the data first
                    s.sendall(len(data).to_bytes(4, 'big'))
                    # Then send the actual data
                    s.sendall(data)
                    
                    data = s.recv(1024)
                    print(f'Received: {data.decode()}')
                    break
                except Exception as e:
                    print(f'Error: {e}')
                    continue