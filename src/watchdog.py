from multiprocessing import Process, Queue
# import Adafruit_BBIO.GPIO as GPIO

class Watchdog(Process):
    def __init__(self):
        self.name = "Watchdog"
        self.daemon = True
        self.running = False
        pass
    def tick(self):
        pass
    def run(self):
        self.running = True
        while self.running:
            continue

