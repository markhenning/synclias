## Current app state
from flask import current_app
from celery import current_app as celery_app
from synclias import db

#from redbeat.schedules import rrule
from redbeat import RedBeatSchedulerEntry
from celery import schedules

# Models
from synclias.models import Prefs

## Celery
from synclias import create_celery_app

celery = create_celery_app()

### This is a messy hack, TODO - tighten
def crontab_hours(hours):
    if hours == 1:
        tab_hours = "*"
    elif hours == 24:
        tab_hours = "0"
    else:
        tab_hours = f"*/{hours}"
    return tab_hours

def crontab_days(days):
    if days == 7:
        tab_days = "1,7,15,22,29"
    elif days == 14:
        tab_days = "1,15,29"
    elif days == 30:
        tab_days = "1"

    return tab_days

def crontab_mins(mins):
    
    return mins


def create_schedule(every_x,unit):
    if unit == "hours":
        interval = schedules.crontab(minute="0", hour=crontab_hours(every_x))
    elif unit == "mins":
        interval = schedules.crontab(minute=crontab_mins(every_x)) ## Yes, this isn't every x, but needs a cron string
    else:
        interval = schedules.crontab(minute="0", hour="0", day_of_month=(crontab_days(every_x)))

    return interval
        

# def create_schedule(every_x,freq):
#     ## Set the start time to 00:00 today, so we don't have to worry about odd scheduling times
#     midnight = datetime.today().replace(hour = 0, minute = 0, second = 0, microsecond = 0)
#     schedule = rrule(freq=freq, interval=every_x, dtstart=midnight)
#     return schedule

# def schedule_task(name,every_x,frequency,task,enabled):       
#     interval = create_schedule(every_x,frequency)
#     entry = RedBeatSchedulerEntry(name,
#         task=task,
#         schedule=interval, 
#         app=celery_app,
#         enabled=enabled,                     
#         )
#     entry.save()
#     current_app.logger.info(f"SCHEDULER - Updated {name} to every {every_x} {frequency}, enabled = {enabled}")

def schedule_task(name,every_x,frequency,task,enabled):
    
    ## This should be fixed further up the chain, but, for now, it works
    if enabled == 1 :
        enabled = True
    elif enabled == 0:
        enabled = False      
    interval = create_schedule(every_x,frequency)
    entry = RedBeatSchedulerEntry(name,
        task=task,
        schedule=interval, 
        app=celery_app,
        enabled=enabled,                     
        )
    entry.save()
    current_app.logger.info(f"SCHEDULER - Updated {name} to every {every_x} {frequency}, enabled = {enabled}")


## Since "name" for scheduled task is unique, create and update are essentially the same thing for this simeple task, rather than extra logic, just overwrite
def create_update_autosync_task():
    prefs = db.session.query(Prefs).first()
    if prefs is not None:
        schedule_task(name="autosync",every_x=prefs.sync_every,frequency="hours",task='synclias.blueprints.syncer.tasks.run_syncer',enabled=prefs.autosync)
    ## else: mad panic
    return True ## TODO - Fix this, it's terrible
    
def create_update_autoasndb_task():
    prefs = db.session.query(Prefs).first()
    if prefs is not None:
        schedule_task(name="autoasndb",every_x=prefs.asndb_every,frequency="days",task='synclias.blueprints.asndb.tasks.download_asn_db_and_names',enabled=prefs.autoasndb)
    return True ## TODO - Fix this, it's terrible

def create_update_ip_history_scan_task():
    prefs = db.session.query(Prefs).first()
    if prefs is not None:
        schedule_task(name="ip_history_scan",every_x="*",frequency="mins",task='synclias.blueprints.ip_history.tasks.update_all_dns_history',enabled=True)
    return True ## TODO - Fix this, it's terrible

## Super simple task to run every 30 mins to make sure the autosync/asndb tasks exist, in case of redis clears/app errors etc
@celery.task
def ensure_auto_tasks_exist():
    create_update_autosync_task()
    create_update_autoasndb_task()