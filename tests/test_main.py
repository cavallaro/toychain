import pytest

import json

# others
import ecdsa

# own
from main import Blockchain, Client, Transaction


@pytest.fixture(scope="session")
def client():
    # TODO: set aliases to these keys rather than to hardcode the address.
    with open('tests/keys/user_01.key') as f:
        # b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d
        user_01_key = ecdsa.SigningKey.from_pem(f.read())
    with open('tests/keys/user_02.key') as f:
        # b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225
        user_02_key = ecdsa.SigningKey.from_pem(f.read())
    with open('tests/keys/user_03.key') as f:
        # 5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883
        user_03_key = ecdsa.SigningKey.from_pem(f.read())
    with open('tests/keys/user_04.key') as f:
        # d79a2f79fb96a0e687094bc896251dae046e571e02d80d2c940f1a18a539f650
        user_04_key = ecdsa.SigningKey.from_pem(f.read())

    return Client([user_01_key, user_02_key, user_03_key, user_04_key])


@pytest.fixture
def blockchain(client):
    _blockchain = Blockchain()
    _blockchain.initialize(miner_key=client.keys['b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'])

    yield _blockchain

    for block in reversed(_blockchain.blocks):
        print(json.dumps(block.serialize(), indent=4, sort_keys=True))

    for address in client.keys.keys():
        print("balance for wallet %s: %s" % (address, _blockchain.calculate_balance(address)))


@pytest.fixture
def first_transaction(blockchain, client):
    block_00 = blockchain.blocks[0]
    block_00_coinbase_transaction_hash = block_00.transactions[0].calculate_hash()

    # Fee: 2
    transaction = Transaction(
        inputs  = [
            {'transaction_id': block_00_coinbase_transaction_hash, 'vout': 0}
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 28}  #  change
        ]
    )
    client.sign(transaction, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    return transaction


def test_mine_ok(blockchain, first_transaction, client):
    blockchain.add_transaction_to_pool(first_transaction)
    block = blockchain.mine(miner_key=client.keys['b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'])

    assert blockchain.height == 1
    assert block.calculate_hash().startswith('0' * blockchain.difficulty)

    # our transaction + coinbase transaction
    assert len(block.transactions) == 2
    transaction = block.transactions[0]
    assert transaction.calculate_hash() == first_transaction.calculate_hash()


def test_mine_block_with_two_transactions_ok(blockchain, first_transaction, client):
    # Genesis block
    assert blockchain.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 50

    blockchain.add_transaction_to_pool(first_transaction)
    block = blockchain.mine(miner_key=client.keys['b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'])

    # block_00.block_reward = 50
    # block_01.transaction_00 = -50 (in) + 28 (change)
    # block_01.block_reward = 50 + block_1.miner_fee = 2
    # total = 80
    assert blockchain.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 80

    # block_01.transaction_00 = 20
    assert blockchain.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 20

    # mined successfully
    assert block is not None
    assert blockchain.height == 1

    previous_transaction = block.transactions[0]
    # the first output in this transaction is for user_02, 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225'

    # transaction_a
    transaction_a = Transaction(
        inputs=[
            {"transaction_id": previous_transaction.calculate_hash(), "vout": 0}
        ],
        outputs=[
            {'address': '5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883', 'amount': 5},  # user_03
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 14}  # change
        ]
    )

    client.sign(transaction_a, 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225')  # user_02
    blockchain.add_transaction_to_pool(transaction_a)

    # transaction_b, user_01 will spend some of the change (28 units) back from the previous transaction.
    transaction_b = Transaction(
        inputs=[
            {"transaction_id": previous_transaction.calculate_hash(), "vout": 1}
        ],
        outputs=[
            {'address': '5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883', 'amount': 5},  # user_03
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 22}  # change
        ]
    )

    client.sign(transaction_b, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')  # user_01
    blockchain.add_transaction_to_pool(transaction_b)

    # mine as user_04.
    # user_04 had no unspents available, now there should be one with 1 + 1 + block_reward.
    block = blockchain.mine(miner_key=client.keys['d79a2f79fb96a0e687094bc896251dae046e571e02d80d2c940f1a18a539f650'])

    # mined successfully
    assert block is not None
    assert blockchain.height == 2

    # our transaction + coinbase transaction
    assert len(block.transactions) == 3

    coinbase_transaction = block.transactions[-1]
    assert len(coinbase_transaction.outputs) == 1
    assert coinbase_transaction.outputs[0]['amount'] == blockchain.block_reward + 2

    # balance at block_01 = 80
    # block_02.transaction_b = -28 (in) + 22 (change)
    # total = 74.
    assert blockchain.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 74

    # balance at block_01 = 20
    # block_02.transaction_a = -20 (in) + 14 (change)
    # total = 14
    assert blockchain.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 14

    # balance at block_01 = 0
    # block_02.transaction_a = 5
    # block_02.transacstion_b = 5
    # total = 10
    assert blockchain.calculate_balance('5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883') == 10

    # balance at block_01 = 0
    # block_02.block_reward = 50 + block_2.miner_fee = 2
    # total = 52
    assert blockchain.calculate_balance('d79a2f79fb96a0e687094bc896251dae046e571e02d80d2c940f1a18a539f650') == 52


def test_input_has_already_been_spent(blockchain, first_transaction, client):
    blockchain.add_transaction_to_pool(first_transaction)
    blockchain.mine(miner_key=client.keys['b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'])

    # let's try to 'broadcast' the same transaction once more
    with pytest.raises(Exception) as e:
        blockchain.add_transaction_to_pool(first_transaction)

    assert "Can't verify transaction" in e.value.args[0]  # ugly, better to use custom exceptions and/or error keys.


def test_inputs_are_not_enough(blockchain):
    block_00 = blockchain.blocks[0]
    block_00_coinbase_transaction_hash = block_00.transactions[0].calculate_hash()

    transaction = Transaction(
        inputs  = [
            {'transaction_id': block_00_coinbase_transaction_hash, 'vout': 0}

        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 35}  # change
        ]
    )

    with pytest.raises(Exception):
        blockchain.add_transaction_to_pool(transaction)


def test_no_miners_fee_ok(blockchain, client):
    block_00 = blockchain.blocks[0]
    block_00_coinbase_transaction_hash = block_00.transactions[0].calculate_hash()

    transaction = Transaction(
        inputs  = [
            {"transaction_id": block_00_coinbase_transaction_hash, "vout": 0}
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 30}
        ]
    )

    client.sign(transaction, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    blockchain.add_transaction_to_pool(transaction)

    block = blockchain.mine(miner_key=client.keys['b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d'])

    # mined successfully
    assert block is not None

    # our transaction + coinbase transaction
    assert len(block.transactions) == 2

    coinbase_transaction = block.transactions[-1]
    assert len(coinbase_transaction.outputs) == 1
    assert coinbase_transaction.outputs[0]['amount'] == blockchain.block_reward


def test_cannot_redeem_unowned_utxo(blockchain, client):
    block_00 = blockchain.blocks[0]
    block_00_coinbase_transaction_hash = block_00.transactions[0].calculate_hash()

    transaction = Transaction(
        inputs  = [
            {"transaction_id": block_00_coinbase_transaction_hash, "vout": 0}
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},  # user_02
            {'address': '5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883', 'amount': 30}   # user_03
        ]
    )

    client.sign(transaction, '5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883')  # user_03

    with pytest.raises(Exception) as e:
        blockchain.add_transaction_to_pool(transaction)

    assert "Public Key hash" in e.value.args[0]  # ugly, better to use custom exceptions and/or error keys.


def test_cannot_verify_signature(blockchain, client):
    block_00 = blockchain.blocks[0]
    block_00_coinbase_transaction_hash = block_00.transactions[0].calculate_hash()

    transaction = Transaction(
        inputs  = [
            {"transaction_id": block_00_coinbase_transaction_hash, "vout": 0}
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},  # user_02
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 30}   # user_01
        ]
    )

    client.sign(transaction, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')    # user_01
    public_key_user_01 = transaction.public_key

    # use user_01's public key, but user_03's signature
    client.sign(transaction, '5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883')    # user_03
    transaction.public_key = public_key_user_01

    with pytest.raises(ecdsa.BadSignatureError) as e:
        blockchain.add_transaction_to_pool(transaction)
