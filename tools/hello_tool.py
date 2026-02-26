from typing import Any, Dict

from tools import YA_MCPServer_Tool

#只有一个通用的配置文件函数
@YA_MCPServer_Tool(
    name="get_server_config",
    title="Get Server Config",
    description="获取服务器的配置信息",
)
async def get_server_config(key: str, default: Any = None) -> Dict[str, Any]:
    """获取服务器的配置信息。

    Args:
        key (str): 配置项的键，支持层级访问，例如 "server.name"。
        default (Any, optional): 如果配置项不存在，返回的默认值。默认为 None。

    Returns:
        Dict[str, Any]: 包含配置项值的字典，例如 {"value": ...}。
    """
    try:
        from modules.YA_Common.utils.config import get_config
    except ImportError as e:
        raise RuntimeError(f"无法导入配置模块: {e}")

    try:
        res = get_config(key, default)
        return {"value": res}
    except Exception as e:
        raise RuntimeError(f"获取配置失败: {e}")
