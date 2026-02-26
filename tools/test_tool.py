"""
旅游Agent测试脚本

测什么：
  1. travel_agent 能否正常返回完整的旅游攻略（天气+景点+酒店）
  2. 三个内部函数能否各自正常工作
  3. 输入不合法时能否正确报错

怎么跑：
  在项目根目录执行：python -m tools.test_tool
"""

import asyncio
import httpx

# 导入Agent统一入口
from .travel_agent import (
    travel_agent,
    _get_travel_weather,
    _search_travel_attractions,
    _query_hotel_price,
)


# ======================== 辅助函数 ========================


def print_section(title: str):
    """打印分隔线，让输出更好看"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


def check_result(name: str, result: dict, required_keys: list[str]) -> bool:
    """检查返回结果是否包含必要的字段。

    Args:
        name: 测试名称（用于打印）
        result: 函数返回的字典
        required_keys: 结果中必须存在的字段名列表

    Returns:
        True=通过, False=失败
    """
    # 如果结果里有 error 字段，说明API调用出了问题
    if "error" in result:
        print(f"  [失败] {name}: {result['error']}")
        return False

    # 检查每个必要字段是否存在
    missing = [k for k in required_keys if k not in result]
    if missing:
        print(f"  [失败] {name}: 缺少字段 {missing}")
        return False

    print(f"  [通过] {name}")
    return True


# ======================== 测试用例 ========================


async def test_travel_agent():
    """测试1：Agent统一入口（最重要的测试）

    这是用户实际会调用的函数。
    输入一个城市名，应该同时返回天气、景点、酒店三部分数据。
    """
    print_section("测试 travel_agent（Agent统一入口）")

    result = await travel_agent("成都")
    print(f"  返回字段: {list(result.keys())}")

    passed = True

    # 检查顶层结构
    if not all(k in result for k in ["city", "weather", "attractions", "hotels"]):
        print("  [失败] 顶层缺少必要字段")
        return False

    print(f"  城市: {result['city']}")

    # 检查天气部分
    weather = result["weather"]
    if "error" not in weather:
        print(f"  天气: {weather.get('temperature', '?')} {weather.get('weather', '?')}")
        passed = check_result("天气数据", weather, ["city", "temperature", "weather"]) and passed
    else:
        print(f"  天气: {weather['error']}")
        passed = False

    # 检查景点部分
    attractions = result["attractions"]
    if "error" not in attractions:
        count = len(attractions.get("attractions", []))
        print(f"  景点: 找到 {count} 个")
        passed = check_result("景点数据", attractions, ["city", "attractions"]) and passed
    else:
        print(f"  景点: {attractions['error']}")
        passed = False

    # 检查酒店部分
    hotels = result["hotels"]
    if "error" not in hotels:
        count = len(hotels.get("hotels", []))
        print(f"  酒店: 找到 {count} 家")
        passed = check_result("酒店数据", hotels, ["city", "hotels"]) and passed
    else:
        print(f"  酒店: {hotels['error']}")
        passed = False

    return passed


async def test_internal_weather():
    """测试2：单独测试天气查询

    验证内部的 _get_travel_weather 函数能否独立工作。
    """
    print_section("测试 _get_travel_weather（天气查询）")

    async with httpx.AsyncClient(timeout=15) as client:
        result = await _get_travel_weather(client, "北京")

    if "error" in result:
        print(f"  [失败] {result['error']}")
        return False

    print(f"  城市: {result.get('city')}")
    print(f"  温度: {result.get('temperature')}")
    print(f"  天气: {result.get('weather')}")
    print(f"  风力: {result.get('wind')}")
    print(f"  湿度: {result.get('humidity')}")
    return check_result("天气查询", result, ["city", "temperature", "weather", "humidity"])


async def test_internal_attractions():
    """测试3：单独测试景点搜索

    验证内部的 _search_travel_attractions 函数能否独立工作。
    """
    print_section("测试 _search_travel_attractions（景点搜索）")

    async with httpx.AsyncClient(timeout=15) as client:
        result = await _search_travel_attractions(client, "西安", size=3)

    if "error" in result:
        print(f"  [失败] {result['error']}")
        return False

    print(f"  城市: {result.get('city')}")
    print(f"  景点总数: {result.get('total')}")
    for att in result.get("attractions", [])[:3]:
        print(f"    - {att['name']}（评分: {att['rating']}）")
    return check_result("景点搜索", result, ["city", "attractions"])


async def test_internal_hotels():
    """测试4：单独测试酒店查询

    验证内部的 _query_hotel_price 函数能否独立工作。
    """
    print_section("测试 _query_hotel_price（酒店查询）")

    async with httpx.AsyncClient(timeout=15) as client:
        result = await _query_hotel_price(client, "三亚")

    if "error" in result:
        print(f"  [失败] {result['error']}")
        return False

    print(f"  城市: {result.get('city')}")
    for h in result.get("hotels", [])[:3]:
        print(f"    - {h['name']} | {h['price']} | 评分: {h['rating']}")
    return check_result("酒店查询", result, ["city", "hotels"])


async def test_invalid_input():
    """测试5：输入不合法的情况

    验证传入空字符串时，Agent能否正确拒绝并报错。
    这叫"边界测试"——专门测极端/错误的输入。
    """
    print_section("测试异常输入（空城市名）")

    try:
        await travel_agent("")
        print("  [失败] 应该抛出错误，但没有")
        return False
    except ValueError:
        print("  [通过] 空字符串正确抛出 ValueError")
        return True
    except Exception as e:
        print(f"  [失败] 抛出了意料之外的错误: {type(e).__name__}: {e}")
        return False


# ======================== 主入口 ========================


async def run_all_tests():
    """按顺序执行所有测试，最后汇总结果"""

    # 所有测试用例，按顺序排列
    tests = [
        ("Agent统一入口", test_travel_agent),
        ("天气查询", test_internal_weather),
        ("景点搜索", test_internal_attractions),
        ("酒店查询", test_internal_hotels),
        ("异常输入", test_invalid_input),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except Exception as e:
            print(f"  [异常] {name} 测试出错: {type(e).__name__}: {e}")
            results[name] = False

    # 打印汇总
    print_section("测试汇总")
    passed = 0
    failed = 0
    for name, ok in results.items():
        status = "通过" if ok else "失败"
        icon = "+" if ok else "-"
        print(f"  [{icon}] {name}: {status}")
        if ok:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print(f"\n  共 {total} 项测试，通过 {passed} 项，失败 {failed} 项")

    if failed == 0:
        print("  所有测试通过！")
    else:
        print(f"  有 {failed} 项测试失败，请检查上面的错误信息。")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
