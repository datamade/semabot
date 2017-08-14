from flask import Flask
from flow import Flow

from config import ORG_ID, CHANNEL_ID

flow = Flow('botbotbot')
app = Flask(__name__)


@app.route('/')
def index():
    flow.send_message(ORG_ID, CHANNEL_ID, 'botbotbot')
    return 'foo'


if __name__ == "__main__":
    app.run()
