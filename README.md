## YA_MCPServer_TravelAssistant

智能旅游助手 MCP 服务器，输入城市名即可获取天气、景点、酒店信息，返回完整旅游攻略。

### 组员信息

| 姓名 | 学号 | 分工 | 备注 |
| :--: | :--: | :--: | :--: |
| 程桦杰 |      | 全部 |      |
|      |      |      |      |
|      |      |      |      |

### Tool 列表

| 工具名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| travel_agent | 旅游智能助手Agent，自动查询天气+景点+酒店 | city (str): 城市名称 | 天气、景点列表、酒店列表 | 三个API并发调用 |
| get_server_config | 获取服务器配置信息 | key (str): 配置键名 | 配置项的值 | 支持层级访问如 "server.name" |

### Resource 列表

| 资源名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| readme_file | 返回项目 README.md 内容 | 无 | 文件文本内容 | URI: file:///README.md |
| server_logs | 返回服务器日志 | path: 日志文件路径 | 日志文本内容 | URI: file:///logs/{path} |

### Prompts 列表

| 指令名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| greet_user | 生成问候消息 | name (str): 用户名 | 问候文本 | 模板自带示例 |

### 项目结构

- `core`: 核心业务逻辑（与 MCP 解耦）
- `tools`: MCP 工具实现
  - `travel_agent.py`: 旅游智能助手 Agent（天气+景点+酒店）
  - `hello_tool.py`: 服务器配置读取工具
  - `test_tool.py`: 测试脚本
- `prompts`: MCP 提示模板
- `resources`: MCP 资源（文件读取）
- `modules`: 底层共享工具库（YA_Common、YA_Secrets）
- `config.yaml`: 服务器元数据与传输配置

### 其他需要说明的情况

- 在 `sops` 模块中添加的密钥变量分别用于什么功能
- 是否使用了 PyTorch、Tensorflow 等深度学习框架
- 是否使用了机器学习、深度学习模型
