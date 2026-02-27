from prompts import YA_MCPServer_Prompt


@YA_MCPServer_Prompt(
    name="travel_guide",
    title="Travel Guide Prompt",
    description="生成旅游攻略提示词，引导AI根据城市信息生成完整旅游攻略",
)
async def travel_guide_prompt(city: str) -> str:
    """生成旅游攻略的提示词模板。

    Args:
        city (str): 目的地城市名称。

    Returns:
        str: 旅游攻略提示词。
    """
    return (
        f"请为我生成一份{city}的旅游攻略。\n"
        f"请先调用 travel_agent 工具查询{city}的实时天气、景点和酒店信息，\n"
        f"然后根据返回的数据，生成一份包含以下内容的攻略：\n"
        f"1. 天气概况与穿衣建议\n"
        f"2. 推荐景点及游玩路线\n"
        f"3. 住宿推荐及价格参考\n"
        f"4. 出行注意事项"
    )


@YA_MCPServer_Prompt(
    name="travel_compare",
    title="Travel Compare Prompt",
    description="生成城市对比提示词，引导AI对比两个城市的旅游信息",
)
async def travel_compare_prompt(city_a: str, city_b: str) -> str:
    """生成城市旅游对比的提示词模板。

    Args:
        city_a (str): 第一个城市。
        city_b (str): 第二个城市。

    Returns:
        str: 城市对比提示词。
    """
    return (
        f"请分别调用 travel_agent 工具查询{city_a}和{city_b}的旅游信息，\n"
        f"然后从以下维度进行对比：\n"
        f"1. 当前天气对比，哪个更适合出行\n"
        f"2. 热门景点对比\n"
        f"3. 酒店价格对比\n"
        f"4. 综合推荐：哪个城市更值得去"
    )
