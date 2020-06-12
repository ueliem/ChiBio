#!/usr/bin/env python3

import os
import random
import time
import math
from flask import Flask, render_template, jsonify
from multiprocessing import Process, Queue
import multiprocessing
import numpy as np
from datetime import datetime, date
# import Adafruit_GPIO.I2C as I2C
# import Adafruit_BBIO.GPIO as GPIO
import time
# import serial
# import simplejson
import copy
import csv
# import smbus2 as smbus
import sched
from collections import deque

from src.logger import Logger
from src.bbbdummy import BBBDummy
from src.reactor import Reactor

reactorCount = 8

logQueue = Queue(100)

class Manager(Process):
    def __init__(self, logQ):
        super(Manager, self).__init__()
        self.running = False
        self.logQ = logQ
        self.scheduler = sched.scheduler()
        self.reactors = deque([Reactor(i) for i in range(reactorCount)], maxlen=8)
    def scanForReactors(self):
        return [r.reactorNum for r in self.reactors if r.scan() != None]
    def scheduleCycle(self):
        for reactor in [r for r in self.reactors if r.detected]:
            self.scheduler.enter(0, ....)
            pass
    def runCycle(self):
        self.scheduler.run()

def main():
    logger = Logger(logQueue)
    manager = Manager(logQueue)
    logger.start()
    manager.start()

if __name__ == '__main__':
    main()

