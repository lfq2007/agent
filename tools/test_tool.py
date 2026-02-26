import asyncio
# 导入你写好的工具函数（假设代码保存在 travel_tools.py 文件中）
from .hello_tool import get_travel_weather, search_travel_attractions, query_hotel_price

# 定义测试函数
async def test_all_tools():
    """测试所有旅游工具的调用"""
    try:
        # 1. 测试天气工具（查询北京天气）
        print("===== 测试天气工具 =====")
        weather_result = await get_travel_weather("北京")
        print(f"北京天气：{weather_result}\n")

        # 2. 测试景点工具（查询成都景点，每页5条）
        print("===== 测试景点工具 =====")
        attraction_result = await search_travel_attractions("成都", page=1, size=5)
        print(f"成都景点：{attraction_result}\n")

        # 3. 测试酒店工具（查询三亚酒店，指定入住/离店日期）
        print("===== 测试酒店工具 =====")
        hotel_result = await query_hotel_price("三亚", "2026-03-01", "2026-03-05")
        print(f"三亚酒店：{hotel_result}\n")

    except Exception as e:
        print(f"调用工具出错：{e}")

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_all_tools())