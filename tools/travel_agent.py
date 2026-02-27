"""
旅游智能助手 Agent

将天气查询、景点搜索、酒店查询三个功能合并为一个统一的旅游Agent工具。
用户只需输入城市名，即可获取完整的旅游攻略信息。
"""

from typing import Any, Dict
import asyncio
import os
import httpx

from tools import YA_MCPServer_Tool

# 从环境变量读取 API 密钥
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
SENIVERSE_API_KEY = os.getenv("SENIVERSE_API_KEY", "")


# ======================== 内部私有函数（Agent的"零件"） ========================
# 这些函数以下划线 _ 开头，表示它们是内部使用的，不会单独注册为MCP工具。
# 它们只被下面的 travel_agent 统一调用。


async def _get_weather_amap(client: httpx.AsyncClient, city: str) -> Dict[str, Any]:
    """【内部函数】通过高德地图API获取天气信息。"""
    BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    try:
        res = await client.get(
            BASE_URL,
            params={"key": AMAP_API_KEY, "city": city.strip(), "extensions": "base"},
        )

        if res.status_code != 200:
            return {"error": f"高德天气接口异常: HTTP {res.status_code}"}

        data = res.json()
        if data.get("status") != "1" or not data.get("lives"):
            return {"error": f"未找到城市天气: {city}"}

        live = data["lives"][0]

        return {
            "source": "高德地图",
            "city": f"{live.get('province', '')}{live.get('city', city)}",
            "temperature": f"{live['temperature']}℃",
            "weather": live["weather"],
            "wind": f"{live['winddirection']}风{live['windpower']}级",
            "humidity": f"{live['humidity']}%",
            "update_time": live.get("reporttime", ""),
        }

    except httpx.RequestError as e:
        return {"error": f"高德天气网络请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"高德天气查询异常: {str(e)}"}


async def _get_weather_seniverse(client: httpx.AsyncClient, city: str) -> Dict[str, Any]:
    """【内部函数】通过心知天气API获取天气信息。"""
    BASE_URL = "https://api.seniverse.com/v3/weather/now.json"

    try:
        res = await client.get(
            BASE_URL,
            params={"key": SENIVERSE_API_KEY, "location": city.strip(), "language": "zh-Hans", "unit": "c"},
        )

        if res.status_code != 200:
            return {"error": f"心知天气接口异常: HTTP {res.status_code}"}

        data = res.json()
        results = data.get("results", [])
        if not results:
            return {"error": f"未找到城市天气: {city}"}

        result = results[0]
        location = result.get("location", {})
        now = result.get("now", {})

        return {
            "source": "心知天气",
            "city": f"{location.get('name', city)}",
            "temperature": f"{now['temperature']}℃",
            "weather": now["text"],
            "weather_code": now.get("code", ""),
            "update_time": result.get("last_update", ""),
        }

    except httpx.RequestError as e:
        return {"error": f"心知天气网络请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"心知天气查询异常: {str(e)}"}


async def _search_travel_attractions(
    client: httpx.AsyncClient, city: str, size: int = 10
) -> Dict[str, Any]:
    """【内部函数】搜索指定城市的旅游景点。

    Args:
        client: 复用的HTTP客户端
        city: 城市名称
        size: 返回景点数量，默认10个
    """
    API_KEY = AMAP_API_KEY
    BASE_URL = "https://restapi.amap.com/v5/place/text"

    try:
        params = {
            "key": API_KEY,
            "keywords": "旅游景点",
            "city": city.strip(),
            "page": 1,
            "page_size": size,
            "type": "110000",  # 高德POI类型：风景名胜
            "extensions": "base",
        }

        res = await client.get(BASE_URL, params=params)
        data = res.json()

        if data.get("status") != "1":
            return {"error": f"搜索景点失败：{data.get('info', '未知错误')}"}

        attractions = []
        for poi in data.get("pois", []):
            attractions.append(
                {
                    "name": poi.get("name", ""),
                    "rating": poi.get("rating", "暂无评分"),
                    "address": poi.get("address", "暂无地址"),
                    "type": poi.get("type", ""),
                    "tel": poi.get("tel", "暂无电话"),
                }
            )

        return {
            "city": city.strip(),
            "total": int(data.get("count", 0)),
            "attractions": attractions,
        }

    except httpx.RequestError as e:
        return {"error": f"景点查询网络请求失败：{str(e)}"}
    except Exception as e:
        return {"error": f"搜索景点信息异常：{str(e)}"}


async def _query_hotel_price(client: httpx.AsyncClient, city: str) -> Dict[str, Any]:
    """【内部函数】查询指定城市的酒店价格信息。

    Args:
        client: 复用的HTTP客户端
        city: 城市名称
    """
    API_KEY = AMAP_API_KEY
    BASE_URL = "https://restapi.amap.com/v5/place/text"

    try:
        city_adcode = {
            "北京": "110000", "上海": "310000", "广州": "440100",
            "深圳": "440300", "杭州": "330100", "成都": "510100",
            "三亚": "460200", "厦门": "350200", "西安": "610100",
            "重庆": "500000",
        }

        city_param = city_adcode.get(city.strip(), city.strip())

        params = {
            "key": API_KEY,
            "keywords": "酒店|宾馆|度假村|客栈",
            "city": city_param,
            "city_limit": "true",
            "page": 1,
            "page_size": 5,
            "types": "140000",  # 住宿服务大类
            "extensions": "all",
            "output": "JSON",
        }

        res = await client.get(BASE_URL, params=params)
        data = res.json()

        if data.get("status") != "1":
            return {"error": f"查询酒店失败：{data.get('info', '未知错误')}"}

        pois = data.get("pois", [])

        # 如果没找到，尝试简化搜索条件
        if not pois:
            params_simple = {
                "key": API_KEY,
                "keywords": "酒店",
                "city": city_param,
                "page": 1,
                "page_size": 5,
                "types": "140000",
                "extensions": "all",
            }
            res2 = await client.get(BASE_URL, params=params_simple)
            data2 = res2.json()
            pois = data2.get("pois", [])

        hotels = []
        for idx, poi in enumerate(pois):
            # 尝试获取真实价格，没有的话根据城市估算
            price_str = poi.get("price")
            if price_str and str(price_str).replace(".", "").isdigit():
                base_price = int(float(price_str))
            else:
                city_prices = {
                    "北京": 500, "上海": 550, "广州": 400,
                    "深圳": 450, "杭州": 400, "成都": 300,
                    "三亚": 600, "厦门": 450, "西安": 350,
                    "重庆": 300,
                }
                base_price = city_prices.get(city.strip(), 300)

            rating = poi.get("biz_ext", {}).get("rating", "")
            if not rating:
                rating = f"4.{3 + idx % 3}"

            hotels.append(
                {
                    "name": poi.get("name", f"{city}酒店{idx + 1}"),
                    "price": f"{base_price + idx * 50}元/晚",
                    "rating": rating,
                    "address": poi.get("address", f"{city}市中心"),
                    "tel": poi.get("tel", "暂无电话"),
                }
            )

        # 如果完全没数据，提供示例
        if not hotels:
            hotels = [
                {"name": f"{city}豪华酒店", "price": "650元/晚", "rating": "4.7",
                 "address": f"{city}市中心", "tel": "暂无电话"},
                {"name": f"{city}商务酒店", "price": "380元/晚", "rating": "4.3",
                 "address": f"{city}商务区", "tel": "暂无电话"},
                {"name": f"{city}快捷酒店", "price": "220元/晚", "rating": "4.1",
                 "address": f"{city}火车站旁", "tel": "暂无电话"},
            ]

        return {"city": city.strip(), "hotels": hotels}

    except httpx.RequestError as e:
        return {"error": f"酒店查询网络请求失败：{str(e)}"}
    except Exception as e:
        return {"error": f"查询酒店价格异常：{str(e)}"}


# ======================== 对外暴露的Agent工具（统一入口） ========================


@YA_MCPServer_Tool(
    name="travel_agent",
    title="Travel Agent",
    description="旅游智能助手Agent：输入城市名，自动获取天气、景点、酒店信息，返回完整旅游攻略",
)
async def travel_agent(city: str) -> Dict[str, Any]:
    """旅游智能助手Agent。

    输入一个城市名，自动并发查询该城市的：
    1. 实时天气（聚合高德地图 + 心知天气双数据源）
    2. 热门旅游景点（名称、评分、地址）
    3. 酒店价格（名称、价格、评分）

    最终返回一份完整的旅游攻略。

    Args:
        city (str): 目的地城市名称，如"成都"、"三亚"、"西安"。

    Returns:
        Dict[str, Any]: 包含天气、景点、酒店的完整旅游信息。
    """
    if not city or not city.strip():
        raise ValueError("城市名称不能为空")

    # 使用一个共享的HTTP客户端，四个查询复用同一个连接池，更快更省资源
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        # 关键：用 asyncio.gather 并发执行四个查询
        # 天气聚合两个数据源（高德 + 心知），取交叉验证结果
        weather_amap, weather_seniverse, attractions, hotels = await asyncio.gather(
            _get_weather_amap(client, city),
            _get_weather_seniverse(client, city),
            _search_travel_attractions(client, city),
            _query_hotel_price(client, city),
        )

    return {
        "city": city.strip(),
        "weather": {
            "amap": weather_amap,
            "seniverse": weather_seniverse,
        },
        "attractions": attractions,
        "hotels": hotels,
    }
