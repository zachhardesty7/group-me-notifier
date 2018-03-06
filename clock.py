from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess

sched = BlockingScheduler()


@sched.scheduled_job('interval', day_of_week='mon-sun', minutes=30, timezone='UTC')
def updatePriceData():
    print('Scheduled bi-hourly run')
    subprocess.run('python3 groupMeNotifier.py', shell=True)


sched.start()
