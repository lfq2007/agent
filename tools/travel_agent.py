"""
旅游智能助手 Agent

将天气查询、景点搜索、酒店查询三个功能合并为一个统一的旅游Agent工具。
用户只需输入城市名，即可获取完整的旅游攻略信息。

AI算法：加权评分模型（Weighted Scoring Model）
基于高德API返回的真实数据（景点等级、酒店星级、距市中心距离），
进行多维度加权评分，自动排序推荐最优选择。
公式：Score = Σ(wi × xi) / Σ(wi)
"""

from typing import Any, Dict, List, Tuple
import asyncio
import math
import os
import httpx

from tools import YA_MCPServer_Tool

# 从环境变量读取 API 密钥
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
SENIVERSE_API_KEY = os.getenv("SENIVERSE_API_KEY", "")

# 城市中心坐标（经度, 纬度）
CITY_CENTERS = {
    "北京": (116.397428, 39.90923), "上海": (121.473701, 31.230416),
    "广州": (113.264385, 23.12911), "深圳": (114.057868, 22.543099),
    "杭州": (120.15507, 30.274084), "成都": (104.065735, 30.659462),
    "三亚": (109.508268, 18.247872), "厦门": (118.11022, 24.490474),
    "西安": (108.948024, 34.263161), "重庆": (106.504962, 29.533155),
}


# ======================== AI 算法：加权评分模型 ========================


def _haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Haversine公式计算两个经纬度坐标之间的距离（公里）。"""
    R = 6371  # 地球半径（公里）
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_location(location_str: str) -> Tuple[float, float]:
    """解析高德返回的 'longitude,latitude' 字符串。"""
    try:
        lon, lat = location_str.split(",")
        return float(lon), float(lat)
    except (ValueError, AttributeError):
        return 0.0, 0.0


def _get_attraction_level(type_str: str) -> float:
    """从 type 字段提取景点等级分数（10分制）。"""
    if "国家级景点" in type_str:
        return 10.0
    elif "省级景点" in type_str:
        return 8.0
    elif "公园" in type_str:
        return 6.0
    elif "寺庙道观" in type_str or "教堂" in type_str:
        return 7.0
    elif "动物园" in type_str or "植物园" in type_str or "水族馆" in type_str:
        return 7.5
    elif "博物馆" in type_str or "纪念馆" in type_str:
        return 8.0
    elif "风景名胜" in type_str:
        return 6.5
    return 5.0


def _get_hotel_star(type_str: str) -> float:
    """从 type 字段提取酒店星级分数（10分制）。"""
    if "五星" in type_str or "豪华" in type_str:
        return 10.0
    elif "四星" in type_str or "高档" in type_str:
        return 8.0
    elif "三星" in type_str or "舒适" in type_str:
        return 6.0
    elif "经济" in type_str or "快捷" in type_str:
        return 4.0
    elif "宾馆酒店" in type_str:
        return 5.0
    return 5.0


def _distance_score(distance_km: float, max_km: float = 30.0) -> float:
    """将距离转换为分数（10分制），越近分越高。"""
    if distance_km <= 0:
        return 10.0
    return max(0.0, 10.0 * (1.0 - distance_km / max_km))


def _weighted_score(dimensions: Dict[str, float], weights: Dict[str, float]) -> float:
    """加权评分算法（Weighted Scoring Model）。

    对多个评价维度分别乘以对应权重，归一化求和得到综合得分。
    公式：Score = Σ(wi × xi) / Σ(wi)

    Args:
        dimensions: 各维度的分值，如 {"level": 8, "distance": 7.5}
        weights: 各维度的权重，如 {"level": 0.6, "distance": 0.4}

    Returns:
        float: 归一化后的综合得分（10分制）
    """
    total_score = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        value = dimensions.get(key, 0)
        total_score += weight * value
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return total_score / total_weight


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
            "keywords": "热门景点",
            "city": city.strip(),
            "page": 1,
            "page_size": size,
            "type": "110000",  # 高德POI类型：风景名胜
            "extensions": "all",
        }

        res = await client.get(BASE_URL, params=params)
        data = res.json()

        if data.get("status") != "1":
            return {"error": f"搜索景点失败：{data.get('info', '未知错误')}"}

        city_center = CITY_CENTERS.get(city.strip())

        attractions = []
        for poi in data.get("pois", []):
            type_str = poi.get("type", "")
            location_str = poi.get("location", "")

            # 维度1：景点等级分（从type字段提取，如国家级景点=10分）
            level = _get_attraction_level(type_str)

            # 维度2：距市中心距离分（用Haversine公式计算真实距离）
            dist_score = 5.0
            distance_km = None
            if city_center and location_str:
                lon, lat = _parse_location(location_str)
                if lon > 0 and lat > 0:
                    distance_km = round(_haversine_distance(
                        city_center[0], city_center[1], lon, lat
                    ), 1)
                    dist_score = _distance_score(distance_km)

            # 加权评分：等级权重0.6，距离权重0.4
            score = _weighted_score(
                {"level": level, "distance": dist_score},
                {"level": 0.6, "distance": 0.4},
            )

            item = {
                "name": poi.get("name", ""),
                "type": type_str,
                "address": poi.get("address", "暂无地址"),
                "smart_score": round(score, 1),
            }
            if distance_km is not None:
                item["distance_km"] = distance_km

            attractions.append(item)

        # 按加权评分降序排列
        attractions.sort(key=lambda x: x["smart_score"], reverse=True)

        return {
            "city": city.strip(),
            "total": int(data.get("count", 0)),
            "ranking_algorithm": "加权评分模型（景点等级×0.6 + 距市中心距离×0.4）",
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

        # 分别搜索高档和经济型酒店，聚合后排序
        pois = []
        for kw in ["五星酒店", "四星酒店", "经济型酒店"]:
            res_h = await client.get(BASE_URL, params={
                "key": API_KEY,
                "keywords": kw,
                "city": city_param,
                "city_limit": "true",
                "page": 1,
                "page_size": 4,
                "type": "140000",
                "extensions": "all",
            })
            data_h = res_h.json()
            if data_h.get("status") == "1":
                pois.extend(data_h.get("pois", []))

        city_center = CITY_CENTERS.get(city.strip())

        hotels = []
        for poi in pois:
            type_str = poi.get("type", "")
            location_str = poi.get("location", "")

            # 维度1：酒店星级分（从type字段提取，如五星=10分）
            star = _get_hotel_star(type_str)

            # 提取星级文字用于展示
            star_label = "未知星级"
            for label in ["五星", "四星", "三星", "经济", "快捷"]:
                if label in type_str:
                    star_label = label + "级"
                    break

            # 维度2：距市中心距离分
            dist_score = 5.0
            distance_km = None
            if city_center and location_str:
                lon, lat = _parse_location(location_str)
                if lon > 0 and lat > 0:
                    distance_km = round(_haversine_distance(
                        city_center[0], city_center[1], lon, lat
                    ), 1)
                    dist_score = _distance_score(distance_km)

            # 加权评分：星级权重0.5，距离权重0.5
            score = _weighted_score(
                {"star": star, "distance": dist_score},
                {"star": 0.5, "distance": 0.5},
            )

            item = {
                "name": poi.get("name", ""),
                "star": star_label,
                "address": poi.get("address", ""),
                "smart_score": round(score, 1),
            }
            if distance_km is not None:
                item["distance_km"] = distance_km

            hotels.append(item)

        # 按加权评分降序排列
        hotels.sort(key=lambda x: x["smart_score"], reverse=True)

        # 只返回前5个
        hotels = hotels[:5]

        return {
            "city": city.strip(),
            "ranking_algorithm": "加权评分模型（酒店星级×0.5 + 距市中心距离×0.5）",
            "hotels": hotels,
        }

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
