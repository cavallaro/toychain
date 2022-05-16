import logging
import threading
import time


logger = logging.getLogger('toychain.minerr')


class Miner(threading.Thread):
    def __init__(self, blockchain, miner_address, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "miner"  # shows as threadName in logging

        self.blockchain = blockchain
        self.miner_address = miner_address

        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        # TODO: concurrent access to data such as blocks needs proper locking
        while not self._stop.is_set():
            logger.info("Attempt to mine a new block, if there are any transactions in the pool...")
            block = self.blockchain.mine(miner_address=self.miner_address)
            if block:
                logger.info("Mined new block: %s", block.serialize())

            time.sleep(10)
