import json

import requests

from flask import Flask, request
from flow import Flow

from config import ORG_ID, CHANNEL_ID

flow = Flow('botbotbot')
app = Flask(__name__)


@app.route('/')
def index():
    flow.send_message(ORG_ID, CHANNEL_ID, 'botbotbot')
    return 'foo'


@app.route('/deployments/', methods=['POST'])
def failures():

    data = json.loads(request.data.decode('utf-8'))
    message_type = data['Type']

    if message_type == 'SubscriptionConfirmation':
        confirmation = requests.get(data['SubscribeURL'])

    elif message_type == 'Notification':

        message_data = json.loads(data['Message'])

        message = '{applicationName} ({deploymentGroupName}) deployment has the status {status}'.format(**message_data)

        flow.send_message(ORG_ID, CHANNEL_ID, message)

    return 'foop'


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1])
    app.run(port=port, debug=True)
