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

# Use clock.py to run program every so often

# Groupy Docs
# http://groupy.readthedocs.io/en/latest/pages/api.html

# config vars
# os.environ == heroku app global vars
# replace os.environ[] with local value if desire
GROUPME_TOKEN = os.environ['GROUPME_TOKEN']
GROUPME_GROUP_ID = os.environ['GROUPME_GROUP_ID']
LOCAL_TIMEZONE = os.environ['LOCAL_TIMEZONE']
KEYWORDS = os.environ['KEYWORDS'].split(',')
EMAIL_TO_NAME = os.environ['EMAIL_TO_NAME']
EMAIL_TO_ADDRESS = os.environ['EMAIL_TO_ADDRESS']
EMAIL_FROM_ADDRESS = os.environ['EMAIL_FROM_ADDRESS']
EMAIL_HOST_URL = os.environ['EMAIL_HOST_URL']
EMAIL_HOST_USERNAME = os.environ['EMAIL_HOST_USERNAME']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_HOST_PORT = os.environ['EMAIL_HOST_PORT']

CLIENT = Client.from_token(GROUPME_TOKEN)
LAST_MESSAGE_ID = os.environ['LAST_MESSAGE_ID']


def main():
    group = CLIENT.groups.get(GROUPME_GROUP_ID)

    messages = getMessages(group)

    matches = getMessagesWithKeywords(messages)

    if len(matches) > 0:
        emailBody = buildEmail(matches)
        sendEmail(emailBody, len(matches))
        updateLastSeenMessage(messages)
        print('email sent with %i matches', len(matches))
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
        return group.messages.list(since_id=LAST_MESSAGE_ID)


def updateLastSeenMessage(messages):
    lastMessage = None

    for message in messages:
        lastMessage = message
        break

    os.environ['LAST_MESSAGE_ID'] = lastMessage.id


if __name__ == '__main__':
    main()
