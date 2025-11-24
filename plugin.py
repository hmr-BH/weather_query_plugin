"""
基于高德天气api的天气查询插件

插件主要功能：
 - 根据用户命令查询指定城市的实时天气
 - 根据用户命令查询指定城市的预报天气
可用命令：
 - /weather <city>  --查询指定城市的实时天气
 - /weather <city> <date> --查询指定城市的预报天气
 其他：
 # 仅支持中国大陆城市中文名，例如：长沙，北京，南京
 # 支持查询未来四天（含当日）的天气预报信息
 # date格式为YYYY-MM-DD
 # 支持城市名和date数据验证
"""
import re
from datetime import datetime, timedelta
from typing import List, Type, Union, Dict, Any, Tuple, Optional
import aiohttp
from src.plugin_system import *

logger = get_logger("weather_query_plugin")

class GetWeatherInfo:
    """获取天气数据工具类"""
    def __init__(self,adcode_url: str, weather_url: str, key: str) -> None:
        #基础参数
        self.adcode_url = adcode_url
        self.weather_url = weather_url
        self.key = key
    async def get_location_adcode(self,location: str) ->  Tuple[bool, str]:
        """
        获取对应城市的adcode码

        Args:
            location: 城市名，仅支持大陆城市

        Returns:
            bool:是否查询成功
            str: 城市对应的adcode码
        """
        params = {
            "address": location,
            "key": self.key,
            "output": "json"
        }
        #构建api查询参数
        try:
            #查询对应城市的adcode码
            async with aiohttp.ClientSession() as session:
                async with session.get(self.adcode_url, params=params) as response:
                    result = await response.json()
                    status = result["status"]
                    if str(status) == "1":
                        return True , str(result['geocodes'][0]['adcode'])
                    elif result["info"] != 'OK':
                        logger.error(f"adcode码查询失败，失败原因:{result['info']}")
                        return False , f"adcode码查询失败，失败原因:{result['info']}"
                    else:
                        logger.error("adcode码查询失败，未知原因")
                        return False , "adcode码查询失败，未知原因"
        except Exception as e:
            logger.error(f"adcode码查询失败，网络连接错误或url填写错误:{str(e)}")
            return False , f"adcode码查询失败，网络连接错误或url填写错误:{str(e)}"

    async def fetch_base_weather(self,adcode: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        利用城市的adcode码，调用天气api进行天气查询，查询成功返回包含天气数据的字典，否则None

        Args:
            adcode:城市adcode码

        Returns:
            bool: 表示是否成功
            Dict[str] | str: 包含天气信息的字典，查询失败则返回错误信息字符串
        """
        params = {
            "key": self.key,
            "city": adcode,
            "output": "json"
        }
        #构建api查询参数
        try:
            #尝试获取天气信息
            async with aiohttp.ClientSession() as session:
                async with session.get(self.weather_url, params=params) as response:
                    result = await response.json()
                    status = result["status"]
                    if str(status) == "1":
                        province = result.get("lives",[{}])[0].get("province")
                        city = result.get("lives",[{}])[0].get("city")
                        adcode = result.get("lives",[{}])[0].get("adcode")
                        weather = result.get("lives",[{}])[0].get("weather")
                        temperature = result.get("lives",[{}])[0].get("temperature")
                        winddirection = result.get("lives",[{}])[0].get("winddirection")
                        windpower = result.get("lives",[{}])[0].get("windpower")
                        humidity = result.get("lives",[{}])[0].get("humidity")
                        reporttime = result.get("lives",[{}])[0].get("reporttime")
                        info = {
                            "province": province,
                            "city": city,
                            "adcode": adcode,
                            "weather": weather,
                            "temperature": temperature,
                            "winddirection": winddirection,
                            "windpower": windpower,
                            "humidity": humidity,
                            "reporttime": reporttime,
                        }
                        return True , info
                    elif str(status) == "0":
                        logger.error(f"天气信息查询失败，错误信息:{result.get('info')}")
                        return False , f"天气信息查询失败，错误信息:{result.get('info')}"
                    else:
                        logger.error("在查询天气信息的时候发生未知错误")
                        return False , "在查询天气信息的时候发生未知错误"

        except Exception as e:
            logger.error(f"天气信息获取失败:{str(e)}")
            return False , f"天气信息获取失败:{str(e)}"

    async def fetch_forecast_weather(self,adcode) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        获取预报天气数据
        由于实时天气数据和预报天气数据返回的json数据格式有所区别，故在此分开处理

        Args:
            adcode:城市的adcode码

        Returns:
            bool: 表示是否成功
            Dict[str] | str: 包含天气信息的字典，查询失败则返回错误信息字符串
        """
        params = {
            "key": self.key,
            "city": adcode,
            "extensions": "all",
            "output": "json"
        }
        # 构建api查询参数
        info = {}
        # 初始化空字典
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.weather_url, params=params) as response:
                    result = await response.json()
                    status = result.get("status", '0')
                    if str(status) == "1":
                        casts = result.get("forecasts", [{}])[0].get("casts")
                        city = result.get("forecasts", [{}])[0].get("city")
                        adcode = result.get("forecasts", [{}])[0].get("adcode")
                        province = result.get("forecasts", [{}])[0].get("province")
                        reporttime = result.get("forecasts", [{}])[0].get("reporttime")
                        for item in casts:
                            date = item.get("date")
                            week = item.get("week")
                            dayweather = item.get("dayweather")
                            nightweather = item.get("nightweather")
                            daytemp = item.get("daytemp")
                            nighttemp = item.get("nighttemp")
                            daywind = item.get("daywind")
                            nightwind = item.get("nightwind")
                            daypower = item.get("daypower")
                            nightpower = item.get("nightpower")
                            info[date] = {
                                "city": city,
                                "adcode": adcode,
                                "province": province,
                                "reporttime": reporttime,
                                "week": week,
                                "dayweather": dayweather,
                                "nightweather": nightweather,
                                "daytemp": daytemp,
                                "nighttemp": nighttemp,
                                "daywind": daywind,
                                "nightwind": nightwind,
                                "daypower": daypower,
                                "nightpower": nightpower,
                                "date": date,
                            }
                        return True , info
                    elif str(status) == "0":
                        logger.error(f"天气信息查询失败，错误信息:{result.get('info')}")
                        return False , f"天气信息查询失败，错误信息:{result.get('info')}"
                    else:
                        logger.error("在查询天气信息的时候发生未知错误")
                        return False , "在查询天气信息的时候发生未知错误"
        except Exception as e:
            logger.error(f"天气信息获取失败:{str(e)}")
            return False , f"天气信息获取失败:{str(e)}"


class BaseWeatherCommand(BaseCommand):
    command_name = "base_weather_command"
    command_description = "这是一个实时天气查询命令，用于查询实时天气"
    command_pattern = r'^/weather\s+(?P<location>\S+)$'

    async def execute(self)-> Tuple[bool, Optional[str], bool]:
        #读取指令
        location = self.matched_groups.get('location') or None
        #读取配置
        adcode_url = self.get_config("weather.adcode_url")
        weather_url = self.get_config("weather.weather_url")
        key = self.get_config("weather.api_key")
        #验证location数据，确保为中文城市名
        try:
            pattern = r'^[\u4e00-\u9fa5]+$'
            if not re.match(pattern, location):
                raise ValueError("城市名为非汉字")
        except ValueError as e:
            await self.send_text(str(e))
            logger.error(str(e))
            return False, str(e), True

        #获取目标城市adcode值
        weather_info = GetWeatherInfo(adcode_url, weather_url, key)
        flag , result = await weather_info.get_location_adcode(location)
        if flag:
            #执行成功，查询天气信息
            adcode = result
            flag , result = await weather_info.fetch_base_weather(adcode)
            if flag:
                #查询天气成功，格式化处理结果
                city = result.get("city")
                if location in city or city in location:
                    #确保查询到了正确的城市
                    result = self.format_weather_data(result)
                    await self.send_text(result)
                    return True, "查询成功，已发送天气信息" , False

                else:
                    error_message = f"‘{location}’不是有效城市"
                    await self.send_text(error_message)
                    logger.error(error_message)
                    return False, error_message, True

            else:
                #查询天气失败，输出错误信息
                error_message = str(result)
                await self.send_text(error_message)
                logger.error(error_message)
                return False, error_message, True

        else:
            #查询adcode失败，输出错误信息
            error_message = str(result)
            await self.send_text(error_message)
            logger.error(error_message)
            return False, error_message, True

    def format_weather_data(self, data: dict) -> str:
        """
        将获取到的天气信息格式化返回

        Args:
            data: 包含天气信息的字典
        Returns:
            str: 格式化后的天气信息
        """
        province = data.get('province')
        city = data.get('city')
        adcode = data.get('adcode')
        weather = data.get('weather')
        temperature = data.get('temperature')
        winddirection = data.get('winddirection')
        windpower = data.get('windpower')
        humidity = data.get('humidity')
        reporttime = data.get('reporttime')
        reporttime = datetime.strptime(reporttime, "%Y-%m-%d %H:%M:%S")
        reporttime = reporttime.strftime("%Y-%m-%d")
        result = f"""🌆{province}{city}实时天气
==============
🌤️天气:{weather}
🌡️温度:{temperature}℃
💨风向:{winddirection}
🌀风力:{windpower}级
💧湿度:{humidity}%
🕒报告时间:{reporttime}
==============""".strip()
        return result


class ForecastWeatherCommand(BaseCommand):
    command_name = "forecast_weather_command"
    command_description = "这是一个天气预报指令，获取至多未来四天的天气预报信息"
    command_pattern = r'^/weather\s+(?P<city>\S+)(?:\s+(?P<date>\S+))?$'

    async def execute(self)-> Tuple[bool, Optional[str], bool]:
        #从指令中获取参数
        location = self.matched_groups.get("city")
        date = self.matched_groups.get("date")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        #验证date数据
        try :
            target_day = datetime.strptime(date, "%Y-%m-%d")
            today = datetime.today()
            today_str = today.strftime("%Y-%m-%d")
            today = datetime.strptime(today_str, "%Y-%m-%d")
            end_day = today + timedelta(days=3)
            #检查日期范围
            if not (today <= target_day <= end_day):
                error_message = f"{date}超出预报日期范围"
                await self.send_text(error_message)
                return False, error_message, True
        except ValueError:
            await self.send_text("日期格式无效")
            logger.error("日期格式无效")
            return False, "日期格式无效", True
        # 读取配置
        adcode_url = self.get_config("weather.adcode_url")
        weather_url = self.get_config("weather.weather_url")
        key = self.get_config("weather.api_key")
        #获取城市adcode码
        weather = GetWeatherInfo(adcode_url, weather_url, key)
        flag , result = await weather.get_location_adcode(location)
        if flag:
            #查询天气信息
            adcode = result
            flag , result = await weather.fetch_forecast_weather(adcode)
            if flag:
                weather_info = result.get(date)
                city = weather_info.get("city")
                if location in city or city in location:
                    result = self.format_weather_data(weather_info)
                    await self.send_text(result)
                    return True , "查询成功，已发送天气信息" , True
                else:
                    error_message = f"’{location}‘并非有效城市"
                    await self.send_text(error_message)
                    logger.error(error_message)
                    return False, error_message, True
            else:
                error_message = result
                await self.send_text(error_message)
                logger.error(error_message)
                return False, error_message, True
        else:
            error_message = result
            await self.send_text(error_message)
            logger.error(error_message)
            return False, error_message, True

    def format_weather_data(self, data: dict) -> str:
        """
        将获取到的天气信息格式化返回

        Args:
            data: 包含天气信息的字典
        Returns:
            str: 格式化后的天气信息
        """
        weather_info = data
        province = weather_info.get("province")
        city = weather_info.get("city")
        adcode = weather_info.get("adcode")
        reporttime = weather_info.get("reporttime")
        week = weather_info.get("week")
        dayweather = weather_info.get("dayweather")
        nightweather = weather_info.get("nightweather")
        daytemp = weather_info.get("daytemp")
        nighttemp = weather_info.get("nighttemp")
        daywind = weather_info.get("daywind")
        nightwind = weather_info.get("nightwind")
        daypower = weather_info.get("daypower")
        nightpower = weather_info.get("nightpower")
        reporttime = datetime.strptime(reporttime, "%Y-%m-%d %H:%M:%S")
        reporttime = reporttime.strftime("%Y-%m-%d")
        date = weather_info.get("date")
        delta_temp = abs(daytemp - nighttemp)
        result = f"""🌆{province}{city}天气预报
==============
📅日期:{date}
☀️日间天气:{dayweather}
🌡️日间气温:{daytemp}℃
💨日间风向:{daywind}
🌀日间风速:{daypower}级
-----------------------
🌙夜间天气:{nightweather}
🌡️夜间气温:{nighttemp}℃
💨夜间风向:{nightwind}
🌀夜间风速:{nightpower}级
-----------------------
📅报告日期:{reporttime}
==============
""".strip()
        return result

@register_plugin
class WeatherQueryPlugin(BasePlugin):
    plugin_name: str = "weather_query_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"
    #配置Schema定义
    config_schema:dict ={
        "plugin":{
            "name":ConfigField(type = str, default = "weather_query_plugin", description="插件名称"),
            "version":ConfigField(type = str , default = "1.0.0", description = "插件版本"),
            "enabled":ConfigField(type = bool , default = True , description = "是否启用本插件")
        },
        "weather":{
            "api_key":ConfigField(type = str , default = "your-api-key" , description = "请更换为自己的高德天气api"),
            "weather_url":ConfigField(type = str , default="https://restapi.amap.com/v3/weather/weatherInfo" , description = "查询指定城市天气情况的url，无需更改"),
            "adcode_url":ConfigField(type = str , default= "https://restapi.amap.com/v3/geocode/geo" , description = "查询指定城市adcode码的url，无需更改")
        }
    }
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return[
            (BaseWeatherCommand.get_command_info(), BaseWeatherCommand),
            (ForecastWeatherCommand.get_command_info(), ForecastWeatherCommand),
        ]