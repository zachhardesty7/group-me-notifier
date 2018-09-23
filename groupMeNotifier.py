# for accessing Heroku sys vars
import os
# for the actual sending function
import smtplib
# for emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# to use secret file local data
import json
import logging
# to update environ var w Heroku
import requests
# GroupMe python wrapper
from groupy import Client
# for timezone conversions
from pytz import timezone

# initialize logger
DEBUG = False
if DEBUG:
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# import json file if present
try:
    with open('secret.json', 'r') as f:
        DATA = json.load(f)
        if not DATA:
            DATA = {}
except FileNotFoundError:
    LOGGER.warning(
        'no secret.json file present in project root to update, ignoring')

# Use clock.py to run program every so often

# config vars
# os.environ == (heroku) environment global vars
# replace with local values if desired
# ex for each above definition

# 1234567890abcdef1234567890abcdef
GROUPME_TOKEN = os.getenv('GROUPME_TOKEN') or DATA['GROUPME_TOKEN']
# 12345678,12345678,12345678,12345678
GROUPME_GROUP_IDS = os.getenv('GROUPME_GROUP_IDS') or DATA['GROUPME_GROUP_IDS']
if GROUPME_GROUP_IDS:
    GROUPME_GROUP_IDS = GROUPME_GROUP_IDS.split(',')
# US/Central
LOCAL_TIMEZONE = os.getenv('LOCAL_TIMEZONE') or DATA['LOCAL_TIMEZONE']
# comma deliminated string of search terms
KEYWORDS = os.getenv('KEYWORDS') or DATA['KEYWORDS']
EMAIL_TO_NAME = os.getenv('EMAIL_TO_NAME') or DATA['EMAIL_TO_NAME']
EMAIL_TO_ADDRESS = os.getenv('EMAIL_TO_ADDRESS') or DATA['EMAIL_TO_ADDRESS']
EMAIL_FROM_ADDRESS = os.getenv('EMAIL_FROM_ADDRESS') or DATA['EMAIL_FROM_ADDRESS']
# secure123.bluehost.com
EMAIL_HOST_URL = os.getenv('EMAIL_HOST_URL') or DATA['EMAIL_HOST_URL']
EMAIL_HOST_USERNAME = os.getenv('EMAIL_HOST_USERNAME') or DATA['EMAIL_HOST_USERNAME']
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD') or DATA['EMAIL_HOST_PASSWORD']
EMAIL_HOST_PORT = os.getenv('EMAIL_HOST_PORT') or DATA['EMAIL_HOST_PORT']

HEROKU_ACCESS_TOKEN = os.getenv('HEROKU_ACCESS_TOKEN') or DATA['HEROKU_ACCESS_TOKEN']
HEROKU_APP_ID = os.getenv('HEROKU_APP_ID') or DATA['HEROKU_APP_ID']
CLIENT = Client.from_token(GROUPME_TOKEN)
# 123456789012345678,123456789012345678,123456789012345678,123456789012345678
LAST_MESSAGE_IDS = os.getenv('LAST_MESSAGE_IDS') or DATA['LAST_MESSAGE_IDS']
if LAST_MESSAGE_IDS:
    LAST_MESSAGE_IDS = LAST_MESSAGE_IDS.split(',')


def main():
    allMessages = []

    for i, groupID in enumerate(GROUPME_GROUP_IDS):
        groups = CLIENT.groups.list_all(omit="memberships")
        group = {}
        for g in groups:
            if g.id == groupID:
                group = g

        last = LAST_MESSAGE_IDS[i]
        if last == 0:
            last = initializeLastID(group, i)
        newMessages = getMessages(group, last)

        updateLastSeenMessage(newMessages, i)
        for message in newMessages:
            allMessages.append(message)

    LOGGER.info('\nSTART ALL MESSAGES:')
    for message in allMessages:
        LOGGER.info(message)

    matches = filterMessages(allMessages)

    LOGGER.info('\nSTART MATCHES:')
    for message in matches:
        LOGGER.info(message)

    if not DEBUG:
        if matches:
            emailBody = buildEmail(matches)
            sendEmail(emailBody, len(matches))
            print('email sent with %i matches' % len(matches))
        else:
            print('no new matches')


def buildEmail(messages):
    body = ''

    for msg in messages:
        cst = timezone(LOCAL_TIMEZONE)
        time_local = msg.created_at.astimezone(cst).strftime('%I:%M:%S %p | %Y-%m-%d')
        body += str(time_local) + '\n'
        body += msg.name + ' - ' + msg.text + '\n\n'

    body += 'target keywords:\n' % len(messages)
    body += str(KEYWORDS) + '\n\n\n'

    return body


def sendEmail(emailBody, numMsgs):
    emailMsg = MIMEMultipart('alternative')
    emailMsg['Subject'] = 'GroupMe Digest - %i New Matches' % numMsgs
    emailMsg['From'] = 'GroupMe Monitor'
    emailMsg['To'] = EMAIL_TO_NAME

    emailMsg.attach(MIMEText(emailBody, 'plain'))

    # Send the message via local SMTP server.
    mail = smtplib.SMTP_SSL(EMAIL_HOST_URL, EMAIL_HOST_PORT)

    mail.ehlo()

    mail.login(EMAIL_HOST_USERNAME, EMAIL_HOST_PASSWORD)
    mail.sendmail(EMAIL_FROM_ADDRESS, EMAIL_TO_ADDRESS, emailMsg.as_string())
    mail.quit()


def filterMessages(messages):
    matches = []

    for message in messages:
        if message.text is not None:
            if any(keyword in message.text for keyword in KEYWORDS.split(',')):
                matches.append(message)

    return matches


def getMessages(group, lastID):
    return group.messages.list_all_after(lastID)


def initializeLastID(group, i):
    LOGGER.log('now initialized, new messages will show in notification email')
    recentMessages = group.messages.list()
    for message in recentMessages:
        LAST_MESSAGE_IDS[i] = message.id
        return message.id


def updateLastSeenMessage(messages, i):
    for message in messages:
        LAST_MESSAGE_IDS[i] = message.id
        break

    # setting os.environ really doesn't do anything apparently,
    # using heroku api to update for my use case
    os.environ['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)

    # set using json file
    try:
        DATA['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)
        with open("secret.json", "w") as f2:
            json.dump(DATA, f2)
    except FileNotFoundError:
        LOGGER.warning('no secret.json file present in project root to update, ignoring')


    url = 'https://api.heroku.com/apps/' + HEROKU_APP_ID + '/config-vars'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/vnd.heroku+json; version=3',
        'Authorization': 'Bearer ' + HEROKU_ACCESS_TOKEN
    }

    payload = 'LAST_MESSAGE_ID=' + ','.join(LAST_MESSAGE_IDS)

    requests.patch(url, headers=headers, data=payload)


if __name__ == '__main__':
    main()
