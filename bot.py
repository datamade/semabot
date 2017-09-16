from flow import Flow

from config import ORG_ID, CHANNEL_MAP, BOTNAME, BOTPW, NICE_NAMES

try:
    flow = Flow(BOTNAME)
except flow.FlowError as e:
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
        elif self.message == 'last deployment':
            response = self.lastDeployment()
        elif self.message == 'last error':
            response = self.lastError()
        elif self.message == 'last commit':
            response = self.lastCommit()
        elif self.message == 'last comment':
            response = self.lastComment()
        elif self.message == 'last issue':
            response = self.lastIssue()
        elif self.message == 'last branch':
            response = self.lastBranch()
        elif self.message == 'last build':
            response = self.lastBuild()
        elif self.message.startswith('stats since'):
            response = self.stats()

        if response:
            flow.send_message(ORG_ID, self.channel_id, response)

    def helpText(self):
        projects = []

        for slug, channel_id in CHANNEL_MAP.items():
            if channel_id == self.channel_id:
                projects.append(NICE_NAMES[slug])

        message = '**Hi there {}!**\n'.format(self.sender_name)
        message += 'The projects associated with this channel are: \n{}'.format('\n  '.join(projects))
        message += '\n{}\n'.format('*' * 50)
        message += '''
Here are the things you can do:
  `last error`: Returns the last error message logged in this channel from sentry
  `last commit`: Returns the last commit logged in this channel from Github
  `last comment`: Returns the last comment logged in this channel from Github
  `last issue`: Returns the last issue logged in this channel from Github
  `last deployment`: Returns the last deployment logged in this channel from CodeDeploy
  `last build`: Returns the last build from Travis
  `stats since <datetime>`: Returns error and deployment counts since a given time for this channel
        '''

        return message

    def lastError(self):
        return "Not yet implemented"

    def lastCommit(self):
        return "Not yet implemented"

    def lastComment(self):
        return "Not yet implemented"

    def lastIssue(self):
        return "Not yet implemented"

    def lastBranch(self):
        return "Not yet implemented"

    def lastDeployment(self):
        response = 'No deployment found'

        for message in flow.enumerate_messages(ORG_ID, self.channel_id):
            if 'aws codedeploy' in message['text']:
                response = message['text']
                break

        return response

    def stats(self):
        return "Not yet implemented"

    def lastBuild(self):
        return "Not yet implemented"


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
