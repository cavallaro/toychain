import base64
import contextlib
import json
import logging
import os
import time

# others
import ecdsa
import flask
import requests.exceptions

# own
import toychain.main
import toychain.miner


blockchain = None
miner = None


def create_app():
    global blockchain
    global miner

    logging.basicConfig(
        format="%(thread)s %(threadName)12.12s %(pathname)-32.32s:%(lineno)4s %(levelname)-8s %(asctime)s | %(message)s",
        level=logging.DEBUG
    )

    app = flask.Flask(__name__)
    app.config['TRAP_BAD_REQUEST_ERRORS'] = True

    blockchain_filename = os.getenv("TOYCHAIN_BLOCKCHAIN_FILE", "blockchain.json")

    def load_blockchain(blockchain_filename):
        global blockchain

        with open(blockchain_filename) as f:
            serialized_blockchain = json.load(f)

        blockchain = toychain.main.Blockchain.unserialize(serialized_blockchain)
        app.logger.info(
            "Load blockchain call, blocks: %s, fork blocks: %s, orphan blocks: %s",
            len(blockchain.blocks), len(blockchain.fork), len(blockchain.orphans)
        )

    @contextlib.contextmanager
    def restart_miner():
        global miner

        miner_was_alive = False
        if miner and miner.is_alive():
            miner.stop()
            miner.join()
            miner_was_alive = True

        yield

        if miner_was_alive:
            miner = toychain.miner.Miner(
                blockchain=blockchain,
                miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'
            )
            miner.start()

    ##
    # balances

    @app.route('/balances/<string:address>', methods=['GET'])
    def get_balance(address):
        return flask.jsonify({"balance": blockchain.calculate_balance(address) or 0})

    ##
    # blocks

    @app.route('/blocks/<block_hash>', methods=['GET'])
    def get_block(block_hash):
        block = blockchain.get_block(hash=block_hash)
        if not block:
            return "", 404

        return flask.jsonify(block.serialize())

    @app.route('/blocks/get-next', methods=['GET'])
    def get_next_block():
        """
        Query string:
            current-tip: hash of the client's current blockchain tip, optional. if no current-tip is provided, return
                the Genesis block.
        """
        if blockchain.height < 0:
            # blockchain is empty
            return "", 404

        peer_tip = flask.request.args.get('current-tip')
        if not peer_tip:
            # return Genesis block
            block = blockchain.blocks[0]
            app.logger.info("Get next block call, no peer tip provided. Genesis block: %s", json.dumps(block.serialize()))
            return flask.jsonify(block.serialize())

        try:
            block = blockchain.get_next_block(previous_hash=peer_tip)
        except toychain.main.BlockIsNotInMainChainError as e:
            app.logger.info(str(e))
            return "", 400

        if not block:
            app.logger.info("Get next block call, peer's tip: %s is same as ours", peer_tip)
            return "", 404

        app.logger.info("Get next block call, peer tip: %s, next block: %s", peer_tip, json.dumps(block.serialize()))
        return flask.jsonify(block.serialize())

    @app.route('/blocks', methods=['POST'])
    def receive_block():
        # note: we will try to retransmit the block to the sender, too, because the `publish_block` method is unaware
        #   of who sent it.
        block = toychain.main.Block.unserialize(json.loads(flask.request.json))
        app.logger.info("New block received, with hash: %s, prev: %s", block.calculate_hash(), block.prev)

        blockchain.receive_block(block)

        return "", 202

    ##
    # transactions

    @app.route('/transactions/<string:transaction_id>', methods=['GET'])
    def get_transaction(transaction_id):
        transaction = blockchain.get_transaction(transaction_id)
        if transaction:
            return flask.jsonify(transaction.serialize())
        else:
            return "", 404

    @app.route('/transactions', methods=['POST'])
    def receive_transaction():
        # note: same as on receive_block
        transaction = toychain.main.Transaction.unserialize(json.loads(flask.request.json))
        app.logger.info("New transaction received, with hash: %s", transaction.calculate_hash())

        blockchain.add_transaction_to_pool(transaction)

        return "", 202

    @app.route('/transactions/sign', methods=['POST'])
    def sign_transaction():
        """
        Body:
            {
                "transaction": serialized Transaction, must at least contain inputs, outputs, timestamp.
                "key": base64 encoded
            }
        Query string:
            add-to-transaction-pool
        """

        transaction = toychain.main.Transaction.unserialize(flask.request.json['transaction'])
        key = ecdsa.SigningKey.from_string(base64.b64decode(flask.request.json['key']), curve=ecdsa.SECP256k1)
        transaction.sign(key=key)

        if "add-to-transaction-pool" in flask.request.args:
            blockchain.add_transaction_to_pool(transaction)

        return transaction.serialize()

    ##
    # control, not a part of the public API

    @app.route('/mine', methods=['POST'])
    def mine():
        address = flask.request.json['address']
        app.logger.info("Block rewards and fees will be paid to: %s", address)
        block = blockchain.mine(miner_address=address)
        return block.serialize()

    @app.route('/persistence/save', methods=['POST'])
    def save():
        with open(flask.request.json.get('filename', blockchain_filename), "w") as f:
            app.logger.info(
                "Save blockchain call, blocks: %s, fork blocks: %s, orphan blocks: %s",
                len(blockchain.blocks), len(blockchain.fork), len(blockchain.orphans)
            )
            json.dump(blockchain.serialize(), f)

        return "", 200

    @app.route('/persistence/load', methods=['POST'])
    @restart_miner()
    def load():
        load_blockchain(flask.request.json.get('filename', blockchain_filename))
        return "", 200

    @app.route('/synchronize', methods=['POST'])
    @restart_miner()
    def synchronize():
        blockchain.synchronize()
        return "", 200

    ##

    # load blockchain (if available)
    try:
        load_blockchain(blockchain_filename)
    except FileNotFoundError:
        app.logger.info("No blockchain file exists.")
        blockchain = toychain.main.Blockchain()

    blockchain.peers = set(os.getenv("TOYCHAIN_PEERS", "").split())
    # blockchain.initialize(miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d")

    if int(os.getenv("TOYCHAIN_SYNCHRONIZE", 0)):
        app.logger.info("Attempt to synchronize before starting")
        for i in range(5):
            try:
                blockchain.synchronize()
                break
            except requests.exceptions.ConnectionError as e:
                app.logger.error(str(e))
                time.sleep(2)

        else:
            app.logger.info("Unable to synchronize blockchain")

    miner = toychain.miner.Miner(
        blockchain=blockchain,
        miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'
    )

    miner.start()

    return app
