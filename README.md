# 天气查询插件(weather_query_plugin)
***
作者编程初学不久，这是第一次尝试为maimai编写插件，也是第一次尝试为项目贡献插件。
代码很粗错捏，还在进一步学习。如有任何疑问或建议请随时练习作者（qq:2649366321）

让maimai能够查询指定城市的实时天气或预报天气 

## ⚠️ 重要注意事项
* 本插件基于高德天气api开发，需要用户自行申请高德天气api的申请 【Web服务API】密钥（Key），详见高德地图api官方文档:https://lbs.amap.com/api/webservice/create-project-and-key
* 仅支持中国大陆城市的天气查询
## 安装插件
* clone本仓库到plugins文件夹下即可
* 首次启动后会自动创建config.toml文件，请手动配置api_key，否则无法使用
## 安装依赖
***
在使用插件前，请先安装必要的依赖:
```
pip install -r requirements.txt
```
或手动安装:
```
pip install aiohttp
```
## 配置文件详解:
```toml
# weather_query_plugin - 自动生成的配置文件
# 支持查询指定城市(中国大陆)的实时天气和预报天气

[plugin]

# 插件名称
name = "weather_query_plugin"

# 插件版本
version = "1.0.0"

# 是否启用本插件
enabled = true


[weather]

# 请更换为自己的高德天气api
api_key = "your_api_key"

# 查询指定城市天气情况的url，无需更改
weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"

# 查询指定城市adcode码的url，无需更改
adcode_url = "https://restapi.amap.com/v3/geocode/geo"
```
## 使用方法:
命令列表：
```
/weather <city>  #查询指定城市的实时天气信息
/weather <city> <date>  #查询指定城市某日的天气预报
```
示例：
`/weather <city>`

<img src="./images/weather-example.png" alt="示例" width="350" height="200">
<img src="./images/weather-example-all.png" alt="示例" width="350" height="200">

`/weather <city> <date>`

<img src="./images/weather-forecast-example.png" alt="示例" width="350" height="200">



注⚠️:
* city值填写顺序为“国家、省份、城市、区县”，一般情况下只输入某某市或某某区即可，遇到重名城市加上某某省即可
* 日期<date>的格式为YYYY-MM-DD,例如2025-11-22
* 支持查看最多三日后的天气信息，例如在2025-11-22，最多可以查询到2025-11-25日的天气预报
* 字段city仅支持中文名