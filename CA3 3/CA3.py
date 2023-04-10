"""Website that helps with covid. Gets weather, news, and number of cases"""

import json
import logging
import time as t
from datetime import date
import sched
from flask import Flask, request, render_template, redirect
import pyttsx3
import requests
from time_conversions import hhmm_to_seconds, current_time_hhmm

s = sched.scheduler(t.time, t.sleep)
app = Flask(__name__)
engine = pyttsx3.init()
notification = []
alarms = []
banned = []
FORMAT = '%(levelname)s:%(asctime)s%(message)s'
logging.basicConfig(filename="sys.log", encoding='utf-8',level=logging.DEBUG, format=FORMAT)
logging.basicConfig(filename="sys1.log", encoding='utf-8',level=logging.DEBUG, format=FORMAT)


with open ('config.json', 'r') as f:
    json_file = json.load(f)
keys = json_file['API-keys']


def get_articles (name = "", source = ""):

    """Gets all the articles given a topic(name) and source such as Covid"""

    base_url = "https://newsapi.org/v2/top-headlines?"
    newsapi_key=keys['news']
    country = "gb"
    complete_news_url = base_url + "country=" + country + "&apiKey=" + newsapi_key
    response = requests.get(complete_news_url).json()
    news_articles = response["articles"]
    ret_news=[]
    for article in news_articles:
        if name in article['title']:
            if(article['source']['name']==source or source==""):
                ret_news.append(article)
    return ret_news
def get_weather ():

    """GEts the weather in a city, in this example London but can be used anywhere"""

    base_url = "https://api.openweathermap.org/data/2.5/weather?"
    weatherapi_key = keys['weather']
    city="London"
    complete_url = base_url + "q=" + city + "&APPID=" + weatherapi_key

    stats_js=requests.get(complete_url).json()
    stat_fin=stats_js["main"]
    current_temperature = stat_fin["temp"]
    current_pressure = stat_fin["pressure"]
    current_humidiy = stat_fin["humidity"]
    weath = stats_js["weather"]
    weather_description = weath[0]["description"]
    text=" Temperature (in kelvin unit) = "+ str(current_temperature) + "\n atmospheric pressure (in hPa unit) = " + str(current_pressure) + "\n humidity (in percentage) = " + str(current_humidiy) + "\n description = " + str(weather_description)
    return {'title': 'weather', 'content': text}

def announce(announcement):

    """Announces what it is given out loud"""

    try:
        engine.endLoop()
    except:
        logging.error('PyTTSx3 Endloop error')
    engine.say(announcement)
    engine.runAndWait()

def restore_alarms():

    """Checks the log file if there are any alarms there that should be recreated"""

    with open('sys.log') as logfile:
        for line in logfile.readlines():
            if line[:4]=="INFO" and "alarm=" in line:
                temp_alarm=""
                args=line.split(' ')
                temp_alarm=temp_alarm+args[-4][19:21] + ":" + args[-4][24:26]
                if args[-4][8] == '2':
                    if hhmm_to_seconds(temp_alarm)>hhmm_to_seconds(current_time_hhmm()):

                        temp_alarm = args[-4][8:18] +" "+ temp_alarm
                        alarms.append({'title':args[-4][31:], 'content':temp_alarm})


def clear_logs():
    """"clears logs"""
    with open('sys.log','w'):
        pass
    with open('sys1.log', 'w'):
        pass
def refresh_alarms():

    """refreshes the alarms and checks if any of them are already apst their set date"""

    index=[]
    for i in alarms:
        temp=i['content'][:11]
        temp=temp.split('-')
        temp=date(int(temp[0]),int(temp[1]), int(temp[2]))
        if date.today()>temp:
            index.append(alarms.index(i))
        elif date.today()==temp and hhmm_to_seconds(i['content'][11:16])< hhmm_to_seconds(current_time_hhmm()):
            index.append(alarms.index(i))
    index=list(dict.fromkeys(index))
    for i in range(len(index)-1,-1,-1):
        delete_alarms_log(alarms[i]['title'])
def check_alarms():

    """checks if any alarms are active, if not it will return the last notification"""

    notification=[]
    for i in alarms:
        if hhmm_to_seconds(i['content'][11:16])== hhmm_to_seconds(current_time_hhmm()):
            banned.clear()
            s.enter(1,1,announce,(i['title'],))
            if 'news' in i['content']:
                notification = get_articles("Covid")
            if 'weather' in i['content']:
                notification.append(get_weather())
            s.run()
            return notification

    try:

        if 'news' in alarms[len(alarms)-1]['content']:
            notification = get_articles("Covid")
        if 'weather' in alarms[len(alarms)-1]['content']:
            notification.append(get_weather())
        elif 'news' not in alarms[len(alarms)-1]['content'] and 'weather' not in alarms[len(alarms)-1]['content']:
            notification=[]
        
        for i in banned:
            for notif in notification:
                if notif['title'] == i:
                    notification.remove(notif)
        return notification
    except IndexError:
        notification = []
        return notification

@app.route('/')
def home():

    """first method run, creates the website"""

    notifications = []
    refresh_alarms()
    if alarms == []:
        restore_alarms()
    alarm_time = request.args.get("alarm")
    if alarm_time:
        banned.clear()
        weather = request.args.get("weather")
        news = request.args.get("news")
        if news is not None :
            notifications = get_articles("Covid")
        if weather is not None:
            notifications.append(get_weather())
        logging.info(alarm_time)
        announcement=request.args.get("two")
        alarm_time=alarm_time.replace('T', ' ')
        alarm_time=alarm_time + str(weather) + str(news)
        addition = {'title': str(announcement), 'content':alarm_time}
        alarms.append(addition)
    temp=check_alarms()
    if temp is not None:
        notifications = temp
    if notifications == []:
        notifications = check_alarms()
    return render_template("template.html", alarms=alarms,
                           title='Daily update', image='meme.jpg', notifications = notifications)

@app.route('/deletealarm')
def delete_alarms_log(name=""):

    """deletes the specific log from the logfile so it will not get recreated later"""

    if name == "":
        name = request.args.get("alarm_item")
    with open('sys.log') as logfile:
        lines = logfile.readlines()
        logfile.close()
        with open('sys1.log','w') as logfile1:
            for line in lines:
                if line[:4] !="INFO" or ("alarm" not in line and "/delete" not in line)or name not in line:
                    logfile1.write(line)
        logfile1.close()
    with open('sys1.log') as logfile:
        lines = logfile.readlines()
        logfile.close()
        with open('sys.log', 'w') as logfile1:
            for line in lines:
                logfile1.write(line)
        logfile1.close()
    for i in alarms:
        if i['title'] == '':
            alarms.remove(i)
        elif i['title'] == name:
            alarms.remove(i)
    return redirect('/')

@app.route('/deletenotification')
def delete_notif(name=""):
    
    """deleting the selected notification"""

    if name =="":
        name = request.args.get('notif')
        banned.append(name)
    #notification = check_alarms()['title']
    return redirect('/')
    
if __name__ == '__main__':
    logging.info('System starting')
    app.run()
