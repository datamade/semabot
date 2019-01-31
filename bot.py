from datetime import datetime, timedelta

import boto3

from flow import Flow

from config import ORG_ID, CHANNEL_MAP, BOTNAME, BOTPW

try:
    flow = Flow(BOTNAME)
except flow.FlowError:
    flow = Flow()
    flow.create_device(BOTNAME, BOTPW)


class MessageHandler(object):
    def __init__(self, message, sender_id, channel_id):
        self.message = message.lower().strip()
        self.raw_message = message.strip()
        self.sender_id = sender_id
        self.channel_id = channel_id
        self.sender_name = flow.get_peer_from_id(sender_id)["username"]

    def respond(self):

        response = None

        if self.message == 'help':
            response = self.helpText()
        elif self.message.startswith('awslogs'):
            response = self.awsLogs()

        if response:
            flow.send_message(ORG_ID, self.channel_id, response)

    def helpText(self):

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

    def awsLogs(self):
        # In order for this to work, you need to have AWS credentials configured
        # for the user that is running the script or, in the case of an EC2
        # instance, you can also add a server level policy that allows these
        # calls to happen. More here:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials

        client = boto3.client('logs')

        message_parts = self.raw_message.split(' ')

        # Pretty stupid way of doing this but it was fast
        if len(message_parts) == 2:

            if len(message_parts[-1].split(':')) == 2:
                log_group, stream = message_parts[-1].split(':')
                response = '**Last 24 hours of {}-{}**'.format(log_group, stream)

                a_day_ago = datetime.now() - timedelta(hours=24)
                a_day_ago = int(a_day_ago.timestamp()) * 1000

                results = client.filter_log_events(logGroupName=log_group,
                                                   logStreamNames=[stream],
                                                   startTime=a_day_ago)

                messages = '\n'.join([m['message'] for m in results['events']])

                response = '```\n{}\n```'.format(messages)

            elif message_parts[-1] == 'list':
                log_groups = client.describe_log_groups()
                response = '**Log Groups**\n'
                response += '\n'.join(['* {}'.format(g['logGroupName']) for g in log_groups['logGroups']])

        elif len(message_parts) == 3:
            log_group_name = message_parts[1]
            log_group_streams = client.describe_log_streams(logGroupName=log_group_name)
            response = '**Log Streams for {}**\n'.format(log_group_name)
            response += '\n'.join(['* {}'.format(g['logStreamName']) for g in log_group_streams['logStreams']])

        elif len(message_parts) == 4:
            _, location, _, query = message_parts

            if len(location.split(':')) == 2:
                log_group, stream = location.split(':')
                results = client.filter_log_events(logGroupName=log_group,
                                                   logStreamNames=[stream],
                                                   filterPattern=query,
                                                   limit=50)

            else:
                results = client.filter_log_events(logGroupName=location,
                                                   filterPattern=query,
                                                   limit=50)

            if results['events']:
                messages = '\n'.join([m['message'] for m in results['events']])
                response = '**Log events matching "{}"**\n'.format(query)
                response += '```\n{}\n```'.format(messages)
            else:
                response = '**No results**'

        return response


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

    # Setup a closure to handle gracefully stopping the processing of
    # notifications.
    def signalHandler(signum, frame):
        flow.set_processing_notifications(value=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    print('Listening for notifications ...')

    # This runs in an infinite loop and passes any notifications it receives to
    # the function decorated above with "@flow.message". From there, we do
    # a little processing and then hand the message off to the class above that
    # works out how to respond.
    flow.process_notifications()
