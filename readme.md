# local preference推理代码实现
## 接口文件

需要调用的文件主要有以下两个
- GlobalController：联邦控制器，通过每个本地控制器上传的已变换的本地拓扑计算全局拓扑结构，而后分发给每个本地控制哎
- LocalController：本地控制器，根据LLDP收集的本地拓扑信息构建本地拓扑结构，上传给联邦控制器并获得全局拓扑，而后监听BGP参数计算消息调用训练好的模型推理出local preference值

调用命令如下(分别在不同的主机（模拟环境为不同的cmd窗口）执行以下命令)

```bash
# 主机（窗口）1 执行全局控制器 .\config\globalConfig.json为配置文件
python .\GlobalController.py --config .\config\globalConfig.json
# 主机（窗口）2-n 执行各域本地控制器 .\config\asConfig1.json为配置文件
python .\LocalController.py --config .\config\asConfig1.json
# 主机（窗口）2-n 执行各域本地控制器 .\config\asConfig2.json为配置文件
python .\LocalController.py --config .\config\asConfig2.json
```



### globalConfig.json

```json
{
    //添加域间链路信息[网桥名1，网桥名2]...
    "cross_domain_links": [
        ["1.3", "2.3"]
    ],
    //添加监听本地控制器发送的拓扑的IP地址和端口号
    "local_topo_listen_address": {
        "ip": "localhost",
        "port": 2101
    },
    //添加所有相关域的域号和对应控制器的IP地址及端口号
    "ASController_listen_addresses": {
        "1": {
            "ip": "localhost",
            "port": 2111
        },
        "2": {
            "ip": "localhost",
            "port": 2211
        }
    }
}
```

### asConfig1.json

```json
{
    //添加域号
    "ASN": 1,
    //添加所有域内网桥
    "router_name_set": [
        "1.1",
        "1.2",
        "1.3"
    ],
    //添加经过域内算法得到的网桥间的路由距离
    "router_distance_dict": {
        "1.1": {
            "1.2": 1,
            "1.3": 1
        },
        "1.2": {
            "1.1": 1,
            "1.3": 1
        },
        "1.3": {
            "1.1": 1,
            "1.2": 1
        }
    },
    //添加所有主机挂载的网桥信息，键为主机地址，值为网桥名
    "ip_router": {
        "1.1.0.1": "1.1",
        "1.1.0.2": "1.1",
        "1.2.0.1": "1.2",
        "1.2.0.2": "1.2"
    },
    //添加全局控制器的IP地址及端口号
    "global_controller_address": {
        "ip": "localhost",
        "port": 2101
    },
    //添加监听全局控制器的端口号
    "global_controller_listen_port": 2111,
    //添加监听BGP路由表项的端口号
    "input_listening_port": 2121
}
```

## 本地控制器的输入格式

在计算local preference时，需要将路由表以字典形式发送给本地控制器，格式如下:

其中，IP_prefix为主机名，next_hop为下一跳网桥名，Router_id为源地址（也就是该路由表项所属的网桥）网桥名

```json
{
'IP_prefix': '10.1.1.0',
'next_hop': '1.1',
'Router_id': '2.1'
}
```

