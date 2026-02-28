## YA_MCPServer_TravelAssistant

智能旅游助手 MCP 服务器。聚合高德地图、心知天气等多个 API，输入城市名即可获取实时天气、热门景点、星级酒店信息，并通过加权评分算法（Weighted Scoring Model）+ Haversine 距离算法对结果进行智能排序，返回完整旅游攻略。

### 组员信息

| 姓名 | 学号 | 分工 | 备注 |
| :--: | :--: | :--: | :--: |
| 程桦杰  |  U202414682    |  智能体封装，api申请    |      |
| 罗富卿  |  U202414912    |  api调用框架搭建    |      |
| 夏彦康  |  U202414707    |  智能排序算法设计，调试    |      |

### 密钥管理

本项目的 API 密钥通过环境变量传入，不硬编码在代码中。

| 环境变量 | 用途 | 申请地址 |
| :------: | :--: | :------: |
| `AMAP_API_KEY` | 高德地图（天气、景点、酒店查询） | https://console.amap.com |
| `SENIVERSE_API_KEY` | 心知天气（天气查询） | https://www.seniverse.com |


### Tool 列表

| 工具名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| travel_agent | 旅游智能助手，聚合多API查询天气+景点+酒店 | city (str): 城市名称 | 双源天气、景点智能排名、酒店智能排名 | 聚合高德+心知共4个API并发调用，加权评分排序 |
| get_server_config | 获取服务器配置信息 | key (str): 配置键名 | 配置项的值 | 支持层级访问如 "server.name" |

### Resource 列表

| 资源名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| supported_cities | 支持的城市列表及简介 | 无 | 城市列表 | URI: travel://cities |
| city_detail | 指定城市的详细信息 | city_name: 城市名 | 城市详情 | URI: travel://cities/{city_name} |
| readme_file | 返回项目 README.md 内容 | 无 | 文件文本内容 | URI: file:///README.md |
| server_logs | 返回服务器日志 | path: 日志文件路径 | 日志文本内容 | URI: file:///logs/{path} |

### Prompts 列表

| 指令名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| travel_guide | 生成单城市旅游攻略提示词 | city (str): 城市名 | 攻略提示词模板 | 引导AI调用travel_agent生成完整攻略 |
| travel_compare | 生成双城市对比提示词 | city_a, city_b (str) | 对比提示词模板 | 引导AI对比两个城市的旅游信息 |
| greet_user | 生成问候消息 | name (str): 用户名 | 问候文本 | 框架示例 |

### 项目结构

- `core`: 目前未使用，可扩展
- `tools`: MCP 工具实现
  - `travel_agent.py`: 旅游智能助手 Agent（聚合高德+心知双数据源 + 加权评分排序）
  - `hello_tool.py`: 服务器配置读取工具
  - `test_tool.py`: 测试脚本
- `prompts`: MCP 提示模板
  - `travel_prompt.py`: 旅游攻略 & 城市对比提示词
- `resources`: MCP 资源
  - `travel_resource.py`: 支持城市列表 & 城市详情
- `modules`: 底层共享工具库（YA_Common、YA_Secrets）
- `config.yaml`: 服务器启动方式设置为 sse
- `.env`: API 密钥配置

### 其他需要说明的情况

- **密钥管理**：API 密钥通过环境变量 `AMAP_API_KEY` 和 `SENIVERSE_API_KEY` 传入，由 `.env` 文件管理
- **未使用** PyTorch、TensorFlow 等深度学习框架
- **AI 算法模型**：
  - **加权评分模型（Weighted Scoring Model）**：对景点按等级（国家级/省级/公园等）×0.6 + 距市中心距离×0.4 加权评分排序；对酒店按星级（五星/四星/三星等）×0.5 + 距市中心距离×0.5 加权评分排序。评分维度数据均来自高德 API 返回的真实 `type` 和 `location` 字段
  - **Haversine 距离算法**：根据 POI 经纬度坐标与城市中心坐标，通过 Haversine 公式计算球面距离（公里），作为加权评分的距离维度输入
- **可拓展方向**：原计划对景点和酒店采用 TF-IDF + 聚类算法（如 K-Means）进行自动分类展示（如将景点分为"历史古迹类"、"自然风光类"、"主题乐园类"等），但由于高德免费版 API 返回的 POI 类型字段（`type`）类别单一、文本数据量不足以支撑有效的文本特征提取和聚类，故未采用。后续如接入更丰富的数据源（如用户评论、景点详情），可扩展实现此功能
