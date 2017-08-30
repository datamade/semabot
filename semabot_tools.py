from flow import Flow

from config import BOTNAME, BOTPW, ORG_ID

try:
    flow = Flow(BOTNAME)
except flow.FlowError as e:
    flow = Flow()
    flow.create_device(BOTNAME, BOTPW)
    print('Device for bot {} created'.format(BOTNAME))

def print_channels():
    print('\033[1mYour bot "{}" has access to these channels:\033[0m\n'.format(BOTNAME))

    for channel in flow.enumerate_channels(ORG_ID):
        print('\033[91m\033[1m"{name}":\033[0m \033[94m{id}\033[0m'.format(**channel))

if __name__ == "__main__":
    print_channels()
