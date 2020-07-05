import os
import random
import time
import math
import multiprocessing
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from datetime import datetime, date
import time
import simplejson
import csv
from flask import Flask, render_template, jsonify
from flask_restful import Resource, Api

dataDir = "/home/ChiBioData/"

manager = SyncManager(address=('127.0.0.1', 7777), authkey='abc')
manager.connect()

application = Flask(__name__)
application.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 #Try this https://stackoverflow.com/questions/23112316/using-flask-how-do-i-modify-the-cache-control-header-for-all-output/23115561#23115561
api = Api(application)

class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

api.add_resource(HelloWorld, '/')

#@application.route('/')
#def index():

#@application.route('/getSysData/')
#def getSysData():

#@application.route('/scanDevices/<which>',methods=['POST'])

#@application.route("/SetFPMeasurement/<item>/<Excite>/<Base>/<Emit1>/<Emit2>/<Gain>",methods=['POST'])

#@application.route("/SetOutputTarget/<item>/<M>/<value>",methods=['POST'])

#@application.route("/SetOutputOn/<item>/<force>/<M>",methods=['POST'])

#@application.route("/Direction/<item>/<M>",methods=['POST'])

#@application.route("/GetSpectrum/<Gain>/<M>",methods=['POST'])

#@application.route("/SetLightActuation/<Excite>",methods=['POST'])

#@application.route("/CharacteriseDevice/<M>/<Program>",methods=['POST'])     

#@application.route("/CalibrateOD/<item>/<M>/<value>/<value2>",methods=['POST'])

#@application.route("/MeasureOD/<M>",methods=['POST'])
   
#@application.route("/MeasureFP/<M>",methods=['POST'])    

#@application.route("/MeasureTemp/<which>/<M>",methods=['POST'])

def main():
    application.run(debug=True,threaded=True,host='0.0.0.0',port=5000)

if __name__ == "__main__": main()

