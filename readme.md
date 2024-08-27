# local preference推理代码实现
## 接口文件

需要调用的文件主要有以下两个
- GlobalController：联邦控制器，通过每个本地控制器上传的已变换的本地拓扑计算全局拓扑结构，而后分发给每个本地控制哎
- LocalController：本地控制器，根据LLDP收集的本地拓扑信息构建本地拓扑结构，上传给联邦控制器并获得全局拓扑，而后监听BGP参数计算消息调用训练好的模型推理出local preference值

### GlobalController.py

在一个单独的控制器主机上执行该代码，需要根据具体场景修改如下四部分内容（main方法中给出了示例及对应注释）
- 调用如下函数为联邦控制器指明所有需要交互的AS号
```python
global_controller.ASes.append(1)
```
- 调用如下函数添加全部域间链路邻接信息
```python
global_controller.global_topology.cross_domain_links.append(['1.3', '2.3']) #[网桥名，网桥名]
```

- 指明本地监听端口

```python
global_controller.listen_local_topology('localhost', 2101)
```

- 调用如下函数添加所有本地控制器的ip和监听端口

```python
global_controller.ASController_ip['ASN'] = ['ip', 2111]
```

### LocalController.py

在每一个域内运行一个控制器，执行本代码，需要根据具体场景修改如下内容（LocalController.py的main方法给出了示例）

- 根据LLDP收集到的本地拓扑信息，指定网桥集合(50行)

```python
router_name_set = ['1.1', '1.2', '1.3']
```

- 根据域内路由算法获得的所有网桥间的路由距离，指定该距离的字典，用于构建BGP peer级的拓扑(58行)

```python
router_distance_dict = {'1.1': {'1.2': 1, '1.3': 1}, '1.2': {'1.1': 1, '1.3': 1}, '1.3': {'1.1': 1, '1.2': 1}}
```

- 为所有主机指明所挂载的网桥(63-66行)

```python
local_controller.local_topology.ip_router['1.1.0.1'] = '1.1'
```

- 指定对应的联邦控制器ip和端口(75-76行)

```python
global_controller_ip = 'localhost'
global_controller_port = 2101
```

- 指定监听联邦控制器的端口(84行，所有控制器统一即可，与联邦控制器侧的配置对应)

```python
global_controller_listen_port = 2111
```

- 指定监听BGP路由表输入的端口(110行)

```python
input_listening_port = 2121
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

