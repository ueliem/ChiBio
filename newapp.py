import os
import random
import time
import math
from flask import Flask, render_template, jsonify
from threading import Thread, Lock
import threading
import numpy as np
from datetime import datetime, date
import Adafruit_GPIO.I2C as I2C
import Adafruit_BBIO.GPIO as GPIO
import time
import serial
import simplejson
import copy
import csv
import smbus2 as smbus

dataDir = "/home/ChiBioData/"

@application.route('/')

@application.route('/getSysdata/')

@application.route('/changeDevice/<M>',methods=['POST'])

@application.route('/scanDevices/<which>',methods=['POST'])

@application.route("/ClearTerminal/<M>",methods=['POST'])

@application.route("/SetFPMeasurement/<item>/<Excite>/<Base>/<Emit1>/<Emit2>/<Gain>",methods=['POST'])

@application.route("/SetOutputTarget/<item>/<M>/<value>",methods=['POST'])

@application.route("/SetOutputOn/<item>/<force>/<M>",methods=['POST'])

@application.route("/Direction/<item>/<M>",methods=['POST'])

@application.route("/GetSpectrum/<Gain>/<M>",methods=['POST'])

@application.route("/SetCustom/<Program>/<Status>",methods=['POST'])

@application.route("/SetLightActuation/<Excite>",methods=['POST'])

@application.route("/CharacteriseDevice/<M>/<Program>",methods=['POST'])     

@application.route("/CalibrateOD/<item>/<M>/<value>/<value2>",methods=['POST'])

@application.route("/MeasureOD/<M>",methods=['POST'])
   
@application.route("/MeasureFP/<M>",methods=['POST'])    

@application.route("/MeasureTemp/<which>/<M>",methods=['POST'])

@application.route("/ExperimentReset",methods=['POST'])

@application.route("/Experiment/<value>/<M>",methods=['POST'])


