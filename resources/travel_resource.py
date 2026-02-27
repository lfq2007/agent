from resources import YA_MCPServer_Resource


SUPPORTED_CITIES = {
    "北京": {"adcode": "110000", "province": "北京市", "features": "历史古都、长城故宫"},
    "上海": {"adcode": "310000", "province": "上海市", "features": "国际都市、外滩东方明珠"},
    "广州": {"adcode": "440100", "province": "广东省", "features": "美食之都、广州塔"},
    "深圳": {"adcode": "440300", "province": "广东省", "features": "科技之城、世界之窗"},
    "杭州": {"adcode": "330100", "province": "浙江省", "features": "西湖美景、人间天堂"},
    "成都": {"adcode": "510100", "province": "四川省", "features": "天府之国、大熊猫基地"},
    "三亚": {"adcode": "460200", "province": "海南省", "features": "热带海滨、天涯海角"},
    "厦门": {"adcode": "350200", "province": "福建省", "features": "鼓浪屿、海滨风光"},
    "西安": {"adcode": "610100", "province": "陕西省", "features": "十三朝古都、兵马俑"},
    "重庆": {"adcode": "500000", "province": "重庆市", "features": "山城火锅、洪崖洞"},
}


@YA_MCPServer_Resource(
    "travel://cities",
    name="supported_cities",
    title="Supported Cities",
    description="返回旅游助手支持的所有城市列表及简介",
)
def get_supported_cities() -> dict:
    """返回支持查询的城市列表。"""
    return {
        "total": len(SUPPORTED_CITIES),
        "cities": [
            {"name": name, "province": info["province"], "features": info["features"]}
            for name, info in SUPPORTED_CITIES.items()
        ],
    }


@YA_MCPServer_Resource(
    "travel://cities/{city_name}",
    name="city_detail",
    title="City Detail",
    description="返回指定城市的详细信息",
)
def get_city_detail(city_name: str) -> dict:
    """返回指定城市的详细信息。

    Args:
        city_name (str): 城市名称。
    """
    city = SUPPORTED_CITIES.get(city_name)
    if not city:
        return {"error": f"不支持的城市: {city_name}，请查询 travel://cities 获取支持列表"}
    return {
        "name": city_name,
        "province": city["province"],
        "adcode": city["adcode"],
        "features": city["features"],
    }
