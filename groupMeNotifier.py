# for accessing Heroku sys vars
import os
# for the actual sending function
import smtplib
# for emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# to use secret file local data
import json
# to update environ var w Heroku
import requests
# GroupMe python wrapper
from groupy.client import Client
# for timezone conversions
from pytz import timezone

# change for slightly more verbose logging
DEBUG = False

# import json file if present
try:
    with open('secret.json', 'r') as f:
        DATA = json.load(f)
        if not DATA:
            DATA = {}
# TODO: refactor out excess try except blocks
except (NameError, FileNotFoundError):
    print('WARNING: no secret.json file present in project root, trying to use environment vars')

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
    # comma deliminated string of search terms
    KEYWORDS = os.getenv('KEYWORDS') or DATA['KEYWORDS']
    IGNORED_USERS = os.getenv('IGNORED_USERS') or DATA['IGNORED_USERS']
    # 123456789012345678,123456789012345678,123456789012345678,123456789012345678
    LAST_MESSAGE_IDS = os.getenv('LAST_MESSAGE_IDS') or DATA['LAST_MESSAGE_IDS']
    if LAST_MESSAGE_IDS:
        LAST_MESSAGE_IDS = LAST_MESSAGE_IDS.split(',')

    # US/Central
    LOCAL_TIMEZONE = os.getenv('LOCAL_TIMEZONE') or DATA['LOCAL_TIMEZONE']
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
except NameError:
    raise Exception('***all necessary global config not defined***')


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

        if not group:
            print('WARNING: skipping invalid groupID: %s' % groupID)
        else:
            last = LAST_MESSAGE_IDS[i]
            if last == 0:
                last = initializeLastID(group, i)
            newMessages = group.messages.list_since(last).autopage()

            # generators cannot be indexed
            # update env var with most recent message id
            for message in newMessages:
                LAST_MESSAGE_IDS[i] = message.id
                break

            # add group name to individual message data
            # not incl by default in Groupy wrapper
            for message in newMessages:
                message.group = group.name
                allMessages.append(message)

    matches = filterMessages(allMessages)

    if not matches:
        print('INFO: no new matches')
    elif DEBUG:
        print('\nINFO: MATCHED MESSAGES:')
        for message in matches:
            print(message)
    else:
        emailBody = buildEmail(matches)
        sendEmail(emailBody, len(matches))
        print('INFO: email sent with %i matches' % len(matches))

    updateLastSeenMessage() # will restart program on heroku


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


def sendEmail(emailBody, numMessages):
    emailMsg = MIMEMultipart('alternative')
    emailMsg['Subject'] = 'GroupMe Digest - {0} New Matches'.format(numMessages)
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
    keywords = KEYWORDS.split(',')
    users = IGNORED_USERS.split(',')

    for message in messages:
        if message.text is not None:
            name = message.name.lower()
            body = message.text.lower()
            if (any(keyword in body for keyword in keywords)
                    and not any(user == name for user in users)):
                matches.append(message)

    return matches


# if there is no most recent ID, set it now to most recent message
# prevents dangerously long json responses from searching entire group
def initializeLastID(group, i):
    recentMessages = group.messages.list()
    for message in recentMessages:
        LAST_MESSAGE_IDS[i] = message.id
        return message.id


def updateLastSeenMessage():
    # setting os.environ doesn't affect Heroku, use api calls instead
    os.environ['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)

    # try to update through json file
    try:
        DATA['LAST_MESSAGE_IDS'] = ','.join(LAST_MESSAGE_IDS)
        with open("secret.json", "w") as f2:
            json.dump(DATA, f2)
    except (NameError, FileNotFoundError):
        print('WARNING: no secret.json file present in project root, ignoring update')

    if USE_HEROKU_HOSTING.lower() == 'true': # heroku vars are strings
        url = 'https://api.heroku.com/apps/' + HEROKU_APP_ID + '/config-vars'

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/vnd.heroku+json; version=3',
            'Authorization': 'Bearer ' + HEROKU_ACCESS_TOKEN
        }

        payload = 'LAST_MESSAGE_IDS=' + ','.join(LAST_MESSAGE_IDS)

        requests.patch(url, headers=headers, data=payload)


if __name__ == '__main__':
    main()
