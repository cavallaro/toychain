import hashlib
import json
import logging
import time

# others
import ecdsa


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('toychain')


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
        del self._transactions[transaction_id]

    def flush(self):
        self._transactions = {}


class Block:
    def __init__(self, prev, nonce=0, timestamp=None, transactions=None):
        self.prev = prev
        self.nonce = nonce
        self.timestamp = timestamp or time.time_ns()
        self.transactions = transactions or []

    @property
    def hashable_contents(self):
        return {
            'timestamp': self.timestamp,
            'prev': self.prev,
            'nonce': self.nonce,
            'transactions': [t.serialize() for t in self.transactions]
        }

    def serialize(self):
        return {**self.hashable_contents, **{'hash': self.calculate_hash()}}

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
    def hashable_contents(self):
        return {
            'inputs': self.inputs,
            'outputs': self.outputs,
            'timestamp': self.timestamp
        }

    def serialize(self):
        return {**self.hashable_contents, **{'hash': self.calculate_hash()}}

    def calculate_hash(self):
        return hashlib.sha256(json.dumps(self.hashable_contents, sort_keys=True).encode('utf-8')).hexdigest()

    def sign(self, key: ecdsa.SigningKey):
        # not a fan of these capabilities on what are otherwise plain data structs, however this is rather convenient,
        # at least for now.
        signature = key.sign(json.dumps(self.hashable_contents, sort_keys=True).encode('utf-8'), hashfunc=hashlib.sha256)
        self.signature = signature
        self.public_key = key.verifying_key.to_string()


class Blockchain:
    def __init__(self, transactions_per_block=2):
        self.transactions_per_block = transactions_per_block
        self.transaction_pool = TransactionPool()
        self.blocks = []

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
    def height(self):
        return len(self.blocks) - 1

    @property
    def difficulty(self):
        return 2 + int(self.height / 2)

    @property
    def block_reward(self):
        # start with 50 units, halve every 5 blocks.
        return int(50/(int(self.height / 5)+1))

    def add_transaction_to_pool(self, transaction):
        transaction_fee = self.verify_transaction(transaction)
        self.transaction_pool.add_transaction(transaction=transaction, fee=transaction_fee)

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
                    print(f"output was already spent in transaction_id: {input['transaction_id']}, vout: {input['vout']}")
                    return False

        return self._is_output_available(output, block_height - 1)

    def can_redeem(self, transaction, source_transaction, vout):
        output = source_transaction.outputs[vout]
        public_key_hash = hashlib.sha256(transaction.public_key).hexdigest()

        # in a cheap attempt to resemble "OP_EQUALVERIFY"
        if output['address'] != public_key_hash:
            raise Exception(f"Public Key hash: {public_key_hash} does not match output's address: {output['address']}")

        # same, but with "OP_CHECKSIG"
        public_key = ecdsa.VerifyingKey.from_string(transaction.public_key, curve=ecdsa.SECP256k1)

        # TODO: wrap this exception in an exception of our own.
        public_key.verify(
            signature=transaction.signature,
            data=json.dumps(transaction.hashable_contents, sort_keys=True).encode('utf-8'),
            hashfunc=hashlib.sha256
        )

    def verify_transaction(self, transaction):
        utxos = []

        # check that the inputs haven't been spent.
        for input in transaction.inputs:
            if not self._is_output_available(input):
                raise Exception(f"Can't verify transaction because input: {input} is unavailable")

            # prove that the transaction signer is entitled to redeeming that output.
            source_transaction = self.get_transaction(input['transaction_id'])
            self.can_redeem(transaction, source_transaction, vout=input['vout'])

            vout = input['vout']
            output = source_transaction.outputs[vout]
            utxos.append(output)

        # calculate fee
        if len(transaction.inputs):  # TODO: coinbase transactions shouldn't go through here ever.
            # it's not a coinbase transaction
            fee = sum(i['amount'] for i in utxos) - sum(i['amount'] for i in transaction.outputs)
            if fee < 0:
                raise Exception("Output amount is higher than input amount")

            logger.info("fee for transaction_id: %s is: %s", transaction.calculate_hash(), fee)
            return fee

        return 0

    def mine(self, miner_key: ecdsa.SigningKey):
        miner_fees = 0

        # handle Genesis block case
        transaction_entries = self.transaction_pool.get_transactions(count=2)
        if len(transaction_entries) == 0 and self.height >= 0:
            # not an error per se, as the transaction pool can be empty.
            logger.info("Can't mine an empty block unless this is the Genesis block.")
            return None

        # create an empty block, point at the previous block (except in Genesis block case)
        block = Block(
            prev=self.blocks[self.height].calculate_hash() if self.height >= 0 else "0" * 64,
            timestamp=time.time_ns()
        )

        for transaction_entry in transaction_entries:
            block.transactions.append(transaction_entry['transaction'])
            miner_fees += transaction_entry['fee']

        # create the transaction to pay the block reward + mining fees
        miner_address = hashlib.sha256(miner_key.verifying_key.to_string()).hexdigest()
        coinbase_transaction = Transaction(
            inputs=[],
            outputs=[{'address': miner_address, 'amount': self.block_reward + miner_fees}]
        )

        coinbase_transaction.sign(key=miner_key)
        block.transactions.append(coinbase_transaction)

        # mine the block.
        hash = block.calculate_hash()
        while not hash.startswith('0' * self.difficulty):
            block.nonce += 1
            hash = block.calculate_hash()

        self.blocks.append(block)

        # clear mined transactions from the transaction pool
        for transaction in transaction_entries:
            self.transaction_pool.delete_transaction(transaction_id=transaction['transaction_id'])

        return block

    def initialize(self, miner_key):
        self.blocks = []
        self.transaction_pool.flush()
        self.mine(miner_key=miner_key)


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
