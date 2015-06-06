from time import sleep
import datetime as d
from subprocess import Popen
import json
import signal
import md5
import sys
import smtplib

config = json.loads(open('config.json', 'r').read())

class Downloader(object):
    def __init__(self):
        self.process = None

    def start(self):
        if self.process is not None:
            raise Exception('Cannot start process twice')
        
        self.process = Popen(['/usr/bin/env', 'python', config["dl_abs_script_path"]])

    def stop(self):
        if self.process is None:
            raise Exception('Process is already started')

        self.process.kill()
        self.process = None

    def started(self):
        return self.process is not None

def interval_to_datetimes(interval):
    now = d.datetime.now()
    interval_start = d.datetime(year=now.year,
                                month=now.month,
                                day=now.day,
                                hour=interval["start"]["h"],
                                minute=interval["start"]["m"])
    displaced_start = interval_start + d.timedelta(minutes=calculate_todays_variance())
    interval_end = displaced_start + d.timedelta(minutes=interval["duration"])

    return { "start": displaced_start, "end": interval_end }

def time_in_interval(time, interval):
    return time > interval["start"] and time < interval["end"]

def time_in_any_interval(time, intervals):
    for i in map(interval_to_datetimes, intervals):
        if time_in_interval(time, i):
            return True
    return False

def kill_downloader_and_exit(signal, frame):
    if dl.started():
        dl.stop()
    exit(0)

def calculate_todays_variance():
    hash_obj = md5.new()
    hash_obj.update(str(d.datetime.now().strftime('%Y-%m-%d')))
    todays_hash = hash_obj.hexdigest()
    todays_hash_ints = map(lambda ch: int(ch, 16), todays_hash)
    todays_sum = reduce(lambda a, b: a + b, todays_hash_ints)
    sign = -1 if todays_sum % 2 else 1
    signed_sum = sign * todays_sum
    return signed_sum % (config['time_variance']) if config['time_variance'] else 0

def send_mail(times_downloader_called):
    to = config['mail_to']
    mail_user = config['username']
    mail_pass = config['password']
    
    smtpserver = smtplib.SMTP("smtp.gmail.com", 587)

    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo()
    smtpserver.login(mail_user, mail_pass)
    header = 'To:' + to + '\n' + 'From: ' + mail_user + '\n' + 'Subject: Daily downloader status\n' + 'Content-Type: text/plain; charset=UTF-8'
    msg = header + '\n\nNumber of times started : %d' % times_downloader_called
    smtpserver.sendmail(mail_user, to, msg)
    print 'Mail sent !'
    smtpserver.close()


dl = Downloader()
intervals = config['intervals']

signal.signal(signal.SIGINT, kill_downloader_and_exit)
signal.signal(signal.SIGTERM, kill_downloader_and_exit)

daily_usage = 0;

while True:
    if d.datetime.now().hour == 0 and d.datetime.now().minute == 0:
        try:
            send_mail(daily_usage)
            daily_usage = 0
        except:
            print 'ERROR While sending e-mail'
            pass

    if dl.started():
        if not time_in_any_interval(d.datetime.now(), intervals):
            dl.stop()
            print d.datetime.now(), 'stopped downloader'
    else:
        if time_in_any_interval(d.datetime.now(), intervals):
            dl.start()
            daily_usage = daily_usage + 1
            print d.datetime.now(), 'started downloader'
    sleep(50)
