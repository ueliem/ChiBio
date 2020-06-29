from multiprocessing import Process, Queue
import multiprocessing
import sched
import smbus2 as smbus

class Reactor(Process):
    def __init__(self, reactorNum, logQ):
        self.scheduler = sched.scheduler()
        self.detected = False
        self.reactorNum = reactorNum
        self.logQ = logQ
        self.pumpRate = [0.0] * 4
    def logError(self):
        pass
    def scan(self):
        pass
    def startPump(self, pump):
        pass
    def stopPump(self, pump):
        pass
    def setPumpRate(self, rate):
        if 0.00 <= value <= 1.00 and round(rate, 2) == rate:
            self.pumpRate = rate
        else:
            self.logError()
    def measureTemp(self):
        pass

