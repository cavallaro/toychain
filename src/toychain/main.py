import base64
import hashlib
import json
import logging
import time

# others
import ecdsa
import requests


logger = logging.getLogger('toychain')


class BlockchainError(Exception):
    pass


class InputIsUnavailableError(BlockchainError):
    pass


class TransactionIsNotInPoolError(BlockchainError):
    pass


class TransactionPool:
    def __init__(self):
        self._transactions = {}

    def add_transaction(self, transaction, fee):
        self._transactions[transaction.calculate_hash()] = {"transaction": transaction, "fee": fee}

    def get_transactions(self, count):
        # this is rather inefficient, i am well aware.
        count = min(count, len(self._transactions))
        transaction_list = [
            {"transaction_id": transaction_id, "fee": v['fee'], "transaction": v['transaction']}
            for transaction_id, v in self._transactions.items()
        ]

        return sorted(transaction_list, key=lambda transaction: transaction["fee"], reverse=True)[:count]

    def delete_transaction(self, transaction_id):
        try:
            del self._transactions[transaction_id]
        except KeyError:
            raise TransactionIsNotInPoolError()

    def flush(self):
        self._transactions = {}


class Block:
    def __init__(self, prev, nonce=0, timestamp=None, transactions=None):
        self.prev = prev
        self.nonce = nonce
        self.timestamp = timestamp or time.time_ns()
        self.transactions = transactions or []

    @property
    def is_genesis(self):
        return self.prev == "0" * 64

    @property
    def hashable_contents(self):
        return {
            'timestamp': self.timestamp,
            'prev': self.prev,
            'nonce': self.nonce,
            'transactions': [t.hashable_contents for t in self.transactions]
        }

    def serialize(self):
        return {
            'timestamp': self.timestamp,
            'prev': self.prev,
            'nonce': self.nonce,
            'hash': self.calculate_hash(),
            'transactions': [t.serialize() for t in self.transactions]
        }

    @classmethod
    def unserialize(cls, serialized_block):
        return Block(
            prev=serialized_block["prev"],
            nonce=serialized_block["nonce"],
            timestamp=serialized_block["timestamp"],
            transactions=[
                Transaction.unserialize(transaction) for transaction in serialized_block['transactions']
            ]
        )

    def calculate_hash(self):
        return hashlib.sha256(json.dumps(self.hashable_contents, sort_keys=True).encode('utf-8')).hexdigest()


class Transaction:
    def __init__(self, inputs, outputs, timestamp=None):
        self.inputs = inputs  # list of {"transaction_id": str, "vout": int} Dicts.
        self.outputs = outputs  # list of {"address": str, "amount": int} Dicts.
        self.timestamp = timestamp or time.time_ns()

        self.signature = None
        self.public_key = None

    @property
    def is_coinbase(self):
        return len(self.inputs) == 0

    @property
    def hashable_contents(self):
        return {
            'inputs': self.inputs,
            'outputs': self.outputs,
            'timestamp': self.timestamp
        }

    def serialize(self):
        return self.hashable_contents | {
            'signature': self.signature.decode('utf-8') if self.signature else None,
            'public_key': self.public_key.decode('utf-8') if self.public_key else None,
            'hash': self.calculate_hash()
        }

    @classmethod
    def unserialize(cls, serialized_transaction):
        transaction = Transaction(
            inputs=serialized_transaction["inputs"],
            outputs=serialized_transaction["outputs"],
            timestamp=serialized_transaction["timestamp"],
        )

        # unsigned transactions won't have these
        signature = serialized_transaction.get('signature')
        if signature:
            transaction.signature = signature.encode('utf-8')

        public_key = serialized_transaction.get('public_key')
        if public_key:
            transaction.public_key = public_key.encode('utf-8')

        return transaction

    def calculate_hash(self):
        return hashlib.sha256(json.dumps(self.hashable_contents, sort_keys=True).encode('utf-8')).hexdigest()

    def sign(self, key: ecdsa.SigningKey):
        # not a fan of these capabilities on what are otherwise plain data structs, however this is rather convenient,
        # at least for now.
        signature = key.sign(json.dumps(self.hashable_contents, sort_keys=True).encode('utf-8'), hashfunc=hashlib.sha256)
        self.signature = base64.b64encode(signature)
        self.public_key = base64.b64encode(key.verifying_key.to_string())


class Blockchain:
    def __init__(self, transactions_per_block=2, confirmations=2, base_difficulty=20, base_block_reward=50):
        self.transactions_per_block = transactions_per_block
        self.confirmations = confirmations
        self.base_difficulty = base_difficulty
        self.base_block_reward = base_block_reward

        self.transaction_pool = TransactionPool()

        self.blocks = []
        self.fork = []
        self.orphans = []

        self.peers = set()

    def serialize(self):
        # TODO: what about the transaction pool? should we dump the transactions?
        return {
            "blocks": [block.serialize() for block in self.blocks],
            "fork": [block.serialize() for block in self.fork],
            "orphans": [block.serialize() for block in self.orphans]
        }

    @classmethod
    def unserialize(cls, serialized_blockchain):
        blockchain = cls()
        blockchain.blocks = [Block.unserialize(sb) for sb in serialized_blockchain["blocks"]]
        blockchain.fork = [Block.unserialize(sb) for sb in serialized_blockchain["fork"]]
        blockchain.orphans = [Block.unserialize(sb) for sb in serialized_blockchain["orphans"]]

        return blockchain

    def calculate_balance(self, address):
        outputs = {}  # {(transaction_id, vout): amount}

        for block_number, block in enumerate(self.blocks):
            for transaction in block.transactions:
                transaction_id = transaction.calculate_hash()

                # prune spent
                for input in transaction.inputs:
                    amount = outputs.pop((input['transaction_id'], input['vout']), None)
                    if amount:
                        logger.info(
                            "%s:%s (%s units) spent on transaction_id: %s, block_number: %s",
                            input['transaction_id'], input['vout'], amount, transaction_id, block_number
                        )

                # collect unspent
                for vout, output in enumerate(transaction.outputs):
                    if output['address'] == address:
                        outputs[(transaction_id, vout)] = output['amount']
                        logger.info(
                            "%s units received on transaction_id: %s, vout: %s, block_number: %s",
                            output['amount'], transaction_id, vout, block_number
                        )

        return sum(outputs.values())

    @property
    def tip(self):
        return self.blocks[-1]

    @property
    def height(self):
        return len(self.blocks) - 1

    @property
    def difficulty(self):
        return self.base_difficulty + int(self.height / 2)

    @property
    def block_reward(self):
        # halve every 5 blocks.
        return int(self.base_block_reward/(int(self.height / 5)+1))

    def add_transaction_to_pool(self, transaction):
        transaction_fee = self._verify_transaction(transaction)
        self.transaction_pool.add_transaction(transaction=transaction, fee=transaction_fee)

    def get_next_block(self, previous_hash):
        for block_number, block in enumerate(self.blocks):
            if block.calculate_hash() == previous_hash:
                if len(self.blocks) == block_number + 1:  # this is the last block!
                    return None
                else:
                    return self.blocks[block_number + 1]

        raise Exception("Block with hash: %s not found")

    def get_block_height(self, hash):
        for block_height, block in enumerate(self.blocks):
            if block.calculate_hash() == hash:
                return block_height

    def get_block(self, hash):
        for block in self.blocks:
            if block.calculate_hash() == hash:
                return block

    # def get_block(self, hash, limit=None):
    #     for i in range(limit or self.height + 1):
    #         if self.height < i:
    #             # can't go before the Genesis block
    #             return None, None
    #
    #         block_height = self.height - i
    #         block = self.blocks[block_height]
    #         if block.calculate_hash() == hash:
    #             return block, block_height
    #
    #     return None, None

    def receive_block(self, block):
        # This blockchain can handle currently only one fork from the main chain at any given time.
        # TODO: support a tree of forks.
        # The way this algorithm would work is:
        # A---B---C---D                     #1
        #     |
        #     +---C'--D'                    #2
        #     |
        #     +---C"--D"--E"--F"--G"--H"    #3
        #             |
        #             +---E^--F^            #4
        # Calculate the length of each chain (easiest way would be to count backwards from the leaves):
        # A  B  C  D  = 4                   #1
        # A  B  C' D' = 4                   #2
        # A  B  C" D" E" F" G" H" = 8       #3
        # A  B  C" D" E^ F^ = 6             #4
        # Select the largest one: #4.
        # Discard all other chains that are shorter than 8 - self.confirmations. Assuming self.confirmations = 2, chains
        #   #1 and #2 are discarded, this means to remove all the blocks in these chains that are not in any other chain
        #   still considered a valid fork, so C, D, C' and D' are thrown away.
        # If any of the discarded blocks was the tip of our main chain:
        #   - select the tip of the largest chain as the tip of our new main chain.
        #   - return to the pool the transactions in the discarded blocks that were part of our main chain.

        block_hash = block.calculate_hash()
        block_height = self.get_block_height(block_hash)
        if block_height is not None:
            logger.info("Block with hash: %s exists in our chain at height: %s", block_hash, block_height)
            return

        self._receive_block(block)
        self._reconverge()

    def _receive_block(self, block):
        if self.height < 0:
            if not block.is_genesis:
                raise Exception("First block in the chain must be a Genesis block")

            self.blocks.append(block)
            logger.info("Genesis block has been added")
            self.publish_block(block)

        elif block.prev == self.tip.calculate_hash():
            self.blocks.append(block)
            logger.info("New block has been added, new height: %s", self.height)
            # TODO: prune the transactions in this block from transaction pool
            self.publish_block(block)

        else:
            logger.warning("Block's previous hash is not our tip")
            # see if the previous block is within the last `self.confirmations` blocks in the main chain
            fork_block_height = self.get_block_height(hash=block.prev)

            if fork_block_height is not None:
                # previous block exists in the main chain
                block_height = fork_block_height + 1

                if self.height - block_height < self.confirmations:
                    self.fork = [block]
                    logger.warning("Fork at block %s", fork_block_height)
                    # TODO: should we propagate this block?

                else:
                    logger.warning(
                        "Fork at block %s, but the next block has %s confirmations",
                        fork_block_height, self.height - block_height
                    )

            elif self.fork and block.prev == self.fork[-1].calculate_hash():
                self.fork.append(block)
                logger.warning("Block points to the tip of a fork, fork is now %s blocks long", len(self.fork))

            else:
                # as we won't be tracking multiple forks in this basic implementation, we assume this is an orphan block
                self.orphans.append(block)
                logger.warning("Orphan block received: %s", block.serialize())

    def _reconverge(self):
        if self.fork:
            # Get the common block between both chains
            fork_block_height = self.get_block_height(hash=self.fork[0].prev)
            secondary_chain_height = fork_block_height + len(self.fork)

            if self.height - secondary_chain_height >= self.confirmations:
                logger.warning("Main chain is %s blocks longer than the fork chain, clearing fork", self.confirmations)
                self.fork.clear()

            elif secondary_chain_height - self.height >= self.confirmations:
                logger.warning(
                    "Fork chain is %s blocks longer than main chain! reconverging from height: %s",
                    self.confirmations, fork_block_height
                )

                # return transactions in the dead branch to the transaction pool
                blocks_to_remove = self.blocks[fork_block_height+1:]

                # reconverge
                self.blocks[fork_block_height+1:] = self.fork[:]

                for block in blocks_to_remove:
                    for transaction in block.transactions:
                        if not transaction.is_coinbase:
                            try:
                                self.add_transaction_to_pool(transaction)
                            except InputIsUnavailableError as e:
                                # one or more inputs may have been spent
                                logger.warning(
                                    "Can't return transaction_id: %s to transaction pool: %s",
                                    transaction.calculate_hash(), str(e)
                                )

                # remove transactions in the new branch from the transaction pool
                for block in self.fork:
                    for transaction in block.transactions:
                        if not transaction.is_coinbase:
                            try:
                                self.transaction_pool.delete_transaction(transaction_id=transaction.calculate_hash())
                            except TransactionIsNotInPoolError:
                                logger.warning(
                                    "transaction_id: %s not in transaction pool", transaction.calculate_hash()
                                )

                self.fork.clear()

    def get_transaction(self, transaction_id, block_height=None):
        # linear lookup of transaction `transaction_id`,  from `block_height`, backwards. Assume chain tip if no
        # `block_height` is passed.
        if block_height is None:
            block_height = self.height

        if block_height < 0:
            return None

        for transaction in self.blocks[block_height].transactions:
            if transaction.calculate_hash() == transaction_id:
                logger.info("transaction_id: %s found in block_height: %s", transaction_id, block_height)
                return transaction

        return self.get_transaction(transaction_id, block_height=block_height - 1)

    def _is_output_available(self, output, block_height=None):
        # scan every transaction in every block to make sure that the output hasn't been spent in a previous
        #   transaction. this operation is suboptimal, to be very kind to myself.
        # this is how bitcoin nodes track the UTXO set:
        #   https://en.bitcoin.it/wiki/Bitcoin_Core_0.11_(ch_2):_Data_Storage#The_UTXO_set_.28chainstate_leveldb.29
        if block_height is None:
            block_height = self.height

        if block_height == 0:
            return True

        for transaction in self.blocks[block_height].transactions:
            for input in transaction.inputs:
                if input['transaction_id'] == output['transaction_id'] and input['vout'] == output['vout']:
                    logger.warning(
                        "Output was spent in transaction_id: %s, vout: %s",
                        input['transaction_id'], input['vout']
                    )
                    return False

        return self._is_output_available(output, block_height - 1)

    def _can_redeem(self, transaction, source_transaction, vout):
        output = source_transaction.outputs[vout]
        public_key_bytes = base64.b64decode(transaction.public_key)
        public_key_hash = hashlib.sha256(public_key_bytes).hexdigest()

        # in a cheap attempt to resemble "OP_EQUALVERIFY"
        if output['address'] != public_key_hash:
            raise Exception(
                "Public Key hash: %s does not match output's address: %s" % (public_key_hash, output['address'])
            )

        # same, but with "OP_CHECKSIG"
        public_key = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)

        # TODO: wrap this exception in an exception of our own.
        public_key.verify(
            signature=base64.b64decode(transaction.signature),
            data=json.dumps(transaction.hashable_contents, sort_keys=True).encode('utf-8'),
            hashfunc=hashlib.sha256
        )

    def _verify_transaction(self, transaction):
        utxos = []

        # check that the inputs haven't been spent.
        for input in transaction.inputs:
            if not self._is_output_available(input):
                raise InputIsUnavailableError("Can't verify transaction because input: %s is unavailable" % input)

            # prove that the transaction signer is entitled to redeeming that output.
            source_transaction = self.get_transaction(input['transaction_id'])
            if not source_transaction:  # TODO: write testcase
                raise Exception("transaction_id: %s could not be found" % input['transaction_id'])

            self._can_redeem(transaction, source_transaction, vout=input['vout'])

            vout = input['vout']
            output = source_transaction.outputs[vout]
            utxos.append(output)

        # calculate fee
        if len(transaction.inputs):  # TODO: coinbase transactions shouldn't go through here ever.
            # it's not a coinbase transaction
            fee = sum(i['amount'] for i in utxos) - sum(i['amount'] for i in transaction.outputs)
            if fee < 0:
                raise Exception("Output amount is higher than input amount")

            logger.info("transaction_id: %s pays %s units in miner fees", transaction.calculate_hash(), fee)
            return fee

        return 0

    def mine(self, miner_address):
        miner_fees = 0

        # handle Genesis block case
        transaction_entries = self.transaction_pool.get_transactions(count=2)
        if len(transaction_entries) == 0 and self.height >= 0:
            # not an error per se, as the transaction pool can be empty.
            return None

        # create an empty block, point at the previous block (except in Genesis block case)
        block = Block(
            prev=self.tip.calculate_hash() if self.height >= 0 else "0" * 64,
            timestamp=time.time_ns()
        )

        for transaction_entry in transaction_entries:
            block.transactions.append(transaction_entry['transaction'])
            miner_fees += transaction_entry['fee']

        # create the transaction to pay the block reward + mining fees
        coinbase_transaction = Transaction(
            inputs=[],
            outputs=[{'address': miner_address, 'amount': self.block_reward + miner_fees}]
        )

        # coinbase transaction has no signature.
        block.transactions.append(coinbase_transaction)

        # mine the block.
        mask = int('f'*64, base=16) >> self.difficulty

        hash = block.calculate_hash()

        logger.info("Attempt to mine a new block with %s transactions", len(transaction_entries))
        while not int(hash, base=16) <= mask:
            if self.blocks and self.tip.prev == block.prev:
                logger.info("Someone else has already mined the next block, so we'll abort this attempt.")
                return

            block.nonce += 1
            hash = block.calculate_hash()

        logger.info("A new block with hash: %s has been mined, tentative new height: %s", hash, self.height + 1)
        self.receive_block(block)

        # clear mined transactions from the transaction pool
        for transaction in transaction_entries:
            self.transaction_pool.delete_transaction(transaction_id=transaction['transaction_id'])

        return block

    def publish_block(self, block):
        successful = 0
        for peer in self.peers:
            # this call is blocking, we eventually want to make it so that it's non-blocking.
            logger.info("Attempt to send block to peer: %s", peer)
            requests.post("http://%s:5000/blocks" % peer, json=json.dumps(block.serialize()))
            successful += 1

        logger.info("Block sent to %s peer(s)", successful)

    def initialize(self, miner_address):
        self.blocks = []
        self.transaction_pool.flush()
        return self.mine(miner_address=miner_address)


class Client:
    def __init__(self, keys: list[ecdsa.SigningKey] = None):
        self.keys = {}
        if keys:
            self.load_keys(keys)

    def load_keys(self, keys: list[ecdsa.SigningKey]):
        new_keys = {hashlib.sha256(key.verifying_key.to_string()).hexdigest(): key for key in keys}
        logger.info("Loaded Wallets: %s", ", ".join(new_keys.keys()))

        self.keys.update(new_keys)
        return

    def sign(self, transaction: Transaction, address):
        transaction.sign(key=self.keys[address])


if __name__ == '__main__':
    client = Client()
    print("A minimal CLI coming soon.")
