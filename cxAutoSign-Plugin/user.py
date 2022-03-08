import os
import re
from bs4 import BeautifulSoup
from .login import login
import requests
from urllib.parse import parse_qs, urlencode
import pickle
import json
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

class_url = 'http://www.elearning.shu.edu.cn/courselist/coursedata?courseType=3&sectionId=7530'
# sectionId为学期的关键字，暂时先硬编码，后续再改


def cookie_to_cookiejar(cookies):
    if not hasattr(cookies, "startswith"):
        raise TypeError
    import requests
    cookiejar = requests.utils.cookiejar_from_dict(
        {cookie[0]: cookie[1] for cookie in
         [cookie.split("=", maxsplit=1) for cookie in cookies.split(";")]})
    return cookiejar

def deleteUser(user_qq):
    dataPath = os.path.join(os.path.dirname(__file__),"usersData.json")
    usersDataFile = open(dataPath)
    usersData = json.load(usersDataFile)
    if user_qq not in usersData.keys():
        return False
    del usersData[user_qq]
    with open(dataPath, 'w') as f:
        f.write(json.dumps(usersData))
        f.close()
    return True

def getUsersData():
    dataPath = os.path.join(os.path.dirname(__file__), "usersData.json")
    usersDataFile = open(dataPath)
    return json.load(usersDataFile)


class User():
    name = ''
    user_qq = 0
    course_dict = {}
    username = ''
    password = ''
    uid = 0
    session = requests.session()

    def login(self):
        ####################################################################
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("window-size=428,843")
        s = Service()
        self.browser = webdriver.Chrome(options=chrome_options, service=s)
        login_result = login(
            self.browser, username=self.username, password=self.password)
        # 利用selenium的登陆，因为selenium的性能开销太高，后续会逐步去除对其的依赖
        if login_result:
            self.name = self.browser.find_element(By.CLASS_NAME,'personalName').get_attribute('title')
            self.uid = self.browser.get_cookie("UID")['value']  # 从cookie中获取签到关键参数——UID
            cookies = self.browser.get_cookies()
            cookie = ""
            for dic1 in cookies:
                name = dic1.get('name')
                value = dic1.get('value')
                cookie = cookie + f"{name}={value}; "
            cookiejar = cookie_to_cookiejar(cookie.strip('; '))
            self.session.cookies = cookiejar
            # 将selenium登录所获得的cookie注入session
            dataPath = os.path.join(os.path.dirname(
                __file__), "cookies", str(self.user_qq))
            # 本地保存cookie
            with open(dataPath, 'wb') as f:
                pickle.dump(self.session.cookies, f)
                self.isSolid = True
            return '登录成功'
        else:
            self.browser.quit()
            return '登录失败'

    def loadUser(self, user_qq):
        usersData = getUsersData()
        if user_qq not in usersData.keys():
            return '账号不存在'
        self.user_qq = user_qq
        self.username = usersData[str(user_qq)]['username']
        self.password = usersData[str(user_qq)]['password']
        self.uid = usersData[str(user_qq)]['uid']
        self.name = usersData[str(user_qq)]['name']
        self.course_dict = usersData[str(user_qq)]['course_dict']
        dataPath = os.path.join(os.path.dirname(__file__), "cookies", user_qq)
        with open(dataPath, 'rb') as f:
            self.session.cookies.update(pickle.load(f))

    def getClass(self):
        klass = self.session.get(url=class_url).text
        klassSoup = BeautifulSoup(klass,'lxml')
        for s in klassSoup.find_all('li', class_='zmy_item'):
            cname = s['cname']
            
            courseId,classId = False,False
            try:
                link = s.find_all('a')[0]['href']
                parse_dict = parse_qs(link)
                courseId, classId = parse_dict['courseId'][0], parse_dict['clazzId'][0]
                # print(cname, courseId, classId)
                self.course_dict.update(
                    {
                        cname: {
                            "courseId": courseId,
                            "classId": classId,
                            "latitude": -1,
                            "longitude": -1,
                            "address": '中国上海市宝山区',
                            "events": {
                }}})
            except:
                print(cname,"出错,可能账号操作过于频繁")
    
    def getEvent(self):
        '''
        回传一个新事件list
        '''        
        newEvent = []
        for c in self.course_dict:
            if self.course_dict[c]["courseId"] == False:
                continue
            print(c)
            courseId = self.course_dict[c]["courseId"]
            classId = self.course_dict[c]["classId"]
            URL = f"http://mobilelearn.elearning.shu.edu.cn/widget/pcpick/stu/index?courseId={courseId}&jclassId={classId}"
            eventSoup = BeautifulSoup(self.session.get(URL).text,'lxml')
            sleep(0.3)
            # print(eventSoup)
            try:
                inSigning = eventSoup.find_all('div',class_='Maincon2')
                activities = inSigning[0].find_all('div',class_ = 'Mct')
                for activity in activities:
                    activeId = re.findall(r"\((.*?),",str(activity['onclick']))[0]
                    if activeId not in self.course_dict[c]["events"]:
                        print(activeId)
                        self.course_dict[c]["events"].update({
                                activeId: True
                            })
                        newEvent.append({
                                "course":c,
                                "activeId":activeId,
                                "courseId":courseId,
                                "classId":classId
                            })
                
            except:
                print(c,"出错")
        return newEvent
    def getType(self, activeId, courseId, classId):
        url = f"http://mobilelearn.elearning.shu.edu.cn/widget/sign/pcStuSignController/preSign?activeId={activeId}&classId={classId}&courseId={courseId}"
        soup = BeautifulSoup(self.session.get(url).text,'lxml')
        eventType = soup.title.text
        if '签到成功' in eventType:
            return "普通签到，签到成功"
        if '学生端-签到' in eventType:
            return '拍照签到，咱解决不了'
        return "进行一个"+eventType+"的签"

    def gestureSign(self,activeId, courseId, classId):
        url = f'http://mobilelearn.elearning.shu.edu.cn/widget/sign/pcStuSignController/signIn?activeId={activeId}&classId={classId}&courseId={courseId}'
        res = self.session.get(url)
        if res == 'success':
            return False
        return True

    def locationSign(self,activeId,latitude,longtitude,address):
        params = {
                'name': self.name,
                'activeId': activeId,
                'address': address,
                'uid': self.uid,
                'clientip': '27.115.83.251',
                'latitude': latitude,
                'longitude': longtitude, #todo 各个课程加入各自的经纬度
                'fid': '209',
                'appType': '15',
                'ifTiJiao': '1'
            }
        res = self.session.get(
            url='https://mobilelearn.chaoxing.com/pptSign/stuSignajax',
            params=params
        )
        if res.text == 'success':
            return False
        return True
    
    def QRSign(self,activeId,enc):
        params = {
                'name': self.name,
                'activeId': activeId,
                'uid': self.uid,
                'clientip': '27.115.83.251',
                'appType': '15',
                'ifTiJiao': '1',
                'enc':enc
            }
        res = self.session.get(
            url='https://mobilelearn.chaoxing.com/pptSign/stuSignajax',
            params=params
        )
        if res.text == 'success':
            return False
        return True
    def saveData(self):
        dataPath = os.path.join(os.path.dirname(__file__),"usersData.json")
        usersDataFile = open(dataPath)
        usersData = json.load(usersDataFile)
        if self.user_qq in usersData.keys():
            usersData[str(self.user_qq)].update(
                    {
                        "username": self.username,
                        "password": self.password,
                        "uid" : self.uid,
                        "name": self.name,
                        "course_dict": self.course_dict
                    }
                )
            with open(dataPath, 'w') as f:
                f.write(json.dumps(usersData))
                f.close()
        else:
            newData = {self.user_qq: {
            "username": self.username,
            "password": self.password,
            "uid" : self.uid,
            "name" : self.name,
            "course_dict": self.course_dict
        }}
            usersData.update(newData)
            with open(dataPath, 'w') as f:
                f.write(json.dumps(usersData))
                f.close()
