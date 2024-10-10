import json

class routerConfig:
    def __init__(self) -> None:
        self.global_config = {}
        self.neighbors = []
        self.policy_definitions = {}
    
    def outputConfig(self, topoName):
        with open('config\\' + topoName + '\config' + self.global_config['router_id'] + '.conf', 'w') as f:
            f.write('[global.config]\n')
            f.write('\tas = %s\n' % self.global_config['as'])
            f.write('\trouter_id = \"%s\"\n' % self.global_config['router_id'])
            f.write('\t[global.apply-policy.config]\n')
            f.write('\t\texport-policy-list = %s\n' % self.global_config['export_policy_list'])
            f.write('[[neighbors]]\n')
            for neighbor in self.neighbors:
                f.write('\t[neighbors.config]\n')
                f.write('\t\tneighbor-address = \"%s\"\n' % neighbor['neighbor_address'])
                f.write('\t\tlocal-as = %s\n' % neighbor['local_as'])
                f.write('\t\tpeer-as = %s\n' % neighbor['peer_as'])
                f.write('\t\t[[neighbors.afi-safis]]\n')
                f.write('\t\t\t[neighbors.afi-safis.config]\n')
                f.write('\t\t\tafi-safi-name = \"%s\"\n' % neighbor['afi_safi_name'])
            f.write('[[policy-definitions]]\n')
            f.write('\tname = \"%s\"\n' % self.policy_definitions['name'])
            f.write('\t[[policy-definitions.statements]]\n')
            f.write('\t\t[policy-definitions.statements.actions.bgp-actions]\n')
            f.write('\t\t\tset-next-hop = \"%s\"\n' % self.policy_definitions['set_next_hop'])
            
if __name__ == '__main__':
    Ases = ['1', '2', '3', '4']
    topoName = 'topo4as20sw'
    config = {}
    routerConfigList = []
    config['asConfigs'] = []
    routerDict = {}
    for asn in Ases:
        with open('config/'+ topoName + '/asConfig' + asn + '.json', 'r') as f:
            config['asConfigs'].append(json.load(f))
    with open('config/' + topoName + '/globalConfig.json', 'r') as f:
        config['globalConfig'] = json.load(f)
    for asConfig in config['asConfigs']:
        for router in asConfig['router_name_set']:
            routerDict[router] = asConfig['ASN']
    # print(config)
    for asConfig in config['asConfigs']:
        for router in asConfig['router_name_set']:
            rc = routerConfig()
            rc.global_config['as'] = asConfig['ASN']
            rc.global_config['router_id'] = router
            rc.global_config['export_policy_list'] = ["policy1"]
            for key in asConfig['router_distance_dict'][router].keys():
                neighbor = {}
                neighbor['neighbor_address'] = "localhost"
                neighbor['local_as'] = asConfig['ASN']
                neighbor['peer_as'] = asConfig['ASN']
                neighbor['afi_safi_name'] = 'ipv4-unicast'
                rc.neighbors.append(neighbor)
            for link in config['globalConfig']['cross_domain_links']:
                if link[0] == router:
                    neighbor = {}
                    neighbor['neighbor_address'] = config['globalConfig']["ASController_listen_addresses"][str(routerDict[link[1]])]["ip"]
                    neighbor['local_as'] = asConfig['ASN']
                    neighbor['peer_as'] = routerDict[link[1]]
                    neighbor['afi_safi_name'] = 'ipv4-unicast'
                    rc.neighbors.append(neighbor)
            rc.policy_definitions['name'] = 'policy1'
            rc.policy_definitions['set_next_hop'] = 'self'
            routerConfigList.append(rc)
            
    for rc in routerConfigList:
        rc.outputConfig(topoName)