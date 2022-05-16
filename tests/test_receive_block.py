# own
from main import Blockchain, Transaction


def test_block_is_genesis_block(client):
    blockchain_a = Blockchain(base_difficulty=2)
    genesis_block = blockchain_a.initialize(miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')

    blockchain_b = Blockchain(base_difficulty=2)
    blockchain_b.receive_block(genesis_block)
    assert blockchain_b.height == 0
    assert blockchain_b.blocks[0].calculate_hash() == genesis_block.calculate_hash()


def test_block_is_next_in_main_chain(client):
    blockchain_a = Blockchain(base_difficulty=2)
    genesis_block = blockchain_a.initialize(miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')

    blockchain_b = Blockchain(base_difficulty=2)
    blockchain_b.receive_block(genesis_block)

    blockchain_a_block_00 = blockchain_a.blocks[0]
    blockchain_a_block_00_coinbase_transaction_hash = blockchain_a_block_00.transactions[0].calculate_hash()

    # Fee: 2
    transaction = Transaction(
        inputs  = [
            {'transaction_id': blockchain_a_block_00_coinbase_transaction_hash, 'vout': 0}
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 28}  #  change
        ]
    )
    client.sign(transaction, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    blockchain_a.add_transaction_to_pool(transaction)
    blockchain_a_block_01 = blockchain_a.mine(
        miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d"
    )

    blockchain_b.receive_block(blockchain_a_block_01)
    assert blockchain_b.height == 1

    next_block = blockchain_b.get_next_block(previous_hash=blockchain_a_block_00.calculate_hash())
    assert next_block.calculate_hash() == blockchain_a_block_01.calculate_hash()
    assert len(blockchain_b.fork) == 0


def test_handle_secondary_chain(client):
    blockchain_a = Blockchain(base_difficulty=2)
    genesis_block = blockchain_a.initialize(miner_address='b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')

    blockchain_b = Blockchain(base_difficulty=2)
    blockchain_b.receive_block(genesis_block)

    # Genesis block successfully received by blockchain_b
    assert blockchain_b.height == 0
    assert blockchain_b.blocks[0].calculate_hash() == genesis_block.calculate_hash()

    blockchain_a_block_00 = blockchain_a.blocks[0]
    blockchain_a_block_00_coinbase_transaction_hash = blockchain_a_block_00.transactions[0].calculate_hash()

    ##
    # mine a new block in blockchain_a (fee: 2)
    transaction_00 = Transaction(
        inputs  = [
            {'transaction_id': blockchain_a_block_00_coinbase_transaction_hash, 'vout': 0}  # 50 units
        ],
        outputs = [
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 20},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 28}  # change
        ]
    )
    client.sign(transaction_00, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    blockchain_a.add_transaction_to_pool(transaction_00)
    blockchain_a_block_01 = blockchain_a.mine(
        miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d"
    )

    assert blockchain_a.height == 1

    # check balances
    # blockchain_a_block_00.block_reward = 50
    # blockchain_a_block_01.transaction_00 = -50 (in) + 28 (change)
    # blockchain_a_block_01.block_reward = 50 + block_1.miner_fee = 2
    # total = 80
    assert blockchain_a.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 80

    # blockchain_a_block_01.transaction_00 = 20
    assert blockchain_a.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 20

    # mine the same transaction in blockchain_b, for the sake of briefness.
    # because of the timestamp, the block hash won't be the same
    blockchain_b.add_transaction_to_pool(transaction_00)
    blockchain_b_block_01 = blockchain_b.mine(
        miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d"
    )

    assert blockchain_b.height == 1
    assert len(blockchain_a.fork) == 0

    # the mined block is now at the tip of blockchain_b's main chain
    assert blockchain_b.tip.calculate_hash() == blockchain_b_block_01.calculate_hash()
    assert blockchain_b.tip.calculate_hash() == blockchain_b.get_next_block(
        previous_hash=genesis_block.calculate_hash()
    ).calculate_hash()

    # blockchain_b's tip block is not the same as blockchain_a's
    assert blockchain_b.tip.calculate_hash() != blockchain_a_block_01.calculate_hash()

    # blockchain_b will now receive blockchain_a's tip block, whose prev is the Genesis block
    blockchain_b.receive_block(blockchain_a_block_01)
    assert blockchain_b.height == 1

    # blockchain_b's tip must stay the same
    assert blockchain_b.tip.calculate_hash() == blockchain_b_block_01.calculate_hash()
    assert blockchain_b.tip.calculate_hash() == blockchain_b.get_next_block(
        previous_hash=genesis_block.calculate_hash()
    ).calculate_hash()

    # blockchain_b must track this fork
    assert len(blockchain_b.fork) == 1
    assert blockchain_b.fork[0].calculate_hash() == blockchain_a_block_01.calculate_hash()

    # share blockchain_b's new block with blockchain_a, to create a fork on blockchain_a
    blockchain_a.receive_block(blockchain_b_block_01)

    assert blockchain_a.height == 1
    assert blockchain_a.tip.calculate_hash() == blockchain_a_block_01.calculate_hash()

    assert len(blockchain_a.fork) == 1

    ##
    # mine a new block in blockchain_a (fee: 8)
    transaction_01 = Transaction(
        inputs=[
            {'transaction_id': transaction_00.calculate_hash(), 'vout': 1}  # 28 units
        ],
        outputs=[
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 10},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 10}  # change
        ]
    )
    client.sign(transaction_01, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    blockchain_a.add_transaction_to_pool(transaction_01)
    blockchain_a_block_02 = blockchain_a.mine(
        miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d"
    )

    assert blockchain_a.height == 2
    assert blockchain_a.tip.calculate_hash() == blockchain_a_block_02.calculate_hash()

    assert len(blockchain_a.fork) == 1

    # check balances
    # blockchain_a_block_00.block_reward = 50
    # blockchain_a_block_01.transaction_00 = -50 (in) + 28 (change)
    # blockchain_a_block_01.block_reward = 50 + block_1.miner_fee (2)
    # blockchain_a_block_02.transaction_01 = -28 (in) + 10 (change)
    # blockchain_a_block_02.block_reward = 50 + block_2.miner_fee (8)
    # total = 120
    assert blockchain_a.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 120

    # blockchain_a_block_01.transaction_00 = 20
    # blockchain_a_block_02.transaction_01 = 10
    # total = 30
    assert blockchain_a.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 30

    # blockchain_b will now receive blockchain_a's tip block once more
    blockchain_b.receive_block(blockchain_a_block_02)
    assert blockchain_b.height == 1

    # blockchain_b's tip must stay the same
    assert blockchain_b.tip.calculate_hash() == blockchain_b_block_01.calculate_hash()
    assert blockchain_b.tip.calculate_hash() == blockchain_b.get_next_block(
        previous_hash=genesis_block.calculate_hash()
    ).calculate_hash()

    # blockchain_b must chain this new block to the fork
    assert len(blockchain_b.fork) == 2
    assert blockchain_b.fork[0].calculate_hash() == blockchain_a_block_01.calculate_hash()
    assert blockchain_b.fork[1].calculate_hash() == blockchain_a_block_02.calculate_hash()

    # check balances
    # blockchain_b_block_00.block_reward = 50
    # blockchain_b_block_01.transaction_00 = -50 (in) + 28 (change)
    # blockchain_b_block_01.block_reward = 50 + block_1.miner_fee (2)
    # total = 80
    assert blockchain_b.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 80

    # blockchain_a_block_01.transaction_00 = 20
    # total = 20
    assert blockchain_b.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 20

    ##
    # mine a new block in blockchain_a (fee: 0)
    transaction_02 = Transaction(
        inputs=[
            {'transaction_id': transaction_01.calculate_hash(), 'vout': 1}  # 10 units
        ],
        outputs=[
            {'address': 'b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225', 'amount': 8},
            {'address': 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d', 'amount': 2}  # change
        ]
    )
    client.sign(transaction_02, 'b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d')
    blockchain_a.add_transaction_to_pool(transaction_02)
    blockchain_a_block_03 = blockchain_a.mine(
        miner_address="b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d"
    )

    assert blockchain_a.height == 3
    assert blockchain_a.tip.calculate_hash() == blockchain_a_block_03.calculate_hash()

    # main chain is now self.confirmation blocks longer than fork -- fork is discarded
    assert len(blockchain_a.fork) == 0

    # check balances
    # blockchain_a_block_00.block_reward = 50
    # blockchain_a_block_01.transaction_00 = -50 (in) + 28 (change)
    # blockchain_a_block_01.block_reward = 50 + block_1.miner_fee (2)
    # blockchain_a_block_02.transaction_01 = -28 (in) + 10 (change)
    # blockchain_a_block_02.block_reward = 50 + block_2.miner_fee (8)
    # blockchain_a_block_03.transaction_02 = -10 (in) + 2 (change)
    # blockchain_a_block_03.block_reward = 50 + block_2.miner_fee (0)
    # total = 162
    assert blockchain_a.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 162

    # blockchain_a_block_01.transaction_00 = 20
    # blockchain_a_block_02.transaction_01 = 10
    # blockchain_a_block_02.transaction_01 = 8
    # total = 38
    assert blockchain_a.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 38

    # blockchain_b will now receive blockchain_a's tip block once more
    blockchain_b.receive_block(blockchain_a_block_03)

    # here is where the chain should reconverge
    assert blockchain_b.height == 3
    assert blockchain_b.tip.calculate_hash() == blockchain_a_block_03.calculate_hash()

    blockchain_b_block_02 = blockchain_b.get_block(hash=blockchain_b.tip.prev)
    assert blockchain_b_block_02.calculate_hash() == blockchain_a_block_02.calculate_hash()
    assert blockchain_b.get_block_height(hash=blockchain_b_block_02.calculate_hash()) == 2

    blockchain_b_block_01 = blockchain_b.get_block(hash=blockchain_b_block_02.prev)
    assert blockchain_b_block_01.calculate_hash() == blockchain_a_block_01.calculate_hash()
    assert blockchain_b.get_block_height(hash=blockchain_b_block_01.calculate_hash()) == 1

    assert len(blockchain_b.fork) == 0

    # balances have to match those of blockchain_a:
    assert blockchain_b.calculate_balance('b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d') == 162
    assert blockchain_b.calculate_balance('b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225') == 38

    # TODO: assert about transactions going back to the transaction pool
