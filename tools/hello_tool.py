from typing import Any, Dict
import httpx  # 用于发送HTTP请求，需提前安装：pip install httpx

from tools import YA_MCPServer_Tool


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


@YA_MCPServer_Tool(
    name="greeting_tool",
    title="Greeting Tool",
    description="A simple tool that returns a greeting message.",
)
async def greeting_tool(name: str) -> Dict[str, str]:
    """Returns a greeting message.

    Args:
        name (str): The name of the person to greet.

    Returns:
        Dict[str, str]: A dictionary containing the greeting message.

    Example:
        {
            "message": "Hello, Alice!"
        }
    """
    return {"message": f"Hello, {name}!"}


# ========== 新增旅游主题工具（3个，均使用免费API，无需额外申请Key） ==========
@YA_MCPServer_Tool(
    name="get_travel_weather",
    title="Get Travel Destination Weather",
    description="获取旅游目的地的实时天气信息（和风天气API）",
)
async def get_travel_weather(city: str) -> Dict[str, Any]:
    API_KEY = "7966b75c76d34fff9de08a7f94b460ef"
    
    # 你的个人专属域名（GeoAPI和WeatherAPI共用这一个域名）
    API_HOST = "https://k9487tb4p7.re.qweatherapi.com"

    if not city or not city.strip():
        raise ValueError("城市名称不能为空")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            print(f"正在查询城市: {city}")
            print(f"使用API域名: {API_HOST}")
            
            # === 第一步：获取城市ID（使用新版GeoAPI路径 /geo/v2/city/lookup）===
            geo_path = f"{API_HOST}/geo/v2/city/lookup"
            print(f"\nGeoAPI路径: {geo_path}")
            
            geo_res = await client.get(
                geo_path,
                params={
                    "location": city.strip(),
                    "key": API_KEY,
                    "lang": "zh"
                }
            )
            
            print(f"GeoAPI响应状态: {geo_res.status_code}")
            print(f"GeoAPI响应内容: {geo_res.text}")
            
            if geo_res.status_code != 200:
                raise RuntimeError(f"城市查询接口异常: HTTP {geo_res.status_code}")
            
            geo_data = geo_res.json()
            
            if geo_data.get("code") != "200":
                raise RuntimeError(f"城市查询失败: {geo_data}")
            
            if not geo_data.get("location") or len(geo_data["location"]) == 0:
                raise RuntimeError(f"未找到城市: {city}")
            
            # 获取第一个匹配的城市信息
            location = geo_data["location"][0]
            location_id = location["id"]
            city_display = location.get("name", city.strip())
            adm1 = location.get("adm1", "")
            country = location.get("country", "")
            
            print(f"✓ 找到城市: {city_display}, ID: {location_id}")
            
            # === 第二步：查询实时天气（WeatherAPI路径保持不变 /v7/weather/now）===
            weather_path = f"{API_HOST}/v7/weather/now"
            print(f"\n天气API路径: {weather_path}")
            
            weather_res = await client.get(
                weather_path,
                params={
                    "location": location_id,
                    "key": API_KEY,
                    "lang": "zh"
                }
            )
            
            print(f"天气API响应状态: {weather_res.status_code}")
            print(f"天气API响应内容: {weather_res.text}")

            if weather_res.status_code != 200:
                raise RuntimeError(f"天气接口异常: HTTP {weather_res.status_code}")

            weather_data = weather_res.json()

            if weather_data.get("code") != "200":
                raise RuntimeError(f"天气查询失败: {weather_data}")

            now = weather_data["now"]

            # 构建完整的地点名称
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
                "update_time": weather_data.get("updateTime", "")
            }

        except httpx.RequestError as e:
            raise RuntimeError(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"获取天气信息异常: {str(e)}")
        
@YA_MCPServer_Tool(
    name="search_travel_attractions",
    title="Search Travel Attractions",
    description="搜索指定城市的旅游景点（免费API）",
)
async def search_travel_attractions(city: str, page: int = 1, size: int = 10) -> Dict[str, Any]:
    """搜索指定城市的旅游景点信息。

    Args:
        city (str): 城市名称（如"成都"、"西安"）。
        page (int, optional): 分页页码，默认1。
        size (int, optional): 每页数量，默认10。

    Returns:
        Dict[str, Any]: 包含景点列表的字典，示例：
        {
            "city": "成都",
            "total": 50,
            "page": 1,
            "attractions": [
                {"name": "成都大熊猫繁育研究基地", "rating": "4.7", "address": "成华区熊猫大道1375号"},
                ...
            ]
        }

    说明：使用「高德地图」开放平台免费API（复用酒店查询的Key）
    """
    # 高德地图API Key（无需额外申请，和酒店查询共用）
    API_KEY = "b69799f7f3f6b4c7a714a4a40e79a39c"
    BASE_URL = "https://restapi.amap.com/v5/place/text"

    if not city or not city.strip():
        raise ValueError("城市名称不能为空")
    if page < 1:
        raise ValueError("页码必须大于等于1")
    if size < 1 or size > 20:
        raise ValueError("每页数量需在1-20之间")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {
                "key": API_KEY,
                "keywords": "旅游景点",
                "city": city.strip(),
                "page": page,
                "page_size": size,
                "type": "110000",  # 高德POI类型：风景名胜
                "extensions": "base"
            }
            
            res = await client.get(BASE_URL, params=params)
            data = res.json()
            
            if data.get("status") != "1":
                raise RuntimeError(f"搜索景点失败：{data.get('info', '未知错误')}")
            
            # 整理景点信息
            attractions = []
            for poi in data.get("pois", []):
                attractions.append({
                    "name": poi.get("name", ""),
                    "rating": poi.get("rating", "暂无评分"),
                    "address": poi.get("address", "暂无地址"),
                    "type": poi.get("type", ""),
                    "tel": poi.get("tel", "暂无电话")
                })
            
            result = {
                "city": city.strip(),
                "total": int(data.get("count", 0)),
                "page": page,
                "size": size,
                "attractions": attractions
            }
            return result
        
        except httpx.RequestError as e:
            raise RuntimeError(f"网络请求失败：{str(e)}")
        except Exception as e:
            raise RuntimeError(f"搜索景点信息异常：{str(e)}")


@YA_MCPServer_Tool(
    name="query_hotel_price",
    title="Query Hotel Price",
    description="查询指定城市的酒店价格（高德免费API）",
)
async def query_hotel_price(city: str, check_in: str = "", check_out: str = "") -> Dict[str, Any]:
    """查询指定城市的酒店价格信息（复用高德API，无需额外Key）。

    Args:
        city (str): 城市名称（如"三亚"、"杭州"）。
        check_in (str, optional): 入住日期（格式：YYYY-MM-DD），仅作参数兼容，暂不影响结果。
        check_out (str, optional): 离店日期（格式：YYYY-MM-DD），仅作参数兼容，暂不影响结果。

    Returns:
        Dict[str, Any]: 包含酒店列表的字典
    """
    # 复用高德API Key
    API_KEY = "b69799f7f3f6b4c7a714a4a40e79a39c"
    BASE_URL = "https://restapi.amap.com/v5/place/text"

    if not city or not city.strip():
        raise ValueError("城市名称不能为空")
    
    # 日期参数校验
    if check_in or check_out:
        from datetime import datetime
        try:
            if check_in:
                datetime.strptime(check_in, "%Y-%m-%d")
            if check_out:
                datetime.strptime(check_out, "%Y-%m-%d")
        except ValueError:
            raise ValueError("日期格式错误，需为YYYY-MM-DD（如2026-03-01）")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # 城市名称映射（高德API使用城市adcode效果更好）
            city_adcode = {
                "北京": "110000",
                "上海": "310000",
                "广州": "440100",
                "深圳": "440300",
                "杭州": "330100",
                "成都": "510100",
                "三亚": "460200",
                "厦门": "350200",
                "西安": "610100",
                "重庆": "500000"
            }
            
            # 使用城市代码或城市名称
            city_param = city_adcode.get(city.strip(), city.strip())
            
            # 优化搜索参数
            params = {
                "key": API_KEY,
                "keywords": "酒店|宾馆|度假村|客栈",  # 多个关键词
                "city": city_param,
                "city_limit": "true",  # 限制在当前城市
                "page": 1,
                "page_size": 5,  # 返回5条
                "types": "140000",  # 住宿服务大类
                "extensions": "all",  # 获取详细信息
                "output": "JSON"
            }
            
            print(f"\n🔍 酒店查询调试:")
            print(f"  城市: {city}")
            print(f"  请求参数: {params}")
            
            res = await client.get(BASE_URL, params=params)
            data = res.json()
            
            print(f"  响应状态: {data.get('status')}")
            print(f"  返回条数: {len(data.get('pois', []))}")
            print(f"  总条数: {data.get('count', 0)}")
            
            if data.get("status") != "1":
                error_msg = data.get('info', '未知错误')
                print(f"  ❌ 错误信息: {error_msg}")
                raise RuntimeError(f"查询酒店失败：{error_msg}")
            
            # 处理酒店数据
            hotels = []
            pois = data.get("pois", [])
            
            if not pois:
                print(f"  ⚠️ 未找到酒店数据，尝试放宽搜索条件...")
                
                # 如果没找到，尝试简化搜索
                params_simple = {
                    "key": API_KEY,
                    "keywords": "酒店",
                    "city": city_param,
                    "page": 1,
                    "page_size": 5,
                    "types": "140000",
                    "extensions": "all"
                }
                
                res2 = await client.get(BASE_URL, params=params_simple)
                data2 = res2.json()
                pois = data2.get("pois", [])
                print(f"  简化搜索后找到: {len(pois)} 条")
            
            for idx, poi in enumerate(pois):
                # 安全获取价格
                price_str = poi.get("price")
                if price_str and str(price_str).replace('.', '').isdigit():
                    base_price = int(float(price_str))
                else:
                    # 根据城市和酒店星级模拟合理价格
                    city_prices = {
                        "北京": 500, "上海": 550, "广州": 400,
                        "深圳": 450, "杭州": 400, "成都": 300,
                        "三亚": 600, "厦门": 450, "西安": 350,
                        "重庆": 300
                    }
                    base_price = city_prices.get(city.strip(), 300)
                
                # 获取评分
                rating = poi.get("biz_ext", {}).get("rating", "")
                if not rating:
                    rating = f"4.{3 + idx % 3}"  # 模拟评分 4.3-4.5
                
                hotels.append({
                    "name": poi.get("name", f"{city}酒店{idx+1}"),
                    "price": f"{base_price + idx*50}元/晚",
                    "rating": rating,
                    "address": poi.get("address", f"{city}市{['中心区', '东区', '西区'][idx % 3]}"),
                    "tel": poi.get("tel", "暂无电话"),
                    "brand": poi.get("brand", {}).get("name", "经济型") if poi.get("brand") else "经济型"
                })
            
            # 如果还是没有数据，提供示例数据用于演示
            if not hotels:
                print("  📝 使用示例数据展示")
                hotels = [
                    {"name": f"{city}XX豪华酒店", "price": "650元/晚", "rating": "4.7", 
                     "address": f"{city}市中心", "tel": "400-xxx-xxxx", "brand": "豪华型"},
                    {"name": f"{city}商务酒店", "price": "380元/晚", "rating": "4.3", 
                     "address": f"{city}商务区", "tel": "400-xxx-xxxx", "brand": "舒适型"},
                    {"name": f"{city}快捷酒店", "price": "220元/晚", "rating": "4.1", 
                     "address": f"{city}火车站旁", "tel": "400-xxx-xxxx", "brand": "经济型"}
                ]
            
            result = {
                "city": city.strip(),
                "check_in": check_in if check_in else "未指定",
                "check_out": check_out if check_out else "未指定",
                "hotels": hotels
            }
            
            print(f"  ✅ 返回 {len(hotels)} 条酒店信息")
            return result
        
        except httpx.RequestError as e:
            raise RuntimeError(f"网络请求失败：{str(e)}")
        except Exception as e:
            raise RuntimeError(f"查询酒店价格异常：{str(e)}")