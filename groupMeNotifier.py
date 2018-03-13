# GroupMe python wrapper
from groupy.client import Client
# for accessing Heroku sys vars
import os
# for the actual sending function
import smtplib
# for emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# for timezone conversions
from pytz import timezone
import logging

# Use clock.py to run program every so often

# config vars
# os.environ == (heroku) environment global vars
# replace with local values if desired
# ex for each above definition

# 1234567890abcdef1234567890abcdef
GROUPME_TOKEN = os.environ['GROUPME_TOKEN']
# 12345678
GROUPME_GROUP_ID = os.environ['GROUPME_GROUP_ID']
# US/Central
LOCAL_TIMEZONE = os.environ['LOCAL_TIMEZONE']
# comma deliminated string of search terms
KEYWORDS = os.environ['KEYWORDS'].split(',')
EMAIL_TO_NAME = os.environ['EMAIL_TO_NAME']
EMAIL_TO_ADDRESS = os.environ['EMAIL_TO_ADDRESS']
EMAIL_FROM_ADDRESS = os.environ['EMAIL_FROM_ADDRESS']
# secure123.bluehost.com
EMAIL_HOST_URL = os.environ['EMAIL_HOST_URL']
EMAIL_HOST_USERNAME = os.environ['EMAIL_HOST_USERNAME']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_HOST_PORT = os.environ['EMAIL_HOST_PORT']

CLIENT = Client.from_token(GROUPME_TOKEN)
LAST_MESSAGE_ID = os.environ['LAST_MESSAGE_ID']

DEBUG = True
if DEBUG:
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def main():
    # print(os.environ['LAST_MESSAGE_ID'])
    group = CLIENT.groups.get(GROUPME_GROUP_ID)

    # for x in CLIENT.groups.get(GROUPME_GROUP_ID).messages.list(since_id="152096168211862649"):
    #     print(x)

    messages = getMessages(group)

    LOGGER.info('\nSTART ALL MESSAGES:')
    for message in messages:
        LOGGER.info(message)

    matches = getMessagesWithKeywords(messages)

    LOGGER.info('\nSTART MATCHES:')
    for message in matches:
        LOGGER.info(message)

    updateLastSeenMessage(messages)

    # print(os.environ['LAST_MESSAGE_ID'])

    if not DEBUG:
        if len(matches) > 0:
            emailBody = buildEmail(matches)
            sendEmail(emailBody, len(matches))
            print('email sent with %i matches' % len(matches))
        else:
            print('no new matches')


def buildEmail(messages):
    body = 'GroupMe Notifier has Found Matches!\n\n'

    body += '%i new messages matching keywords:\n' % len(messages)
    body += str(KEYWORDS) + '\n\n\n'

    for msg in messages:
        cst = timezone(LOCAL_TIMEZONE)
        time_local = msg.created_at.astimezone(cst).strftime('%I:%M:%S %p | %Y-%m-%d')
        body += str(time_local) + '\n'
        body += msg.name + ' - ' + msg.text + '\n\n'

    return body


def sendEmail(emailBody, numMsgs):
    emailMsg = MIMEMultipart('alternative')
    emailMsg['Subject'] = 'GroupMe Digest - %i New Chats' % numMsgs
    emailMsg['From'] = 'GroupMe Monitor'
    emailMsg['To'] = EMAIL_TO_NAME

    emailMsg.attach(MIMEText(emailBody, 'plain'))

    # Send the message via local SMTP server.
    mail = smtplib.SMTP_SSL(EMAIL_HOST_URL, EMAIL_HOST_PORT)

    mail.ehlo()

    mail.login(EMAIL_HOST_USERNAME, EMAIL_HOST_PASSWORD)
    mail.sendmail(EMAIL_FROM_ADDRESS, EMAIL_TO_ADDRESS, emailMsg.as_string())
    mail.quit()


def getMessagesWithKeywords(messages):
    matches = []

    for message in messages:
        if message.text is not None:
            maybeAdd = False
            for keyword in KEYWORDS:
                if keyword in message.text:
                    maybeAdd = True
            if maybeAdd:
                matches.append(message)

    return matches


def getMessages(group):
    if LAST_MESSAGE_ID == 0:
        return group.messages.list_all()
    else:
        return group.messages.list(since_id=str(LAST_MESSAGE_ID))


def updateLastSeenMessage(messages):
    lastMessage = None

    for message in messages:
        lastMessage = message
        break

    LOGGER.info('\nlast message')
    LOGGER.info(lastMessage.id)
    os.environ['LAST_MESSAGE_ID'] = lastMessage.id
    # LOGGER.info('\nlast message')
    # LOGGER.info(messages[0].id)
    # os.environ['LAST_MESSAGE_ID'] = messages[0].id


if __name__ == '__main__':
    main()
