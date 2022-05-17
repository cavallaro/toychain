# toychain
A toy PoW blockchain, still and by far a WIP.

### Dev environment, tests, etc.

#### Set up virtualenv
```
mkvirtualenv toychain
pip install -r requirements-dev.txt
```

#### Run unit tests
```
cd tests
PYTHONPATH=$PYTHONPATH:../src/toychain coverage run --include ../src/toychain/main.py -m pytest -v
```

Or for more verbose output -- useful to see the state of the blockchain and test wallets balances after each test, as well as some logging:
```
PYTHONPATH=$PYTHONPATH:../src/toychain coverage run --include ../src/toychain/main.py -m pytest -v --capture=no --log-cli-level=INFO
```

Get coverage report:
```
coverage report -m
```

### Interacting with the blockchain

See API.md for reference

#### Start a pair of nodes
```
docker-compose up --build --remove-orphans
```

They will listen at `localhost:8443` and `localhost:8444`.

You can also stop/start individual nodes by running:
```
docker-compose stop/start <node-name>
```

Environment variables (set in `docker-compose.yml`):
- `TOYCHAIN_BLOCKCHAIN_FILE`: Restore the blockchain from this file, `blockchain.json` currently contains the Genesis block.
- `TOYCHAIN_PEERS`: The list of peers known to this node, as there is currently no peer discovery.
- `TOYCHAIN_SYNCHRONIZE`: Synchronize the blockchain state at startup from the first peer in the list
