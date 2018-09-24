import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()


@sched.scheduled_job('interval', minutes=10, timezone='UTC')
def updatePriceData():
    print('Scheduled run')
    subprocess.run('python3 groupMeNotifier.py', shell=True)


sched.start()
