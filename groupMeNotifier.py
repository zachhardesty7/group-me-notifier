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
from groupy.client import Client
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
except (NameError, FileNotFoundError):
    LOGGER.warning('no secret.json file present in project root, ignoring update')

# Use clock.py to run program every so often in Heroku

# config vars
# os.environ == (heroku) environment global vars
# replace with local values if desired
# ex for each above definition
try:
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

    USE_HEROKU_HOSTING = os.getenv('USE_HEROKU_HOSTING') or DATA['USE_HEROKU_HOSTING']
    HEROKU_ACCESS_TOKEN = os.getenv('HEROKU_ACCESS_TOKEN') or DATA['HEROKU_ACCESS_TOKEN']
    HEROKU_APP_ID = os.getenv('HEROKU_APP_ID') or DATA['HEROKU_APP_ID']
    CLIENT = Client.from_token(GROUPME_TOKEN)
    # 123456789012345678,123456789012345678,123456789012345678,123456789012345678
    LAST_MESSAGE_IDS = os.getenv('LAST_MESSAGE_IDS') or DATA['LAST_MESSAGE_IDS']
    if LAST_MESSAGE_IDS:
        LAST_MESSAGE_IDS = LAST_MESSAGE_IDS.split(',')
except NameError:
    LOGGER.error('***all necessary global config not defined, see below***')
    raise


def main():
    allMessages = []

    for i, groupID in enumerate(GROUPME_GROUP_IDS):
        group = {}
        # list_all fails more than list().autopage()
        # retrieving group by ID doesn't allow "omit" param
        # without "omit" large groups overflow json request max size
        for g in CLIENT.groups.list(omit="memberships").autopage():
            if g.id == groupID:
                group = g

        last = LAST_MESSAGE_IDS[i]
        if last == 0:
            last = initializeLastID(group, i)
        newMessages = getMessages(group, last)

        updateLastSeenMessage(newMessages, i)
        for message in newMessages:
            message.group = group.name
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

    for message in messages:
        cst = timezone(LOCAL_TIMEZONE)
        time_local = message.created_at.astimezone(cst).strftime('%I:%M:%S %p | %m%d%y')
        body += str(time_local) + '\n'
        body += message.group + '\n'
        body += message.name + ' - ' + message.text + '\n\n'

    body += '{0} target keywords:\n'.format(len(KEYWORDS.split(',')))
    body += str(KEYWORDS.replace(',', ', ')) + '\n\n\n'

    return body


def sendEmail(emailBody, numMsgs):
    emailMsg = MIMEMultipart('alternative')
    emailMsg['Subject'] = 'GroupMe Digest - {0} New Matches'.format(numMsgs)
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
    try:
        # use list_since().autopage() instead of list_all_after()
        # to get most recent messages first
        return group.messages.list_since(lastID).autopage()
    except: # pylint: disable=W0702
        # unsure of error type when raised by groupy
        # error appears spontaneously with no apparent reason
        LOGGER.warning('http authentication error, retrying')
        return getMessages(group, lastID)


# if there is no most recent ID, set it now to most recent message
# prevents dangerously long json responses from searching entire group
def initializeLastID(group, i):
    LOGGER.log('now initialized, new messages will show in notification email')
    recentMessages = group.messages.list()
    for message in recentMessages:
        LAST_MESSAGE_IDS[i] = message.id
        return message.id


def updateLastSeenMessage(messages, i):
    # generators cannot be indexed
    for message in messages:
        LAST_MESSAGE_IDS[i] = message.id
        break

    # setting os.environ doesn't affect Heroku, use api calls instead
    os.environ['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)

    # try to update through json file
    try:
        DATA['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)
        with open("secret.json", "w") as f2:
            json.dump(DATA, f2)
    except (NameError, FileNotFoundError):
        LOGGER.warning('no secret.json file present in project root, ignoring update')

    if USE_HEROKU_HOSTING.lower() == 'True':
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
