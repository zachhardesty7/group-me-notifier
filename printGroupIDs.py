# for accessing Heroku sys vars
import os
# to use secret file local data
import json
import logging
# GroupMe python wrapper
from groupy.client import Client

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
    LOGGER.warning(
        'no secret.json file present in project root, ignoring update')


# config vars
# os.environ == (heroku) environment global vars
# replace with local values if desired
# ex for each above definition
try:
    # 1234567890abcdef1234567890abcdef
    GROUPME_TOKEN = os.getenv('GROUPME_TOKEN') or DATA['GROUPME_TOKEN']
    CLIENT = Client.from_token(GROUPME_TOKEN)
except NameError:
    LOGGER.error('***all necessary global config not defined, see below***')
    raise


def main():
    for group in CLIENT.groups.list(omit="memberships").autopage():
        print(group.name + ' (' + group.id + ')')


if __name__ == '__main__':
    main()
