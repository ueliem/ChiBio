import os, time
from datetime import datetime, date
import multiprocessing
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
import serial
import simplejson
import copy
import smbus2 as smbus
import Adafruit_GPIO.I2C as I2C
import Adafruit_BBIO.GPIO as GPIO

#SysDevices is unique to each device and is responsible for storing information required for the digital communications, and various automation funtions. These values are stored outside sysData since they are not passable into the HTML interface using the jsonify package.        
sysDevices = {'M0' : {
    'AS7341' : {'device' : 0},
    'ThermometerInternal' : {'device' : 0},
    'ThermometerExternal' : {'device' : 0},
    'ThermometerIR' : {'device' : 0,'address' :0},
    'DAC' : {'device' : 0},
    'Pumps' : {'device' : 0,'startup' : 0, 'frequency' : 0},
    'PWM' : {'device' : 0,'startup' : 0, 'frequency' : 0},
    'Pump1' : {'thread' : 0,'threadCount' : 0, 'active' : 0},
    'Pump2' : {'thread' : 0,'threadCount' : 0, 'active' : 0},
    'Pump3' : {'thread' : 0,'threadCount' : 0, 'active' : 0},
    'Pump4' : {'thread' : 0,'threadCount' : 0, 'active' : 0},
    'Experiment' : {'thread' : 0},
    'Thermostat' : {'thread' : 0,'threadCount' : 0},
    
}}

core = {
    'Multiplexer': {'device' : 0},
    'Watchdog': {'thread' : 0, 'ON' : 1},
    'presentDevices' : { 'M0' : 0,'M1' : 0,'M2' : 0,'M3' : 0,'M4' : 0,'M5' : 0,'M6' : 0,'M7' : 0},
}

#sysItems stores information about digital addresses which is used as a reference for all devices.        
with open('sysdata.json', 'r') as f:
    sysData = simplejson.load(f)

with open('sysitems.json', 'r') as f:
    sysItems = simplejson.load(f)

class HAL(Process):
    def __init__(self, inQ, logQ):
        super(Process, self).__init__()
        self.running = False
        self.inQ = inQ
        self.logQ = logQ
        self.sysData = {}
        self.sysDevices = {}
        for M in ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
            self.sysData[M]=copy.deepcopy(sysData['M0'])
            self.sysDevices[M]=copy.deepcopy(sysDevices['M0'])
    def run(self):
        self.running = True
        while self.running:
            pass

    def I2CCom(self, M, device, rw, hl, data1, data2, SMBUSFLAG):
        global sysItems
        #Function used to manage I2C bus communications for ALL devices.
        M=str(M) #Turbidostat to write to
        device=str(device) #Name of device to be written to
        rw=int(rw) #1 if read, 0 if write
        hl=int(hl) #8 or 16
        SMBUSFLAG=int(SMBUSFLAG) # If this flag is set to 1 it means we are communuicating with an SMBUs device.
        data1=int(data1) if isinstance(data1, int) else int(data1, 16) #First data/register 
        if hl<20:
            data2=int(data2) if isinstance(data2, int) else int(data2, 16) #First data/register 
        if(self.sysData[M]['present']==0): #Something stupid has happened in software if this is the case!
            print(str(datetime.now()) + ' Trying to communicate with absent device - bug in software!. Disabling hardware and software!')
            sysItems['Watchdog']['ON']=0 #Basically this will crash all the electronics and the software. 
            out=0
            tries=-1
            os._exit(4)
        #cID=str(M)+str(device)+'d'+str(data1)+'d'+str(data2)  # This is an ID string for the communication that we are trying to send - not used at present
        #Any time a thread gets to this point it will wait until the lock is free. Then, only one thread at a time will advance. 
        #lock.acquire()
        #We now connect the multiplexer to the appropriate device to allow digital communications.
        tries=0
        while(tries!=-1):
            try:
                sysItems['Multiplexer']['device'].write8(int(0x00),int(sysItems['Multiplexer'][M],2)) #We have established connection to correct device. 
                check=(sysItems['Multiplexer']['device'].readRaw8()) #We check that the Multiplexer is indeed connected to the correct channel.
                if(check==int(sysItems['Multiplexer'][M],2)):
                    tries=-1
                else:
                    tries=tries+1
                    time.sleep(0.02)
                    print(str(datetime.now()) + ' Multiplexer didnt switch ' + str(tries) + " times on " + str(M))
            except: #If there is an error in the above.
                tries=tries+1
                time.sleep(0.02)
                print(str(datetime.now()) + ' Failed Multiplexer Comms ' + str(tries) + " times")
                if (tries>2):
                    try:
                        sysItems['Multiplexer']['device'].write8(int(0x00),int(0x00)) #Disconnect multiplexer. 
                        print('Disconnected multiplexer on ' + str(M) + ', trying to connect again.')
                    except:
                        print('Failed to recover multiplexer on device ' + str(M))
                if tries==5:
                    time.sleep(0.2)
                    
            if tries>20: #If it has failed a number of times then likely something is seriously wrong, so we crash the software.
                sysItems['Watchdog']['ON']=0 #Basically this will crash all the electronics and the software. 
                out=0
                print('Failed to communicate to Multiplexer 10 times. Disabling hardware and software!')
                tries=-1
                os._exit(4)
        time.sleep(0.0005)
        out=0;
        tries=0
        while(tries!=-1): #We now do appropriate read/write on the bus.
            try:
                if SMBUSFLAG==0:
                    if rw==1:
                        if hl==8:
                            out=int(self.sysDevices[M][device]['device'].readU8(data1))
                        elif(hl==16):
                            out=int(self.sysDevices[M][device]['device'].readU16(data1,data2))
                    else:
                        if hl==8:
                            self.sysDevices[M][device]['device'].write8(data1,data2)
                            out=1
                        elif(hl==16):
                            self.sysDevices[M][device]['device'].write16(data1,data2)
                            out=1
                elif SMBUSFLAG==1:
                    out=self.sysDevices[M][device]['device'].read_word_data(self.sysDevices[M][device]['address'],data1)
                tries=-1
            except: #If the above fails then we can try again (a limited number of times)
                tries=tries+1
                if (device!="ThermometerInternal"):
                    print(str(datetime.now()) + ' Failed ' + str(device) + ' comms ' + str(tries) + " times on device " + str(M) )
                    time.sleep(0.02)
                if (device=='AS7341'):
                    print(str(datetime.now()) + ' Failed  AS7341 in I2CCom while trying to send ' + str(data1)  + " and " + str(data2))
                    out=-1
                    tries=-1
            if (tries>2 and device=="ThermometerInternal"): #We don't allow the internal thermometer to fail, since this is what we are using to see if devices are plugged in at all.
                out=0
                self.sysData[M]['present']=0
                tries=-1
            if tries>10: #In this case something else has gone wrong, so we panic.
                sysItems['Watchdog']['ON']=0 #Basically this will crash all the electronics and the software. 
                out=0
                self.sysData[M]['present']=0
                print('Failed to communicate to a device 10 times. Disabling hardware and software!')
                tries=-1
                os._exit(4)
        time.sleep(0.0005)
        try:
            sysItems['Multiplexer']['device'].write8(int(0x00),int(0x00)) #Disconnect multiplexer with each iteration. 
        except:
            print('Failed to disconnect multiplexer on device ' + str(M))
        return(out)
    
    def scanDevices(self, which):
        which=str(which)
        
        if which=="all":
            for M in ['M0','M1','M2','M3','M4','M5','M6','M7']:
                self.sysData[M]['present'] = 1
                self.I2CCom(M,'ThermometerInternal',1,16,0x05,0,0) #We arbitrarily poll the thermometer to see if anything is plugged in! 
                self.sysData[M]['DeviceID'] = self.GetID(M)
        else: 
            M = which
            #print M + " before: " + str(self.sysData[M])
            self.sysData[which]['present'] = 1
            self.I2CCom(which,'ThermometerInternal',1,16,0x05,0,0)
            self.sysData[which]['DeviceID'] = self.GetID(which)
            #print M + " after: " + str(self.sysData[M])
        # return ('', 204)

    def GetID(self, M):
        #Gets the Chi.Bio reactor's ID, which is basically just the unique ID of the infrared thermometer.
        M = str(M)
        ID = ''
        #print M + ": " + str(self.sysData[M]['present'])
        if self.sysData[M]['present'] == 1:
            pt1 = str(self.I2CCom(M,'ThermometerIR',1,0,0x3C,0,1))
            pt2 = str(self.I2CCom(M,'ThermometerIR',1,0,0x3D,0,1))
            pt3 = str(self.I2CCom(M,'ThermometerIR',1,0,0x3E,0,1))
            pt4 = str(self.I2CCom(M,'ThermometerIR',1,0,0x3F,0,1))
            ID = pt1+pt2+pt3+pt4
        print "ID: " + str(len(ID))
        return ID

    def initialise(self, M):
        #Function that initialises all parameters / clears stored values for a given device.
        #If you want to record/add values to self.sysData, recommend adding an initialisation line in here.
        global sysItems;

        for LED in ['LEDA','LEDB','LEDC','LEDD','LEDE','LEDF','LEDG']:
            self.sysData[M][LED]['target']=self.sysData[M][LED]['default']
            self.sysData[M][LED]['ON']=0
        
        self.sysData[M]['UV']['target']=self.sysData[M]['UV']['default']
        self.sysData[M]['UV']['ON']=0
        
        self.sysData[M]['LASER650']['target']=self.sysData[M]['LASER650']['default']
        self.sysData[M]['LASER650']['ON']=0
        
        FP='FP1'
        self.sysData[M][FP]['ON']=0
        self.sysData[M][FP]['LED']="LEDB"
        self.sysData[M][FP]['Base']=0
        self.sysData[M][FP]['Emit1']=0
        self.sysData[M][FP]['Emit2']=0
        self.sysData[M][FP]['BaseBand']="CLEAR"
        self.sysData[M][FP]['Emit1Band']="nm510"
        self.sysData[M][FP]['Emit2Band']="nm550"
        self.sysData[M][FP]['Gain']="x10"
        self.sysData[M][FP]['BaseRecord']=[]
        self.sysData[M][FP]['Emit1Record']=[]
        self.sysData[M][FP]['Emit2Record']=[]
        FP='FP2'
        self.sysData[M][FP]['ON']=0
        self.sysData[M][FP]['LED']="LEDD"
        self.sysData[M][FP]['Base']=0
        self.sysData[M][FP]['Emit1']=0
        self.sysData[M][FP]['Emit2']=0
        self.sysData[M][FP]['BaseBand']="CLEAR"
        self.sysData[M][FP]['Emit1Band']="nm583"
        self.sysData[M][FP]['Emit2Band']="nm620"
        self.sysData[M][FP]['BaseRecord']=[]
        self.sysData[M][FP]['Emit1Record']=[]
        self.sysData[M][FP]['Emit2Record']=[]
        self.sysData[M][FP]['Gain']="x10"
        FP='FP3'
        self.sysData[M][FP]['ON']=0
        self.sysData[M][FP]['LED']="LEDE"
        self.sysData[M][FP]['Base']=0
        self.sysData[M][FP]['Emit1']=0
        self.sysData[M][FP]['Emit2']=0
        self.sysData[M][FP]['BaseBand']="CLEAR"
        self.sysData[M][FP]['Emit1Band']="nm620"
        self.sysData[M][FP]['Emit2Band']="nm670"
        self.sysData[M][FP]['BaseRecord']=[]
        self.sysData[M][FP]['Emit1Record']=[]
        self.sysData[M][FP]['Emit2Record']=[]
        self.sysData[M][FP]['Gain']="x10"
     
        for PUMP in ['Pump1','Pump2','Pump3','Pump4']:
            self.sysData[M][PUMP]['default']=0.0;
            self.sysData[M][PUMP]['target']=self.sysData[M][PUMP]['default']
            self.sysData[M][PUMP]['ON']=0
            self.sysData[M][PUMP]['direction']=1.0
            self.sysDevices[M][PUMP]['threadCount']=0
            self.sysDevices[M][PUMP]['active']=0
        
        
        self.sysData[M]['Heat']['default']=0;
        self.sysData[M]['Heat']['target']=self.sysData[M]['Heat']['default']
        self.sysData[M]['Heat']['ON']=0

        self.sysData[M]['Thermostat']['default']=37.0;
        self.sysData[M]['Thermostat']['target']=self.sysData[M]['Thermostat']['default']
        self.sysData[M]['Thermostat']['ON']=0
        self.sysData[M]['Thermostat']['Integral']=0
        self.sysData[M]['Thermostat']['last']=-1

        self.sysData[M]['Stir']['target']=self.sysData[M]['Stir']['default']
        self.sysData[M]['Stir']['ON']=0
        
        self.sysData[M]['Light']['target']=self.sysData[M]['Light']['default']
        self.sysData[M]['Light']['ON']=0
        self.sysData[M]['Light']['Excite']='LEDD'
        
        self.sysData[M]['Custom']['Status']=self.sysData[M]['Custom']['default']
        self.sysData[M]['Custom']['ON']=0
        self.sysData[M]['Custom']['Program']='C1'
        
        self.sysData[M]['Custom']['param1']=0.0
        self.sysData[M]['Custom']['param2']=0.0
        self.sysData[M]['Custom']['param3']=0.0
        
        self.sysData[M]['OD']['current']=0.0
        self.sysData[M]['OD']['target']=self.sysData[M]['OD']['default'];
        self.sysData[M]['OD0']['target']=65000.0
        self.sysData[M]['OD0']['raw']=65000.0
        self.sysData[M]['OD']['device']='LASER650'
        #self.sysData[M]['OD']['device']='LEDA'
        
        #if (M=='M0'):
        #    self.sysData[M]['OD']['device']='LEDA'
        
        
        self.sysData[M]['Volume']['target']=20.0
        
        #clearTerminal(M)
        #addTerminal(M,'System Initialised')
      
        self.sysData[M]['Experiment']['ON']=0
        self.sysData[M]['Experiment']['cycles']=0
        self.sysData[M]['Experiment']['threadCount']=0
        self.sysData[M]['Experiment']['startTime']=' Waiting '
        self.sysData[M]['Experiment']['startTimeRaw']=0
        self.sysData[M]['OD']['ON']=0
        self.sysData[M]['OD']['Measuring']=0
        self.sysData[M]['OD']['Integral']=0.0
        self.sysData[M]['OD']['Integral2']=0.0
        self.sysData[M]['Zigzag']['ON']=0
        self.sysData[M]['Zigzag']['target']=0.0
        self.sysData[M]['Zigzag']['SwitchPoint']=0
        self.sysData[M]['GrowthRate']['current']=self.sysData[M]['GrowthRate']['default']

        self.sysDevices[M]['Thermostat']['threadCount']=0

        channels=['nm410','nm440','nm470','nm510','nm550','nm583','nm620', 'nm670','CLEAR','NIR','DARK','ExtGPIO', 'ExtINT' , 'FLICKER']
        for channel in channels:
            self.sysData[M]['AS7341']['channels'][channel]=0
            self.sysData[M]['AS7341']['spectrum'][channel]=0
        DACS=['ADC0', 'ADC1', 'ADC2', 'ADC3', 'ADC4', 'ADC5']
        for DAC in DACS:
            self.sysData[M]['AS7341']['current'][DAC]=0

        self.sysData[M]['ThermometerInternal']['current']=0.0
        self.sysData[M]['ThermometerExternal']['current']=0.0
        self.sysData[M]['ThermometerIR']['current']=0.0
     
        self.sysData[M]['time']['record']=[]
        self.sysData[M]['OD']['record']=[]
        self.sysData[M]['OD']['targetrecord']=[]
        self.sysData[M]['Pump1']['record']=[]
        self.sysData[M]['Pump2']['record']=[]
        self.sysData[M]['Pump3']['record']=[]
        self.sysData[M]['Pump4']['record']=[]
        self.sysData[M]['Heat']['record']=[]
        self.sysData[M]['Light']['record']=[]
        self.sysData[M]['ThermometerInternal']['record']=[]
        self.sysData[M]['ThermometerExternal']['record']=[]
        self.sysData[M]['ThermometerIR']['record']=[]
        self.sysData[M]['Thermostat']['record']=[]
            
        self.sysData[M]['GrowthRate']['record']=[]

        self.sysDevices[M]['ThermometerInternal']['device']=I2C.get_i2c_device(0x18,2) #Get Thermometer on Bus 2!!!
        self.sysDevices[M]['ThermometerExternal']['device']=I2C.get_i2c_device(0x1b,2) #Get Thermometer on Bus 2!!!
        self.sysDevices[M]['DAC']['device']=I2C.get_i2c_device(0x48,2) #Get DAC on Bus 2!!!
        self.sysDevices[M]['AS7341']['device']=I2C.get_i2c_device(0x39,2) #Get OD Chip on Bus 2!!!!!
        self.sysDevices[M]['Pumps']['device']=I2C.get_i2c_device(0x61,2) #Get OD Chip on Bus 2!!!!!
        self.sysDevices[M]['Pumps']['startup']=0
        self.sysDevices[M]['Pumps']['frequency']=0x1e #200Hz PWM frequency
        self.sysDevices[M]['PWM']['device']=I2C.get_i2c_device(0x60,2) #Get OD Chip on Bus 2!!!!!
        self.sysDevices[M]['PWM']['startup']=0
        self.sysDevices[M]['PWM']['frequency']=0x03# 0x14 = 300hz, 0x03 is 1526 Hz PWM frequency for fan/LEDs, maximum possible. Potentially dial this down if you are getting audible ringing in the device! 
        #There is a tradeoff between large frequencies which can make capacitors in the 6V power regulation oscillate audibly, and small frequencies which result in the number of LED "ON" cycles varying during measurements.
        self.sysDevices[M]['ThermometerIR']['device']=smbus.SMBus(bus=2) #Set up SMBus thermometer
        self.sysDevices[M]['ThermometerIR']['address']=0x5a 
        
        
        # This section of commented code is used for testing I2C communication integrity.
        # self.sysData[M]['present']=1
        # getData=I2CCom(M,'ThermometerInternal',1,16,0x05,0,0)
        # i=0
        # while (1==1):
        #     i=i+1
        #     if (i%1000==1):
        #         print(str(i))
        #     self.sysDevices[M]['ThermometerInternal']['device'].readU8(int(0x05))
        # getData=I2CCom(M,which,1,16,0x05,0,0)

        self.scanDevices(M)
        if(self.sysData[M]['present']==1):
            self.turnEverythingOff(M)
            print(str(datetime.now()) + " Initialised " + str(M) +', Device ID: ' + self.sysData[M]['DeviceID'])

    def initialiseAll(self):
        global sysItems
        # Initialisation function which runs at when software is started for the first time.
        sysItems['Multiplexer']['device']=I2C.get_i2c_device(0x74,2) 
        sysItems['FailCount']=0
        time.sleep(2.0) #This wait is to allow the watchdog circuit to boot.
        print(str(datetime.now()) + ' Initialising devices')

        for M in ['M0','M1','M2','M3','M4','M5','M6','M7']:
            self.initialise(M)
        #self.scanDevices("all")

    def setPWM(self, M, device, channels, fraction, ConsecutiveFails):
        #Sets up the PWM chip (either the one in the reactor or on the pump board)
        global sysItems
        
        if self.sysDevices[M][device]['startup']==0: #The following boots up the respective PWM device to the correct frequency. Potentially there is a bug here; if the device loses power after this code is run for the first time it may revert to default PWM frequency.
            self.I2CCom(M,device,0,8,0x00,0x11,0) #Turns off device.
            self.I2CCom(M,device,0,8,0xfe,sysDevices[M][device]['frequency'],0) #Sets frequency of PWM oscillator. 
            self.sysDevices[M][device]['startup']=1
        self.I2CCom(M,device,0,8,0x00,0x01,0) #Turns device on for sure! 
        
        timeOn=int(fraction*4095.99)
        self.I2CCom(M,device,0,8,channels['ONL'],0x00,0)
        self.I2CCom(M,device,0,8,channels['ONH'],0x00,0)
        
        OffVals=bin(timeOn)[2:].zfill(12)
        HighVals='0000' + OffVals[0:4]
        LowVals=OffVals[4:12]
        
        self.I2CCom(M,device,0,8,channels['OFFL'],int(LowVals,2),0)
        self.I2CCom(M,device,0,8,channels['OFFH'],int(HighVals,2),0)
        
        CheckLow=self.I2CCom(M,device,1,8,channels['OFFL'],-1,0)
        CheckHigh=self.I2CCom(M,device,1,8,channels['OFFH'],-1,0)
        CheckLowON=self.I2CCom(M,device,1,8,channels['ONL'],-1,0)
        CheckHighON=self.I2CCom(M,device,1,8,channels['ONH'],-1,0)
        
        if(CheckLow!=(int(LowVals,2)) or CheckHigh!=(int(HighVals,2)) or CheckHighON!=int(0x00) or CheckLowON!=int(0x00)): #We check to make sure it has been set to appropriate values.
            ConsecutiveFails=ConsecutiveFails+1
            print(str(datetime.now()) + ' Failed transmission test on ' + str(device) + ' ' + str(ConsecutiveFails) + ' times consecutively on device '  + str(M) )
            if ConsecutiveFails>10:
                sysItems['Watchdog']['ON']=0 #Basically this will crash all the electronics and the software. 
                print('Failed to communicate to PWM 10 times. Disabling hardware and software!')
                os._exit(4)
            else:
                time.sleep(0.1)
                sysItems['FailCount']=sysItems['FailCount']+1
                self.setPWM(M,device,channels,fraction,ConsecutiveFails)

    def SetOutputOn(self, M, item, force):
        #General function used to switch an output on or off.
        global sysItems
        item = str(item)
        force = int(force)
        M=str(M)
        if (M=="0"):
            M=sysItems['UIDevice']
        #The first statements are to force it on or off it the command is called in force mode (force implies it sets it to a given state, regardless of what it is currently in)
        if (force==1):
            self.sysData[M][item]['ON']=1
            self.SetOutput(M,item)
            return ('', 204)    
        elif(force==0):
            self.sysData[M][item]['ON']=0;
            self.SetOutput(M,item)
            return ('', 204)    
        #Elsewise this is doing a flip operation (i.e. changes to opposite state to that which it is currently in)
        if (self.sysData[M][item]['ON']==0):
            self.sysData[M][item]['ON']=1
            self.SetOutput(M,item)
            return ('', 204)    
        else:
            self.sysData[M][item]['ON']=0;
            self.SetOutput(M,item)
            return ('', 204)    

    def SetOutput(self, M, item):
        #Here we actually do the digital communications required to set a given output. This function is called by SetOutputOn above as required.
        global sysItems
        M=str(M)
        #We go through each different item and set it going as appropriate.
        if(item=='Stir'): 
            #Stirring is initiated at a high speed for a couple of seconds to prevent the stir motor from stalling (e.g. if it is started at an initial power of 0.3)
            if (self.sysData[M][item]['target']*float(self.sysData[M][item]['ON'])>0):
                self.setPWM(M,'PWM',sysItems[item],1.0*float(self.sysData[M][item]['ON']),0) # This line is to just get stirring started briefly.
                time.sleep(1.5)

                if (self.sysData[M][item]['target']>0.4 and self.sysData[M][item]['ON']==1):
                    self.setPWM(M,'PWM',sysItems[item],0.5*float(self.sysData[M][item]['ON']),0) # This line is to just get stirring started briefly.
                    time.sleep(0.75)
                
                if (self.sysData[M][item]['target']>0.8 and self.sysData[M][item]['ON']==1):
                    self.setPWM(M,'PWM',sysItems[item],0.7*float(self.sysData[M][item]['ON']),0) # This line is to just get stirring started briefly.
                    time.sleep(0.75)

            self.setPWM(M,'PWM',sysItems[item],self.sysData[M][item]['target']*float(self.sysData[M][item]['ON']),0)
            
            
        elif(item=='Heat'):
            self.setPWM(M,'PWM',sysItems[item],self.sysData[M][item]['target']*float(self.sysData[M][item]['ON']),0)
        elif(item=='UV'):
            self.setPWM(M,'PWM',sysItems[item],self.sysData[M][item]['target']*float(self.sysData[M][item]['ON']),0)
        #elif (item=='Thermostat'):
            #self.sysDevices[M][item]['thread']=Process(target = Thermostat, args=(M,item))
            #self.sysDevices[M][item]['thread'].daemon = True
            #self.sysDevices[M][item]['thread'].start();
        #elif (item=='Pump1' or item=='Pump2' or item=='Pump3' or item=='Pump4'): 
            #if (self.sysData[M][item]['target']==0):
                #self.sysData[M][item]['ON']=0
            #self.sysDevices[M][item]['thread']=Process(target = PumpModulation, args=(M,item))
            #self.sysDevices[M][item]['thread'].daemon = True
            #self.sysDevices[M][item]['thread'].start();
        elif (item=='OD'):
            self.SetOutputOn(M,'Pump1',0)
            self.SetOutputOn(M,'Pump2',0) #We turn pumps off when we switch OD state
        elif (item=='Zigzag'):
            self.sysData[M]['Zigzag']['target']=5.0
            self.sysData[M]['Zigzag']['SwitchPoint']=self.sysData[M]['Experiment']['cycles']
        
        elif (item=='LEDA' or item=='LEDB' or item=='LEDC' or item=='LEDD' or item=='LEDE' or item=='LEDF' or item=='LEDG'):
            self.setPWM(M,'PWM',sysItems[item],self.sysData[M][item]['target']*float(self.sysData[M][item]['ON']),0)
            
        else: #This is if we are setting the DAC. All should be in range [0,1]
            register = int(sysItems['DAC'][item],2)
            
            value=self.sysData[M][item]['target']*float(self.sysData[M][item]['ON']) 
            if (value==0):
                value=0
            else:
                value=(value+0.00)/1.00
                sf=0.303 #This factor is scaling down the maximum voltage being fed to the laser, preventing its photodiode current (and hence optical power) being too large.
                value=value*sf
            binaryValue=bin(int(value*4095.9)) #Bit of a dodgy method for ensuring we get an integer in [0,4095]
            toWrite=str(binaryValue[2:].zfill(16))
            toWrite1=int(toWrite[0:8],2)
            toWrite2=int(toWrite[8:16],2)
            self.I2CCom(M,'DAC',0,8,toWrite1,toWrite2,0)

    def turnEverythingOff(self, M):
        global sysItems
        # Function which turns off all actuation/hardware.
        for LED in ['LEDA','LEDB','LEDC','LEDD','LEDE','LEDF','LEDG']:
            self.sysData[M][LED]['ON']=0
            
        self.sysData[M]['LASER650']['ON']=0
        self.sysData[M]['Pump1']['ON']=0
        self.sysData[M]['Pump2']['ON']=0
        self.sysData[M]['Pump3']['ON']=0
        self.sysData[M]['Pump4']['ON']=0
        self.sysData[M]['Stir']['ON']=0
        self.sysData[M]['Heat']['ON']=0
        self.sysData[M]['UV']['ON']=0
        
        self.I2CCom(M,'DAC',0,8,int('00000000',2),int('00000000',2),0)#Sets all DAC Channels to zero!!! 
        self.setPWM(M,'PWM',sysItems['All'],0,0)
        self.setPWM(M,'Pumps',sysItems['All'],0,0)
        
        self.SetOutputOn(M,'Stir',0)
        #self.SetOutputOn(M,'Thermostat',0)
        self.SetOutputOn(M,'Heat',0)
        self.SetOutputOn(M,'UV',0)
        #self.SetOutputOn(M,'Pump1',0)
        #self.SetOutputOn(M,'Pump2',0)
        #self.SetOutputOn(M,'Pump3',0)
        #self.SetOutputOn(M,'Pump4',0)
           

# This section of code is responsible for the watchdog circuit. The circuit is implemented in hardware on the control computer, and requires the watchdog pin be toggled low->high each second, otherwise it will power down all connected devices. This section is therefore critical to operation of the device.
def runWatchdog():  
    #Watchdog toggling function which continually runs in a thread.
    global sysItems
    while (sysItems['Watchdog']['ON']==1):
        sysItems['Watchdog']['thread']
        GPIO.output(sysItems['Watchdog']['pin'], GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(sysItems['Watchdog']['pin'], GPIO.LOW)
        time.sleep(0.4)

GPIO.setup(sysItems['Watchdog']['pin'], GPIO.OUT)
print(str(datetime.now()) + ' Starting watchdog')
sysItems['Watchdog']['thread']=Process(target = runWatchdog, args=())
sysItems['Watchdog']['thread'].daemon = True
sysItems['Watchdog']['thread'].start(); 

def main():
    print("done")
    manager = SyncManager(address=('', 7777), authkey='abc')
    manager.start()
    q1 = manager.Queue()
    q2 = manager.Queue()
    h = HAL(q1, q2)
    h.initialiseAll()

if __name__ == "__main__": main()

