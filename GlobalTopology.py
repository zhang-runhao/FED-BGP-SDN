from Topology import Topology

class GlobalTopology(Topology) :
    '''
    Class for Global Topology. 
    '''
    
    '''
    Contructor for object of the class GlobalTopology. Creates the class variable "list_of_all_Nodes" as an empty dictionary.
    '''
    def __init__(self):
        super().__init__()
        self.list_of_ASes = {}
        self.cross_domain_links = []
        self.router_id_str_to_int = dict()
        self.router_id_int_to_str = dict()
        self.ip_router = dict()
    
    '''
    generate the global topology
    '''
    def generate_global_topology(self):
        # 添加所有的节点
        for AS in self.list_of_ASes.values():
            for node in AS.list_of_all_Nodes.values():
                self.list_of_all_Nodes[node.RouterID] = node
            for key, value in AS.ip_router.items():
                self.ip_router[key] = value
        # 补充跨域链路
        self.add_cross_domain_links()
    
    '''
    add cross domain links
    '''
    def add_cross_domain_links(self):
        for link in self.cross_domain_links:
            self.list_of_all_Nodes[self.router_id_str_to_int[link[0]]].add_neighbor(self.list_of_all_Nodes[self.router_id_str_to_int[link[1]]], 1)
        