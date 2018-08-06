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
