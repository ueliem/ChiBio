from multiprocessing import Process, Queue
import multiprocessing
import sched
import smbus2 as smbus

class Reactor(Process):
    def __init__(self, reactor_num, com_q, log_q):
        self.scheduler = sched.scheduler()
        self.detected = False
        self.reactor_num = reactor_num
        self.log_q = log_q
        self.com_q = com_q
        self.pump_rate = [0.0] * 4
    def run(self):
        time.sleep(2.0)
        self.log("Reactor controller " + str(self.reactor_num) + " started.")
        while not self.running.is_set():
            pass
    def log(self, msg):
        self.log_q.put(LogPacket(msg))
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

