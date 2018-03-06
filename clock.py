from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-sun', hour=0, timezone='UTC')
@sched.scheduled_job('cron', day_of_week='mon-sun', hour=12, timezone='UTC')
def updatePriceData():
    print('Scheduled bi-daily run')
    subprocess.run('python3 groupMeNotifier.py', shell=True)


sched.start()
