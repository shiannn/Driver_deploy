from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchElementException
import datetime, time
import json

import psycopg2
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.scheduler import Scheduler
#from apscheduler.schedulers.blocking import BlockingScheduler

import logging
import sys
import os
logging.basicConfig(stream=sys.stdout, 
format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
"""
try:
    with open('access.json', 'r') as f:
        access = json.load(f)
        USERID = access['USERID']
        PASSWORD = access['PASSWORD']
        DRIVERLOCATION = access['DRIVERLOCATION']
        SQLALCHEMY_DATABASE_URI = access['SQLALCHEMY_DATABASE_URI']
except:
    logging.warning('Please Add access json')
    exit(0)
"""

USERID = os.environ.get('USERID')
PASSWORD = os.environ.get('PASSWORD')
DRIVERLOCATION = os.environ.get('CHROMEDRIVER_PATH')
GOOGLE_CHROME_BIN = os.environ.get("GOOGLE_CHROME_BIN")
SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')


SLEEP_TIME = 240
REST_THRESHOLD = 600
def getCourse(course_name, options_course):
    for coruse in options_course.options:
        if(coruse.text[:len(course_name)] == course_name):
            return coruse.text
    logging.warning('course input error')
    return False

def getPostion(position_name, options_pos):
    for position in options_pos.options:
        if(position.text[:len(position_name)] == position_name):
            return position.text
    logging.warning('position input error')
    return False

def getDate(date_name, options_date):
    for date in options_date.options:
        if(date.text[:len(date_name)] == date_name):
            return date.text
    logging.warning('date input error')
    return False

def checkInPage(driver):
    #time.sleep(2)
    into_book_page, sleep_times = False, 0
    while(not into_book_page):
        if sleep_times >= SLEEP_TIME:
            return False
        sleep_times += 1
        try:
            driver.find_element_by_css_selector("select[id='class_selector']")
            into_book_page = True
            return True
        except NoSuchElementException:
            time.sleep(1)

def checkInLogin(driver):
    login, sleep_times = False, 0
    while(not login):
        if sleep_times >= SLEEP_TIME:
            return False
        sleep_times += 1
        try:
            driver.find_element_by_id('id')
            login = True
            return True
        except NoSuchElementException:
            time.sleep(1)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_DATABASE_URISQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Booking(db.Model):
    """ Booking model """

    __tablename__ = "Booking"
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(), nullable=False)
    date = db.Column(db.String(), nullable=False) # unique
    position = db.Column(db.String(), nullable=False)
    last_update = db.Column(db.String(), nullable=False)

    def __init__(self, course, date, position, last_update):
        self.course = course
        self.date = date
        self.position = position
        self.last_update = last_update
    
    def __repr__(self):
        return "Booking {} {} {}".format(self.course, self.date, self.position)

def getConfig():
    query = Booking.query.first()
    config = {
        'course':query.course,
        'date':query.date,
        'position':query.position
    }
    return config

def bookTKB():
    logging.warning('[TKB booking...]')

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.binary_location = GOOGLE_CHROME_BIN

    driver = webdriver.Chrome(executable_path=DRIVERLOCATION, chrome_options=options) # 選擇Chrome瀏覽器
    driver.set_window_size(400, 1800)

    ### get config
    config = getConfig()
    print(config)

    st = time.time()
    logging.warning('=== start {} ==='.format(st - st))
    driver.get(LOGIN_URL)
    connect_time = time.time()
    logging.warning('=== connected {} ==='.format(connect_time - st))

    islogin = checkInLogin(driver)
    if not islogin:
        logging.warning('fail to login')
        return False

    driver.find_element_by_id('id').click()
    driver.find_element_by_id('id').send_keys(USERID)
    driver.find_element_by_id('pwd').click()
    driver.find_element_by_id('pwd').send_keys(PASSWORD)
    driver.find_element_by_link_text('送出').click()

    get_submit_alert, sleep_times = False, 0
    while(not get_submit_alert):
        if sleep_times >= SLEEP_TIME:
            logging.warning('no alert in login')
            return False
        sleep_times += 1
        try:
            alogin = driver.switch_to_alert()
            print(alogin.text)
            alogin.accept()
            get_submit_alert = True
        except NoAlertPresentException:
            time.sleep(1)
            pass

    inCoursePage = checkInPage(driver)
    if not inCoursePage:
        logging.warning('fail to in course page')
        return False

    
    logging.warning('=== into_time ===')
    today = datetime.datetime.now()
    if today < datetime.datetime(today.year, today.month, today.day, 12 - 8, 0, 0):
        # morning, booking noon
        rest_time = (datetime.datetime(today.year, today.month, today.day, 12 - 8, 0, 0) - today).total_seconds() + 1
    else:
        # afternoon, booking midnight
        rest_time = (datetime.datetime(today.year, today.month, today.day, 23 - 8, 59, 59) - today).total_seconds() + 2
    
    if rest_time > REST_THRESHOLD or rest_time < 0:
        logging.warning('something wrong on rest')
        return False

    #driver.save_screenshot('login.png')
    
    logging.warning('[sleeping {} minutes...]'.format(rest_time / 60))
    time.sleep(rest_time)
    logging.warning('[wake up and clean refresh course...]')

    ### push clear
    driver.find_element_by_link_text('清除').click()

    clearCoursePage = checkInPage(driver)
    if not clearCoursePage:
        logging.warning('fail to clear course page')
        return False

    #driver.save_screenshot('clear.png')

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    select_course = driver.find_element_by_css_selector("select[id='class_selector']")
    options_course = Select(select_course)
    course_name = getCourse(config["course"], options_course)
    if not course_name:
        return False
    options_course.select_by_visible_text(course_name)
    logging.warning(course_name)

    select_date = driver.find_element_by_css_selector("select[id='date_selector']")
    options_date = Select(select_date)
    date_name = getDate(config["date"], options_date)
    if not date_name:
        return False
    options_date.select_by_visible_text(date_name)
    logging.warning(date_name)

    select_branch = driver.find_element_by_css_selector("select[id='branch_selector']")
    options_branch = Select(select_branch)
    position_name = getPostion(config["position"], options_branch)
    if not position_name:
        return False
    options_branch.select_by_visible_text(position_name)
    logging.warning(position_name)

    has_class=driver.find_elements_by_css_selector('input[type=checkbox][value=hasClass]')
    
    if len(has_class) != 0:
        logging.warning('You already have seat')
        return False

    all_checkboxs=driver.find_elements_by_css_selector('input[type=checkbox]')
    disabled_checkboxs=driver.find_elements_by_css_selector('input[type=checkbox][disabled]')
    abled_checkboxs = [a for a in all_checkboxs if a not in disabled_checkboxs]

    checked = False
    for idx, checkbox in enumerate(all_checkboxs):
        if idx + 1 == 3:
            continue
        if checkbox in abled_checkboxs:
            checkbox.click()
            checked = True
            break

    #driver.save_screenshot('test.png')

    if not checked:
        logging.warning('no more session')
        return False

    ed = time.time()
    logging.warning('=== end {} ==='.format(ed - st))
    driver.find_element_by_link_text('送出').click()

    ### Todo: sleep and wait for the alert
    get_submit_alert, sleep_times = False, 0
    while(not get_submit_alert):
        if sleep_times >= SLEEP_TIME:
            print('fail to confirm submit')
            return False
        sleep_times += 1
        try:
            abook = driver.switch_to_alert()
            print(abook.text)
            abook.accept()
            get_submit_alert = True
        except NoAlertPresentException:
            time.sleep(1)
            pass

    get_submit_alert, final_sleep_times = False, 0
    while(not get_submit_alert):
        if(final_sleep_times >= SLEEP_TIME):
            print('No final alert')
            return False
        final_sleep_times += 1
        try:
            afinal = driver.switch_to_alert()
            print(afinal.text)
            afinal.accept()
            get_submit_alert = True
        except NoAlertPresentException:
            time.sleep(1)
            pass

    ### Todo: try 5 times until succeed with function call
    ### Todo: scheduling and get config each trial
    ### Todo: put the root directory of program into config
    return True

def printHello():
    print('hello')
    return

def main():
    sched = Scheduler()
    #sched = BlockingScheduler()
    sched.start()
    sched.add_cron_job(bookTKB, hour=3, minute=50)
    sched.add_cron_job(bookTKB, hour=15, minute=50)

    sched.add_cron_job(bookTKB, hour=8, minute=57)
    #sched.add_cron_job(bookTKB, hour=16, minute=50)
    #sched.add_job(bookTKB, 'cron', hour=3, minute=55)
    #sched.add_job(bookTKB, 'cron', hour=15, minute=55)
    #sched.add_job(bookTKB, 'cron', hour=8, minute=12)
    logging.warning('running...')

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

    
if __name__ == '__main__':
    LOGIN_URL = 'https://bookseat.tkblearning.com.tw/book-seat/student/login/toLogin'
    main()