import time
from multiprocessing import Process
from multiprocessing.managers import SyncManager
import simplejson
import csv
from collections import deque

import hal
from hal import HAL, Watchdog

REACTOR_COUNT = 8

class Commander(Process):
    def __init__(self, in_q, log_q, hwlock, running):
        (Process.__init__(self))
        pass
    def run(self):
        time.sleep(2.0)
        self.initialise_all()
        self.log("started")
        while not self.running.is_set():
            self.set_output_on('M0', 'LEDA', 1)
            time.sleep(1)
            self.set_output_on('M0', 'LEDA', 0)
            self.log("testing")
            time.sleep(3)
    def log(self, msg):
        self.log_q.put(LogPacket(msg))

def main():
    manager = SyncManager(address=('', 7777), authkey='abc')
    manager.start()
    q1 = manager.Queue()
    q2 = manager.Queue()
    #hardware_lock = multiprocessing.Lock()
    #manager.register('Lock', lambda _: hardware_lock, AcquirerProxy)
    running = manager.Event()
    hwlock = manager.RLock()
    q2.put(hal.LogPacket("Created manager."))
    wd = Watchdog(q2, hwlock, running)
    wd.start()
    #time.sleep(2.0)
    h = HAL(q1, q2, hwlock, running)
    #h.initialiseAll()
    h.start()
    #print("init")
    while not running.is_set():
        print(q2.get())


if __name__ == '__main__': main()

