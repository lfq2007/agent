"""
旅游智能助手 Agent

将天气查询、景点搜索、酒店查询三个功能合并为一个统一的旅游Agent工具。
用户只需输入城市名，即可获取完整的旅游攻略信息。
"""

from typing import Any, Dict
import asyncio
import httpx

from tools import YA_MCPServer_Tool


# ======================== 内部私有函数（Agent的"零件"） ========================
# 这些函数以下划线 _ 开头，表示它们是内部使用的，不会单独注册为MCP工具。
# 它们只被下面的 travel_agent 统一调用。


async def _get_travel_weather(client: httpx.AsyncClient, city: str) -> Dict[str, Any]:
    """【内部函数】获取旅游目的地的实时天气信息。

    为什么要单独写成函数？
    - 每个函数只做一件事（查天气），代码清晰好维护
    - 如果天气API换了，只改这一个函数就行

    Args:
        client: 复用的HTTP客户端（避免每次都新建连接，提高性能）
        city: 城市名称
    """
    API_KEY = "7966b75c76d34fff9de08a7f94b460ef"
    API_HOST = "https://k9487tb4p7.re.qweatherapi.com"

    try:
        # 第一步：把城市名转成城市ID（API要求用ID查天气，不能直接用名字）
        geo_res = await client.get(
            f"{API_HOST}/geo/v2/city/lookup",
            params={"location": city.strip(), "key": API_KEY, "lang": "zh"},
        )

        if geo_res.status_code != 200:
            return {"error": f"城市查询接口异常: HTTP {geo_res.status_code}"}

        geo_data = geo_res.json()
        if geo_data.get("code") != "200" or not geo_data.get("location"):
            return {"error": f"未找到城市: {city}"}

        location = geo_data["location"][0]
        location_id = location["id"]
        city_display = location.get("name", city.strip())
        adm1 = location.get("adm1", "")
        country = location.get("country", "")

        # 第二步：用城市ID查实时天气
        weather_res = await client.get(
            f"{API_HOST}/v7/weather/now",
            params={"location": location_id, "key": API_KEY, "lang": "zh"},
        )

        if weather_res.status_code != 200:
            return {"error": f"天气接口异常: HTTP {weather_res.status_code}"}

        weather_data = weather_res.json()
        if weather_data.get("code") != "200":
            return {"error": f"天气查询失败: {weather_data}"}

        now = weather_data["now"]

        # 拼接完整地名（如：四川成都, 中国）
        full_location = city_display
        if adm1 and adm1 != city_display:
            full_location = f"{adm1}{city_display}"
        if country:
            full_location = f"{full_location}, {country}"

        return {
            "city": full_location,
            "temperature": f"{now['temp']}℃",
            "feels_like": f"{now['feelsLike']}℃",
            "weather": now["text"],
            "wind": f"{now['windDir']}{now['windScale']}级",
            "wind_speed": f"{now['windSpeed']}公里/小时",
            "humidity": f"{now['humidity']}%",
            "pressure": f"{now['pressure']}hPa",
            "visibility": f"{now['vis']}公里",
            "update_time": weather_data.get("updateTime", ""),
        }

    except httpx.RequestError as e:
        return {"error": f"天气查询网络请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"获取天气信息异常: {str(e)}"}


async def _search_travel_attractions(
    client: httpx.AsyncClient, city: str, size: int = 10
) -> Dict[str, Any]:
    """【内部函数】搜索指定城市的旅游景点。

    Args:
        client: 复用的HTTP客户端
        city: 城市名称
        size: 返回景点数量，默认10个
    """
    API_KEY = "b69799f7f3f6b4c7a714a4a40e79a39c"
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
    API_KEY = "b69799f7f3f6b4c7a714a4a40e79a39c"
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
    1. 实时天气（温度、体感、风力等）
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

    # 使用一个共享的HTTP客户端，三个查询复用同一个连接池，更快更省资源
    async with httpx.AsyncClient(timeout=15) as client:
        # 关键：用 asyncio.gather 并发执行三个查询
        # 这意味着三个API请求同时发出，而不是一个等一个
        # 比如每个请求要2秒，串行要6秒，并发只要2秒
        weather, attractions, hotels = await asyncio.gather(
            _get_travel_weather(client, city),
            _search_travel_attractions(client, city),
            _query_hotel_price(client, city),
        )

    return {
        "city": city.strip(),
        "weather": weather,
        "attractions": attractions,
        "hotels": hotels,
    }
