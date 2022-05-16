import base64
import json
import logging
import os

# others
import ecdsa
import flask

# own
import toychain.main
import toychain.miner


def create_app():
    logging.basicConfig(
        format="%(thread)s %(threadName)12.12s %(pathname)-32.32s:%(lineno)4s %(levelname)-8s %(asctime)s | %(message)s",
        level=logging.DEBUG
    )

    app = flask.Flask(__name__)
    app.config['TRAP_BAD_REQUEST_ERRORS'] = True

    blockchain = None

    # load blockchain (if available)
    try:
        with open("blockchain.json") as f:
            serialized_blockchain = json.load(f)
        app.logger.info("A blockchain.json file exists, loading...")
        blockchain = toychain.main.Blockchain.unserialize(serialized_blockchain)
    except FileNotFoundError:
        app.logger.info("No blockchain.json file exists.")
        blockchain = toychain.main.Blockchain()

    blockchain.peers = set(os.getenv("TOYCHAIN_PEERS", "").split())
    # blockchain.initialize(miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d")

    @app.route('/transactions/<string:transaction_id>', methods=['GET'])
    def get_transaction(transaction_id):
        transaction = blockchain.get_transaction(transaction_id)
        if transaction:
            return flask.jsonify(transaction.serialize())
        else:
            return "", 404

    @app.route('/balances/<string:address>', methods=['GET'])
    def get_balance(address):
        balance = blockchain.calculate_balance(address)
        return flask.jsonify({"balance": balance or 0})

    @app.route('/mine', methods=['POST'])
    def mine():
        address = flask.request.json['address']
        app.logger.info("Block rewards and fees will be paid to: %s", address)
        block = blockchain.mine(miner_address=address)
        return block.serialize()

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
            app.logger.info("Get blocks call, no peer tip provided. Genesis block: %s", json.dumps(block.serialize()))
            return flask.jsonify({"block": block.serialize()})

        block = blockchain.get_next_block(previous_hash=peer_tip)
        if block:
            app.logger.info("Get blocks call, peer tip: %s, next block: %s", peer_tip, json.dumps(block.serialize()))
            return flask.jsonify({"block": block.serialize()})
        else:
            return "", 404

    @app.route('/blocks', methods=['POST'])
    def receive_block():
        block = toychain.main.Block.unserialize(json.loads(flask.request.json))
        app.logger.info("New block received, with hash: %s, prev: %s", block.calculate_hash(), block.prev)
        blockchain.receive_block(block)
        return "", 202

    miner = toychain.miner.Miner(
        blockchain=blockchain,
        miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'
    )
    miner.start()

    return app
