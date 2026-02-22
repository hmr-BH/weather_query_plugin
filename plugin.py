"""
基于高德天气api的天气查询插件

插件主要功能：
 - 根据用户命令查询指定城市的实时天气
 - 根据用户命令查询指定城市的预报天气
 - 通过自然语言让AI查询天气（Tool方式）
可用命令：
 - /weather <city>                --查询指定城市的实时天气
 - /weather <city> <date>         --查询指定城市的预报天气
AI调用方式：
 - “查一下北京今天的天气”
 - “上海明天会下雨吗？”
 - “深圳后天天气怎么样”
其他：
 # 仅支持中国大陆城市中文名，例如：长沙，北京，南京
 # 支持查询未来四天（含当日）的天气预报信息
 # date格式为YYYY-MM-DD，或相对词：今天、明天、昨天、前天、后天
 # 昨天、前天超出预报范围时会提示错误
"""
import re
from datetime import datetime, timedelta
from typing import List, Type, Union, Dict, Any, Tuple, Optional
import aiohttp
from src.plugin_system import (
    get_logger,
    BaseCommand,
    BaseTool,
    ToolParamType,
    register_plugin,
    BasePlugin,
    ConfigField,
    ComponentInfo
)

logger = get_logger("weather_query_plugin")


class GetWeatherInfo:
    """获取天气数据工具类"""
    def __init__(self, adcode_url: str, weather_url: str, key: str) -> None:
        self.adcode_url = adcode_url
        self.weather_url = weather_url
        self.key = key

    async def get_location_adcode(self, location: str) -> Tuple[bool, str]:
        """获取对应城市的adcode码"""
        params = {
            "address": location,
            "key": self.key,
            "output": "json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.adcode_url, params=params) as response:
                    result = await response.json()
                    status = result["status"]
                    if str(status) == "1":
                        return True, str(result['geocodes'][0]['adcode'])
                    elif result['info'] == 'ENGINE_RESPONSE_DATA_ERROR':
                        logger.error(f"错误的参数，'{location}'可能不是一个有效的城市名")
                        return False, f"错误的参数，'{location}'可能不是一个有效的城市名"
                    elif result["info"] != 'OK':
                        logger.error(f"adcode码查询失败，失败原因:{result['info']}")
                        return False, f"adcode码查询失败，失败原因:{result['info']}"
                    else:
                        logger.error("adcode码查询失败，未知原因")
                        return False, "adcode码查询失败，未知原因"
        except Exception as e:
            logger.error(f"adcode码查询失败，网络连接错误或url填写错误:{str(e)}")
            return False, f"adcode码查询失败，网络连接错误或url填写错误:{str(e)}"

    async def fetch_base_weather(self, adcode: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """实时天气查询"""
        params = {
            "key": self.key,
            "city": adcode,
            "output": "json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.weather_url, params=params) as response:
                    result = await response.json()
                    status = result["status"]
                    if str(status) == "1":
                        if not result.get("lives") or not result["lives"][0]:
                            return False, "暂无天气信息"
                        live = result["lives"][0]
                        info = {
                            "province": live.get("province"),
                            "city": live.get("city"),
                            "adcode": live.get("adcode"),
                            "weather": live.get("weather"),
                            "temperature": live.get("temperature"),
                            "winddirection": live.get("winddirection"),
                            "windpower": live.get("windpower"),
                            "humidity": live.get("humidity"),
                            "reporttime": live.get("reporttime"),
                        }
                        return True, info
                    elif str(status) == "0":
                        logger.error(f"天气信息查询失败，错误信息:{result.get('info')}")
                        return False, f"天气信息查询失败，错误信息:{result.get('info')}"
                    else:
                        logger.error("在查询天气信息的时候发生未知错误")
                        return False, "在查询天气信息的时候发生未知错误"
        except Exception as e:
            logger.error(f"天气信息获取失败:{str(e)}")
            return False, f"天气信息获取失败:{str(e)}"

    async def fetch_forecast_weather(self, adcode: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """预报天气查询（返回多天数据，以日期为键的字典）"""
        params = {
            "key": self.key,
            "city": adcode,
            "extensions": "all",
            "output": "json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.weather_url, params=params) as response:
                    result = await response.json()
                    status = result.get("status", '0')
                    if str(status) == "1":
                        casts = result.get("forecasts", [{}])[0].get("casts")
                        if not casts:
                            return False, "暂无天气信息"
                        city = result.get("forecasts", [{}])[0].get("city")
                        adcode = result.get("forecasts", [{}])[0].get("adcode")
                        province = result.get("forecasts", [{}])[0].get("province")
                        reporttime = result.get("forecasts", [{}])[0].get("reporttime")
                        info = {}
                        for item in casts:
                            date = item.get("date")
                            info[date] = {
                                "city": city,
                                "adcode": adcode,
                                "province": province,
                                "reporttime": reporttime,
                                "week": item.get("week"),
                                "dayweather": item.get("dayweather"),
                                "nightweather": item.get("nightweather"),
                                "daytemp": item.get("daytemp"),
                                "nighttemp": item.get("nighttemp"),
                                "daywind": item.get("daywind"),
                                "nightwind": item.get("nightwind"),
                                "daypower": item.get("daypower"),
                                "nightpower": item.get("nightpower"),
                                "date": date,
                            }
                        return True, info
                    elif str(status) == "0":
                        logger.error(f"天气信息查询失败，错误信息:{result.get('info')}")
                        return False, f"天气信息查询失败，错误信息:{result.get('info')}"
                    else:
                        logger.error("在查询天气信息的时候发生未知错误")
                        return False, "在查询天气信息的时候发生未知错误"
        except Exception as e:
            logger.error(f"天气信息获取失败:{str(e)}")
            return False, f"天气信息获取失败:{str(e)}"


# ==================== 日期解析工具 ====================
def parse_date_expression(date_expr: Optional[str]) -> Tuple[bool, Optional[datetime], str]:
    """
    解析自然语言日期表达式，返回datetime对象
    支持格式：今天、明天、昨天、前天、后天、YYYY-MM-DD
    返回 (是否成功, datetime对象, 错误信息)
    """
    if not date_expr:
        return True, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), ""

    expr = date_expr.strip()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 相对词映射
    rel_map = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "昨天": -1,
        "前天": -2,
    }
    if expr in rel_map:
        target = today + timedelta(days=rel_map[expr])
        return True, target, ""

    # 尝试标准格式
    try:
        target = datetime.strptime(expr, "%Y-%m-%d")
        return True, target, ""
    except ValueError:
        return False, None, f"日期格式无效，请使用 YYYY-MM-DD 或 今天/明天/昨天/前天/后天"


def is_date_in_forecast_range(target_date: datetime) -> bool:
    """检查日期是否在预报范围内（今天起未来3天，即总共4天）"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = today + timedelta(days=3)
    return today <= target_date <= end


# ==================== 天气查询核心逻辑 ====================
async def query_weather_by_city_and_date(
    city: str,
    date_expr: Optional[str],
    config: dict
) -> Tuple[bool, str]:
    """
    统一查询入口：根据城市和日期表达式返回天气信息字符串
    返回 (是否成功, 结果字符串)
    """
    # 1. 解析日期
    success, target_date, err_msg = parse_date_expression(date_expr)
    if not success:
        return False, err_msg

    # 2. 检查日期范围（预报仅支持今天~未来3天）
    if not is_date_in_forecast_range(target_date):
        date_str = target_date.strftime("%Y-%m-%d")
        return False, f"{date_str} 超出预报日期范围（仅支持今天起未来3天）"

    date_str = target_date.strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 3. 获取配置
    adcode_url = config.get("weather.adcode_url")
    weather_url = config.get("weather.weather_url")
    key = config.get("weather.api_key")

    weather_helper = GetWeatherInfo(adcode_url, weather_url, key)

    # 4. 获取adcode
    flag, result = await weather_helper.get_location_adcode(city)
    if not flag:
        return False, str(result)
    adcode = result

    # 5. 如果是今天，可以优先使用实时天气
    if date_str == today_str:
        # 尝试实时天气
        flag, result = await weather_helper.fetch_base_weather(adcode)
        if flag:
            # 验证城市正确性
            if city not in result.get("city", "") and result.get("city") not in city:
                return False, f"'{city}' 不是有效城市"
            formatted = format_base_weather(result)
            return True, formatted
        # 实时查询失败，回退到预报（可能是网络问题，但预报也可能失败，继续尝试预报）
        logger.warning(f"实时天气查询失败，尝试预报: {result}")

    # 6. 使用预报查询（支持今天及未来3天）
    flag, result = await weather_helper.fetch_forecast_weather(adcode)
    if not flag:
        return False, str(result)

    forecast_data = result  # 字典，键为日期
    if date_str not in forecast_data:
        # 理论上不会发生，因为范围已检查
        return False, f"未找到 {date_str} 的天气数据"

    day_data = forecast_data[date_str]
    if city not in day_data.get("city", "") and day_data.get("city") not in city:
        return False, f"'{city}' 不是有效城市"

    formatted = format_forecast_weather(day_data)
    return True, formatted


def format_base_weather(data: dict) -> str:
    """格式化实时天气"""
    province = data.get('province')
    city = data.get('city')
    weather = data.get('weather')
    temperature = data.get('temperature')
    winddirection = data.get('winddirection')
    windpower = data.get('windpower')
    humidity = data.get('humidity')
    reporttime = data.get('reporttime')
    try:
        reporttime = datetime.strptime(reporttime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
    except:
        pass
    return f"""🌆{province}{city}实时天气
==============
🌤️天气:{weather}
🌡️温度:{temperature}℃
💨风向:{winddirection}
🌀风力:{windpower}级
💧湿度:{humidity}%
🕒报告时间:{reporttime}
=============="""


def format_forecast_weather(data: dict) -> str:
    """格式化预报天气"""
    province = data.get("province")
    city = data.get("city")
    week = data.get("week")
    dayweather = data.get("dayweather")
    nightweather = data.get("nightweather")
    daytemp = data.get("daytemp")
    nighttemp = data.get("nighttemp")
    daywind = data.get("daywind")
    nightwind = data.get("nightwind")
    daypower = data.get("daypower")
    nightpower = data.get("nightpower")
    reporttime = data.get("reporttime")
    date = data.get("date")
    try:
        reporttime = datetime.strptime(reporttime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
    except:
        pass
    delta_temp = abs(int(daytemp) - int(nighttemp)) if daytemp and nighttemp else "?"
    return f"""🌆{province}{city}天气预报
==============
📅日期:{date} 周{week}
☀️日间天气:{dayweather}
🌡️日间气温:{daytemp}℃
💨日间风向:{daywind}
🌀日间风速:{daypower}级
==============
🌙夜间天气:{nightweather}
🌡️夜间气温:{nighttemp}℃
💨夜间风向:{nightwind}
🌀夜间风速:{nightpower}级
==============
🔥❄️温差:{delta_temp}℃
📅报告时间:{reporttime}
=============="""


# ==================== Tool 定义（修正为符合框架规范）====================
class WeatherTool(BaseTool):
    """天气查询工具 - 供AI自然语言调用"""

    name = "weather_query"
    description = "查询中国大陆城市的实时天气或未来三天天气预报。支持相对日期：今天、明天、后天，以及具体日期YYYY-MM-DD。"
    parameters = [
        ("city", ToolParamType.STRING, "城市中文名，如：北京、上海、广州", True, None),
        ("date", ToolParamType.STRING, "日期，可选。可以是具体日期（YYYY-MM-DD）或相对词：今天、明天、后天、昨天、前天。默认为今天。注意：昨天、前天可能超出预报范围。", False, None)
    ]
    available_for_llm = True

    async def execute(self, function_args: dict[str, Any]) -> dict[str, Any]:
        """执行天气查询，返回结果字典"""
        city = function_args.get("city")
        date = function_args.get("date")

        if not city:
            return {"name": self.name, "content": "❌ 请提供城市名"}

        config = {
            "weather.adcode_url": self.get_config("weather.adcode_url"),
            "weather.weather_url": self.get_config("weather.weather_url"),
            "weather.api_key": self.get_config("weather.api_key"),
        }

        success, result = await query_weather_by_city_and_date(city, date, config)
        if not success:
            return {"name": self.name, "content": f"❌ {result}"}

        return {"name": self.name, "content": result}


# ==================== 命令类（复用查询逻辑） ====================
class BaseWeatherCommand(BaseCommand):
    command_name = "base_weather_command"
    command_description = "这是一个实时天气查询命令，用于查询实时天气"
    command_pattern = r'^/weather\s+(?P<location>\S+)$'

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        location = self.matched_groups.get('location')
        if not location:
            await self.send_text("请提供城市名")
            return False, "缺少城市名", True

        config = {
            "weather.adcode_url": self.get_config("weather.adcode_url"),
            "weather.weather_url": self.get_config("weather.weather_url"),
            "weather.api_key": self.get_config("weather.api_key"),
        }
        # 命令默认查询今天实时天气
        success, result = await query_weather_by_city_and_date(location, "今天", config)
        if success:
            await self.send_text(result)
            return True, "查询成功", False
        else:
            await self.send_text(result)
            return False, result, True


class ForecastWeatherCommand(BaseCommand):
    command_name = "forecast_weather_command"
    command_description = "这是一个天气预报指令，获取至多未来四天的天气预报信息"
    command_pattern = r'^/weather\s+(?P<city>\S+)(?:\s+(?P<date>\S+))?$'

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        city = self.matched_groups.get("city")
        date = self.matched_groups.get("date") or "今天"

        config = {
            "weather.adcode_url": self.get_config("weather.adcode_url"),
            "weather.weather_url": self.get_config("weather.weather_url"),
            "weather.api_key": self.get_config("weather.api_key"),
        }
        success, result = await query_weather_by_city_and_date(city, date, config)
        if success:
            await self.send_text(result)
            return True, "查询成功", False
        else:
            await self.send_text(result)
            return False, result, True


@register_plugin
class WeatherQueryPlugin(BasePlugin):
    plugin_name: str = "weather_query_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"

    config_schema = {
        "plugin": {
            "name": ConfigField(type=str, default="weather_query_plugin", description="插件名称"),
            "version": ConfigField(type=str, default="1.2.0", description="插件版本"),  # 版本更新
            "enabled": ConfigField(type=bool, default=True, description="是否启用本插件")
        },
        "weather": {
            "api_key": ConfigField(type=str, default="your-api-key", description="请更换为自己的高德天气api"),
            "weather_url": ConfigField(type=str, default="https://restapi.amap.com/v3/weather/weatherInfo", description="查询指定城市天气情况的url，无需更改"),
            "adcode_url": ConfigField(type=str, default="https://restapi.amap.com/v3/geocode/geo", description="查询指定城市adcode码的url，无需更改")
        }
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            # 注册Tool供AI自然语言调用
            (WeatherTool.get_tool_info(), WeatherTool),
            # 保留原有命令
            (BaseWeatherCommand.get_command_info(), BaseWeatherCommand),
            (ForecastWeatherCommand.get_command_info(), ForecastWeatherCommand),
        ]
