from unittest import result
import nonebot
from nonebot import on_command, on_message,require,get_bot
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ArgPlainText, State
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.adapters.onebot.v11.helpers import Cooldown
from nonebot.typing import T_State
from sched import scheduler
from prettytable import PrettyTable
from datetime import datetime as dt

# from .data_source import *
from .user import *

matcher = on_command("超星初始化")
@matcher.handle()
async def initialize(
    event:MessageEvent,
    state: T_State = State()
):
    newUser = User()
    newUser.user_qq = event.get_user_id()
    usersData = newUser.loadUser(newUser.user_qq)
    if usersData != '账号不存在':
        await matcher.finish("你已经完成过初始化了")
    state["newUser"] = newUser
    await matcher.send("来个学号")


@matcher.got("username")
async def getUsername(
    username:str = ArgPlainText("username"),
    state: T_State = State()    
):
    if len(username) != 8:
        await matcher.finish("请发送8位的正确学号，谢谢茄子")
    newUser:  User = state["newUser"]
    newUser.username = username
    state["newUser"] = newUser
    await matcher.send("来个密码")

@matcher.got("password")
async def getPassword(
    password:str=ArgPlainText("password"),
    state:T_State = State()
):
    newUser : User = state["newUser"]
    newUser.password = password
    await matcher.send("验证中")
    await matcher.send(newUser.login())
    
    if newUser.isSolid:
        newUser.getClass()
        myTable = PrettyTable()
        myTable.add_column(
            "课程列表",
            list(newUser.course_dict.keys())
        )
        await matcher.send(str(myTable))
        newUser.saveData()
    else:
        await matcher.finish("超新初始化失败")
    
    
deletor = on_command("注销超星")
@deletor.handle()
async def delUser(event:MessageEvent):
    if deleteUser(event.get_user_id()):
        await deletor.finish("注销成功")
    await deletor.finish("您当前并没有登记过超星账号")
    
scheduler = require('nonebot_plugin_apscheduler').scheduler
@scheduler.scheduled_job(
    "interval",
    seconds = 180
)
async def _(state: T_State = State()):
    try:
        bot = get_bot()  # 当未连接bot时返回
    except ValueError:
        return
    time = dt.now().hour
    if time > 7 and time < 23:
        usersData = getUsersData()
        for user in usersData.keys():
            print("检查："+user)
            User_Instance : User = User()
            User_Instance.loadUser(user)
            test = User_Instance.session.get('http://i.mooc.elearning.shu.edu.cn/space/index?t=1646615407358').text
            if User_Instance.name not in test:
                print("session过期，重新登陆")
            print("cookies未过期，session复活成功")
            newEvent = User_Instance.getEvent()
            for i in newEvent:
                type = User_Instance.getType(i["activeId"],i["courseId"],i["classId"])
                if '手势' in type:
                    await bot.send_private_msg(user_id=int(user),message=f'手势签到进行')
                    User_Instance.gestureSign(i["activeId"],i["courseId"],i["classId"])
                if '位置' in type:
                    await bot.send_private_msg(user_id=int(user),message=f'位置签到进行')
                    latitude,longtitude = '121.401833','31.32001'
                    address = '中国上海市宝山区'
                    User_Instance.locationSign(activeId=i["activeId"],latitude =latitude,longtitude=longtitude,address = address)
                if '二维码' in type:
                    await bot.send_private_msg(user_id=int(user),message=f'检测到二维码签到')
                if '拍照' in type:
                    await bot.send_private_msg(user_id=int(user),message=f'检测到拍照签到，咱解决不了')
                if '普通' in type:
                    await bot.send_private_msg(user_id=int(user),message=f'普通签到,已完成')
            User_Instance.saveData()

    
    

    