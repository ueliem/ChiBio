import logging
import logging.config
import logging.handlers
from multiprocessing import Process, Queue
from systemd.journal import JournalHandler

logger = logging.getLogger("ChiBio")
journalHandler = JournaldLogHandler()

journalHandler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))

logger.addHandler(journalHandler)

class Logger(Process):
    def __init__(self, logQ):
        super(Logger, self).__init__()
        self.running = False
        self.logQ = logQ
    def run(self):
        self.running = True
        while self.running:
            record = self.logQ.get()
            continue

