from flow import Flow

from config import ORG_ID, CHANNEL_MAP, BOTNAME, BOTPW, NICE_NAMES

try:
    flow = Flow(BOTNAME)
except flow.FlowError:
    flow = Flow()
    flow.create_device(BOTNAME, BOTPW)


class MessageHandler(object):
    def __init__(self, message, sender_id, channel_id):
        self.message = message.lower().strip()
        self.sender_id = sender_id
        self.channel_id = channel_id
        self.sender_name = flow.get_peer_from_id(sender_id)["username"]

    def respond(self):

        response = None

        if self.message == 'help':
            response = self.helpText()

        if response:
            flow.send_message(ORG_ID, self.channel_id, response)

    def helpText(self):
        projects = []

        for slug, channel_id in CHANNEL_MAP.items():
            if slug in ['devops', 'bot-testing']:
                message = '**Hi there {}!**\n'.format(self.sender_name)
                message += '''
Here are the things you can do:
  `awslogs list`: Returns a list of log groups we have configured
  `awslogs <log group name> list`: Returns a list of log streams for the given log group
  `awslogs <log group name>:<log stream name>`: Returns the last 24 hours of logs for the given log stream
  `awslogs <log group name> search <query>`: Searches an entire log group for the last 24 hours for the given query
  `awslogs <log group name>:<log stream name> search <query>`: Searches a log stream for the last 24 hours for the given query
                '''

        return message

    def awsLogs(self, message):
        pass


@flow.message
def respond(notif_type, data):
    regular_messages = data["regularMessages"]

    for message in regular_messages:

        sender_id = message["senderAccountId"]

        if sender_id != flow.account_id():

            channel_id = message["channelId"]
            message = message["text"]

            handler = MessageHandler(message, sender_id, channel_id)
            handler.respond()


if __name__ == "__main__":
    import sys
    import signal

    try:
        deployment_id = sys.argv[1]
    except IndexError:
        deployment_id = ''

    with open('/tmp/bot_running.txt', 'w') as f:
        f.write(deployment_id)

    def signalHandler(signum, frame):
        flow.set_processing_notifications(value=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    print('Listening for notifications ...')
    flow.process_notifications()
