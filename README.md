# toychain
A toy PoW blockchain, still and by far a WIP.

#### Set up virtualenv
```
mkvirtualenv toychain
pip install -r requirements.txt
```

#### Run tests
```
cd tests
pytest -vvv
```

or for more verbose output -- useful to see the state of the blockchain and test wallets balances after each test, as well as some logging:
```
pytest -vvv --capture=no --log-cli-level=INFO
```