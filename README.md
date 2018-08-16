# SEMABOT

See [`config.py.example`](config.py.example) to add your app to Semabot
(DataMaders) or configure a Semabot of your own (everyone else)! 

### Installing the requirements

This app relies upon SpiderOak's [flow-python](https://github.com/SpiderOak/flow-python) project to post messages to Semaphor. Unfortunately, it seems that the way that it is packaged doesn't make it possible to be pip installed. Instead, you need to clone their repo, activate the virtual environment that you'd like to install it into, and then run the `setup.py` script that's distributed with the project.

```
git clone https://github.com/SpiderOak/flow-python
cd flow-python
workon <name of virtualenv>
python setup.py install
```

Once that is taken care of, you should be able to install the rest of the
requirements using `pip`:

```
cd <path to semabot>
pip install -r requirements.txt
```

#### Alternative installation patterns

Running `pip install` in a brand new virtualenv should clone `flow-python` onto your local machine. For that reason, you can also do the following to get Semabot up-and-running locally.

```
# Make a new vitual environment, downgrade pip, and install requirements
mkvirtualenv semabot
pip install --upgrade 'pip<10'
pip install -r requirements.txt
```

Sanity check! The install log should show that `python-flow` originates from Github:

```
Obtaining flow-python from git+https://github.com/SpiderOak/flow-python.git#egg=flow-python (from -r requirements.txt (line 2))
```

Visit your installation of `python-flow`, and manually install it in your virtualenv:

```
# example path (Mac OS)
cd /Users/<your user name>/.virtualenvs/semabot/src/flow-python

python setup.py install
```

### Adding a new channel (DataMaders)

Do you want to log Sentry errors to Semaphor? tell your friends about successful deployments? know when Travis does its business? Follow these steps.

1. Create a new project channel in Semaphor.
2. Add botbotbot as a member.
3. Update `CHANNEL_MAP`, `TRAVIS_MAP`, and `NICE_NAMES` in config.py.gpg. Getting the correct channel ID may require a little patience. First, try to run:

```
python semabot_tools.py
```

`python-flow` expects your Semaphor installation to reside in a particular location with a particular name. Watch out for the following error:

```
# Mac OS error
FileNotFoundError: [Errno 2] No such file or directory: '/Applications/Semaphor.app/Contents/Resources/app/build-version.json’
```

In this case, you can copy, move, and/or sneakily rename Semaphor to the location that `python-flow` expects. Then, run `semabot_tools` again (possibly, multiple times!) - until you see something like:

```
Your bot "botbotbot" has access to these channels:

"large-lots": XXXXXXXXXXXXXXXXXXXXX
"ocd": XXXXXXXXXXXXXXXXXXXXX
"ihs": XXXXXXXXXXXXXXXXXXXXX
"bga-payroll-database": XXXXXXXXXXXXXXXXXXXXX
"your-new-channel": XXXXXXXXXXXXXXXXXXXXX
```

Paste the ID into the config. 

Finally, in the `.travis` file of your application, add the webhook below, and enjoy your message thread in Semaphor!

```
notifications:
  webhooks:
    - https://semabot.datamade.us/travis/
```







