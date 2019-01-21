# for accessing Heroku sys vars
import os
# to use secret file local data
import json
# GroupMe python wrapper
from groupy.client import Client

# import json file if present
try:
    with open('secret.json', 'r') as f:
        DATA = json.load(f)
        if not DATA:
            DATA = {}
except (NameError, FileNotFoundError):
    print('WARNING: no secret.json file present in project root, ignoring update')

# config vars
# os.environ == (heroku) environment global vars
# replace with local values if desired
# ex for each above definition
try:
    # 1234567890abcdef1234567890abcdef
    GROUPME_TOKEN = os.getenv('GROUPME_TOKEN') or DATA['GROUPME_TOKEN']
    CLIENT = Client.from_token(GROUPME_TOKEN)
except NameError:
    raise Exception('***all necessary global config not defined***')


def getIDs():
    for group in CLIENT.groups.list(omit="memberships").autopage():
        print(group.name + ' (' + group.id + ')')


if __name__ == '__getIDs__':
    getIDs()
