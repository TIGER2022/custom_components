DOMAIN = 'bus485'

# 发送初始查询ID号请求的时间间隔，分钟
DISCOVERY_INTERVAL = 10

# 灯发送请求状态的时间间隔，分钟
LIGHT_QUERY_STATES_INTERVAL = 2

# 传感器发送请求状态的时间间隔，分钟
BINARY_SENSOR_QUERY_STATES_INTERVAL = 0.5

# 写指令到485的间隔，秒
WRITE_INTERVAL = 0.2

# 窗帘从开到关总运行时长, 秒
CURTAIN_TIME = 30

# 类型
DEVICE_DEFINE = {
    b'\x8c': { "component": "light",
               "subtype": "relay",
               "number": 8,
               "polling": True,
               "name": "MP0816"
               },
    b'\xdc': { "component": "light",
               "subtype": "relay",
               "number": 12,
               "polling": True,
               "name": "DR1220"
               },
    b'\x4d': { "component": "light",
               "subtype": "dimmer",
               "number": 4,
               "polling": True,
               "name": "DI0405"
               },
    b'\x6d': { "component": "light",
               "subtype": "dimmer",
               "number": 4,
               "polling": True,
               "name": "DH0416"
               },
    b'\x3f': { "component": "light",
               "subtype": "dimmer",
               "number": 4,
               "polling": True,
               "name": "DA0405"
               },
    b'\x7c': { "component": "light",
               "subtype": "dimmer",
               "number": 96,
               "polling": True,
               "name": "DMX96"
               },
    #这个编号错误，应该为2b，但样品返回的是4c
    b'\x4c': { "component": "light",
               "subtype": "relay_cu",
               "number": 4,
               "polling": True,
               "name": "DR0420CU"
               },
    b'\xec': { "component": "cover",
               "subtype": "relay",
               "number": 6,
               "polling": False,
               "name": "MP-CUR06"
               },
    b'\x8e': { "component": "binary_sensor",
               "subtype": "board",
               "number": 8,
               "polling": True,
               "name": "8路干节点"
               },
    }
