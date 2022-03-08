import time
from selenium.webdriver.common.by import By




RETRY = 5
RETRY_TIMEOUT = 30


def login(browser, username, password):
    for retry in range(RETRY):
        print(f'第{retry}次尝试登陆')

        try:
            browser.get('http://www.elearning.shu.edu.cn/login/to')
            browser.find_element(By.ID, 'username').send_keys(username)
            browser.find_element(By.ID, 'password').send_keys(password)
            browser.find_element(By.ID, 'submit-button').click()
        except Exception as e:
            print(e)

        browser.get('http://i.mooc.elearning.shu.edu.cn/')
        time.sleep(1)
        if 'index' in browser.current_url:
            return True

        time.sleep(RETRY_TIMEOUT)

    return False


