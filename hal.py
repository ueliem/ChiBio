import os
import time
from datetime import datetime
from multiprocessing import Process
import copy
import simplejson
import smbus2 as smbus
from Adafruit_GPIO import I2C
from Adafruit_BBIO import GPIO

# SysDevices is unique to each device and is responsible for storing information
# required for the digital communications, and various automation funtions.
# These values are stored outside sysData since they are not passable into the
# HTML interface using the jsonify package.
with open('sysdevices.json', 'r') as f:
    SYS_DEVICES = simplejson.load(f)

#self.hwmap stores information about digital addresses which is used as a reference for all devices.
with open('sysdata.json', 'r') as f:
    SYS_DATA = simplejson.load(f)

class CommandPacket(object):
    def __init__(self, cmd, M, params):
        self.time = datetime.now()
        self.cmd = cmd
        self.M = M
        self.params = params
    def __str__(self):
        return str(self.time) + " CMD " + str(self.cmd) + " " + self.M + " " + str(self.params)

class LogPacket(object):
    def __init__(self, msg):
        self.time = datetime.now()
        self.kind = "logpacket"
        self.msg = msg
    def __str__(self):
        return str(self.time) + " " + str(self.msg)

class HAL(Process):
    def __init__(self, in_q, log_q, hwlock, running):
        (Process.__init__(self))
        self.in_q = in_q
        self.log_q = log_q
        self.hwlock = hwlock
        self.running = running
        self.mux = None
        self.sys_data = {}
        self.sys_devices = {}
        with open('sysitems.json', 'r') as f:
            self.hwmap = simplejson.load(f)

        for M in ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
            self.sys_data[M] = copy.deepcopy(SYS_DATA['M0'])
            self.sys_devices[M] = copy.deepcopy(SYS_DEVICES['M0'])
    def run(self):
        time.sleep(2.0)
        self.initialise_all()
        self.log("started")
        while not self.running.is_set():
            self.set_led('M0', 'LEDA', 1.0)
            self.set_pump('M0', 'Pump1', 1.0, 'forward')
            time.sleep(1)
            self.set_led('M0', 'LEDA', 0.0)
            self.set_pump('M0', 'Pump1', 0.0, 'forward')
            self.log("testing")
            time.sleep(3)
    def log(self, msg):
        self.log_q.put(LogPacket(msg))

    #LEDS A-G
    def set_led(self, M, item, target):
        if item in ['LEDA', 'LEDB', 'LEDC', 'LEDD', 'LEDE', 'LEDF', 'LEDG']:
            if target >= 0.0 and target <= 1.0:
                self.set_pwm(M, 'PWM', self.hwmap[item], target, 0)
        else:
            self.log('Cannot set LED with name \"' + item + '\" on reactor ' + M)
    #LASER
    def set_laser(self, M, target):
        # register = int(sysItems['DAC'][item],2)
        if target == 0.0:
            # Sets all DAC Channels to zero!!!
            self.i2c_com(M, 'DAC', 0, 8, int('00000000', 2), int('00000000', 2), 0)
        elif target > 0.0 and target <= 1.0:
            # This factor is scaling down the maximum voltage being fed to the laser,
            # preventing its photodiode current (and hence optical power) being too large.
            sf = 0.303
            target = target * sf
            # Bit of a dodgy method for ensuring we get an integer in [0,4095]
            binary_value = bin(int(target * 4095.9))
            to_write = str(binary_value[2:].zfill(16))
            to_write1 = int(to_write[0:8], 2)
            to_write2 = int(to_write[8:16], 2)
            self.i2c_com(M, 'DAC', 0, 8, to_write1, to_write2, 0)
    #UV
    def set_uv(self, M, target):
        self.set_pwm(M, 'PWM', self.hwmap['UV'], target, 0)
    #PUMPS
    def set_pump(self, M, item, target, direction):
        if target == 0.0:
            self.set_pwm(M, 'Pumps', self.hwmap[item]['In1'], 0.0, 0)
            self.set_pwm(M, 'Pumps', self.hwmap[item]['In2'], 0.0, 0)
        elif target > 0.0 and target <= 1.0:
            if direction == 'forward':
                self.set_pwm(M, 'Pumps', self.hwmap[item]['In1'], target, 0)
                self.set_pwm(M, 'Pumps', self.hwmap[item]['In2'], 0.0, 0)
            elif direction == 'backward':
                self.set_pwm(M, 'Pumps', self.hwmap[item]['In1'], 0.0, 0)
                self.set_pwm(M, 'Pumps', self.hwmap[item]['In2'], target, 0)
    #HEATER
    def set_heater(self, M, target):
        if target >= 0.0 and target <= 1.0:
            self.set_pwm(M, 'PWM', self.hwmap['Heat'], target, 0)
    #STIRRER
    def set_stir(self, M, target):
        if target == 0.0:
            self.set_pwm(M, 'PWM', self.hwmap['Stir'], 0.0, 0)
        elif target > 0.0 and target <= 1.0:
            # This line is to just get stirring started briefly.
            self.set_pwm(M, 'PWM', self.hwmap['Stir'], 1.0, 0)
            time.sleep(0.05)
            self.set_pwm(M, 'PWM', self.hwmap['Stir'], target, 0)

    #TEMP INTERNAL
    def get_temp_int(self, M):
        get_data = self.i2c_com(M, 'ThermometerInternal', 1, 16, 0x05, 0, 0)
        get_data_binary = bin(get_data)
        temp_data = get_data_binary[6:]
        temperature = float(int(temp_data, 2))/16.0
        return temperature
    #TEMP EXTERNAL
    def get_temp_ext(self, M):
        get_data = self.i2c_com(M, 'ThermometerExternal', 1, 16, 0x05, 0, 0)
        get_data_binary = bin(get_data)
        temp_data = get_data_binary[6:]
        temperature = float(int(temp_data, 2)) / 16.0
        return temperature
    #TEMP IR
    def get_temp_ir(self, M):
        get_data = self.i2c_com(M, 'ThermometerIR', 1, 0, 0x07, 0, 1)
        temperature = (get_data * 0.02) - 273.15
        return temperature

    #OD
    def get_od(self, M):
        pass
    #FP
    #SPECT

    def i2c_com(self, M, device, rw, hl, data1, data2, smbus_flag=0):
        #Function used to manage I2C bus communications for ALL devices.
        M = str(M) #Turbidostat to write to
        device = str(device) #Name of device to be written to
        rw = int(rw) #1 if read, 0 if write
        hl = int(hl) #8 or 16
        # If this flag is set to 1 it means we are communuicating with an SMBUs device.
        smbus_flag = int(smbus_flag)
        data1 = int(data1) if isinstance(data1, int) else int(data1, 16) #First data/register
        if hl < 20:
            data2 = int(data2) if isinstance(data2, int) else int(data2, 16) #First data/register
        with self.hwlock:
            if self.sys_data[M]['present'] == 0:
                # Something stupid has happened in software if this is the case!
                self.log(str(datetime.now()) + \
                    ' Trying to communicate with absent device - bug in software!. \
                    Disabling hardware and software!')
                self.running.set() #Basically this will crash all the electronics and the software.
                return 0
                #out=0
                #tries=-1
                #os._exit(4)
            # This is an ID string for the communication that we are trying to send
            # - not used at present
            # cID=str(M)+str(device)+'d'+str(data1)+'d'+str(data2)
            # Any time a thread gets to this point it will wait until the lock is free.
            # Then, only one thread at a time will advance.
            # lock.acquire()
            # We now connect the multiplexer to the appropriate device
            # to allow digital communications.
            tries = 0
            while not self.running.is_set() and tries != -1:
                try:
                    # We have established connection to correct device.
                    self.mux.write8(int(0x00), int(self.hwmap['Multiplexer'][M], 2))
                    # We check that the Multiplexer is indeed connected to the correct channel.
                    check = self.mux.readRaw8()
                    if check == int(self.hwmap['Multiplexer'][M], 2):
                        break # good to go
                    else:
                        tries += 1
                        time.sleep(0.02)
                        self.log(str(datetime.now()) + ' Multiplexer didnt switch ' \
                                + str(tries) + " times on " + str(M))
                except: # If there is an error in the above.
                    tries += 1
                    time.sleep(0.02)
                    self.log(str(datetime.now()) + ' Failed Multiplexer Comms ' \
                            + str(tries) + " times")
                    if tries > 2:
                        try:
                            self.mux.write8(int(0x00), int(0x00)) #Disconnect multiplexer.
                            self.log('Disconnected multiplexer on ' + str(M) \
                                    + ', trying to connect again.')
                        except:
                            self.log('Failed to recover multiplexer on device ' + str(M))
                    if tries == 5:
                        time.sleep(0.2)
                if tries > 20:
                    # If it has failed a number of times then likely something is \
                    # seriously wrong, so we crash the software.
                    self.log('Failed to communicate to Multiplexer 10 times. \
                            Disabling hardware and software!')
                    # Basically this will crash all the electronics and the software.
                    self.running.set()
                    return 0
                    #out=0
                    #tries=-1
                    #os._exit(4)
            time.sleep(0.0005)
            out = 0
            tries = 0
            while not self.running.is_set() and tries != -1:
                #We now do appropriate read/write on the bus.
                try:
                    if smbus_flag == 0:
                        if rw == 1:
                            if hl == 8:
                                out = int(self.sys_devices[M][device]['device'].readU8(data1))
                            elif hl == 16:
                                out = int(self.sys_devices[M][device]['device'] \
                                        .readU16(data1, data2))
                        else:
                            if hl == 8:
                                self.sys_devices[M][device]['device'].write8(data1, data2)
                                out = 1
                            elif hl == 16:
                                self.sys_devices[M][device]['device'].write16(data1, data2)
                                out = 1
                    elif smbus_flag == 1:
                        out = self.sys_devices[M][device]['device'] \
                                .read_word_data(self.sys_devices[M][device]['address'], data1)
                    tries = -1
                except: #If the above fails then we can try again (a limited number of times)
                    tries += 1
                    if device != "ThermometerInternal":
                        self.log(str(datetime.now()) + ' Failed ' + str(device) + ' comms ' \
                                + str(tries) + " times on device " + str(M))
                        time.sleep(0.02)
                    if device == 'AS7341':
                        self.log(str(datetime.now()) \
                                + ' Failed  AS7341 in i2c_com while trying to send ' \
                                + str(data1)  + " and " + str(data2))
                        out = -1
                        tries = -1
                if tries > 2 and device == "ThermometerInternal":
                    # We don't allow the internal thermometer to fail, since this is what
                    # we are using to see if devices are plugged in at all.
                    out = 0
                    self.sys_data[M]['present'] = 0
                    tries = -1
                if tries > 10: # In this case something else has gone wrong, so we panic.
                    #out = 0
                    self.sys_data[M]['present'] = 0
                    self.log('Failed to communicate to a device 10 times. \
                            Disabling hardware and software!')
                    # Basically this will crash all the electronics and the software.
                    self.running.set()
                    return 0
                    #tries = -1
                    #os._exit(4)
            time.sleep(0.0005)
            try:
                # Disconnect multiplexer with each iteration.
                self.mux.write8(int(0x00), int(0x00))
            except:
                self.log('Failed to disconnect multiplexer on device ' + str(M))
            return out

    def scan_devices(self, which):
        which = str(which)
        if which == "all":
            for M in ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
                self.sys_data[M]['present'] = 1
                # We arbitrarily poll the thermometer to see if anything is plugged in!
                self.i2c_com(M, 'ThermometerInternal', 1, 16, 0x05, 0, 0)
                self.sys_data[M]['DeviceID'] = self.get_id(M)
        else:
            M = which
            self.sys_data[which]['present'] = 1
            self.i2c_com(which, 'ThermometerInternal', 1, 16, 0x05, 0, 0)
            self.sys_data[which]['DeviceID'] = self.get_id(which)

    def get_id(self, M):
        # Gets the Chi.Bio reactor's ID, which is basically just
        # the unique ID of the infrared thermometer.
        M = str(M)
        ID = ''
        if self.sys_data[M]['present'] == 1:
            pt1 = str(self.i2c_com(M, 'ThermometerIR', 1, 0, 0x3C, 0, 1))
            pt2 = str(self.i2c_com(M, 'ThermometerIR', 1, 0, 0x3D, 0, 1))
            pt3 = str(self.i2c_com(M, 'ThermometerIR', 1, 0, 0x3E, 0, 1))
            pt4 = str(self.i2c_com(M, 'ThermometerIR', 1, 0, 0x3F, 0, 1))
            ID = pt1 + pt2 + pt3 + pt4
        return ID

    def initialise(self, M):
        # Function that initialises all parameters / clears stored values for a given device.
        # If you want to record/add values to self.sys_data,
        # recommend adding an initialisation line in here.
        for led in ['LEDA', 'LEDB', 'LEDC', 'LEDD', 'LEDE', 'LEDF', 'LEDG']:
            self.sys_data[M][led]['target'] = self.sys_data[M][led]['default']
            self.sys_data[M][led]['ON'] = 0

        self.sys_data[M]['UV']['target'] = self.sys_data[M]['UV']['default']
        self.sys_data[M]['UV']['ON'] = 0

        self.sys_data[M]['LASER650']['target'] = self.sys_data[M]['LASER650']['default']
        self.sys_data[M]['LASER650']['ON'] = 0

        FP = 'FP1'
        self.sys_data[M][FP]['ON'] = 0
        self.sys_data[M][FP]['LED'] = "LEDB"
        self.sys_data[M][FP]['Base'] = 0
        self.sys_data[M][FP]['Emit1'] = 0
        self.sys_data[M][FP]['Emit2'] = 0
        self.sys_data[M][FP]['BaseBand'] = "CLEAR"
        self.sys_data[M][FP]['Emit1Band'] = "nm510"
        self.sys_data[M][FP]['Emit2Band'] = "nm550"
        self.sys_data[M][FP]['Gain'] = "x10"
        self.sys_data[M][FP]['BaseRecord'] = []
        self.sys_data[M][FP]['Emit1Record'] = []
        self.sys_data[M][FP]['Emit2Record'] = []
        FP = 'FP2'
        self.sys_data[M][FP]['ON'] = 0
        self.sys_data[M][FP]['LED'] = "LEDD"
        self.sys_data[M][FP]['Base'] = 0
        self.sys_data[M][FP]['Emit1'] = 0
        self.sys_data[M][FP]['Emit2'] = 0
        self.sys_data[M][FP]['BaseBand'] = "CLEAR"
        self.sys_data[M][FP]['Emit1Band'] = "nm583"
        self.sys_data[M][FP]['Emit2Band'] = "nm620"
        self.sys_data[M][FP]['BaseRecord'] = []
        self.sys_data[M][FP]['Emit1Record'] = []
        self.sys_data[M][FP]['Emit2Record'] = []
        self.sys_data[M][FP]['Gain'] = "x10"
        FP = 'FP3'
        self.sys_data[M][FP]['ON'] = 0
        self.sys_data[M][FP]['LED'] = "LEDE"
        self.sys_data[M][FP]['Base'] = 0
        self.sys_data[M][FP]['Emit1'] = 0
        self.sys_data[M][FP]['Emit2'] = 0
        self.sys_data[M][FP]['BaseBand'] = "CLEAR"
        self.sys_data[M][FP]['Emit1Band'] = "nm620"
        self.sys_data[M][FP]['Emit2Band'] = "nm670"
        self.sys_data[M][FP]['BaseRecord'] = []
        self.sys_data[M][FP]['Emit1Record'] = []
        self.sys_data[M][FP]['Emit2Record'] = []
        self.sys_data[M][FP]['Gain'] = "x10"

        for pump in ['Pump1', 'Pump2', 'Pump3', 'Pump4']:
            self.sys_data[M][pump]['default'] = 0.0
            self.sys_data[M][pump]['target'] = self.sys_data[M][pump]['default']
            self.sys_data[M][pump]['ON'] = 0
            self.sys_data[M][pump]['direction'] = 1.0
            self.sys_devices[M][pump]['active'] = 0

        self.sys_data[M]['Heat']['default'] = 0
        self.sys_data[M]['Heat']['target'] = self.sys_data[M]['Heat']['default']
        self.sys_data[M]['Heat']['ON'] = 0

        self.sys_data[M]['Stir']['target'] = self.sys_data[M]['Stir']['default']
        self.sys_data[M]['Stir']['ON'] = 0

        self.sys_data[M]['Light']['target'] = self.sys_data[M]['Light']['default']
        self.sys_data[M]['Light']['ON'] = 0
        self.sys_data[M]['Light']['Excite'] = 'LEDD'

        self.sys_data[M]['OD']['current'] = 0.0
        self.sys_data[M]['OD']['target'] = self.sys_data[M]['OD']['default']
        self.sys_data[M]['OD0']['target'] = 65000.0
        self.sys_data[M]['OD0']['raw'] = 65000.0
        self.sys_data[M]['OD']['device'] = 'LASER650'
        #self.sys_data[M]['OD']['device'] = 'LEDA'
        #if (M =  = 'M0'):
        #    self.sys_data[M]['OD']['device'] = 'LEDA'
        self.sys_data[M]['Volume']['target'] = 20.0

        self.sys_data[M]['OD']['ON'] = 0
        self.sys_data[M]['OD']['Measuring'] = 0
        self.sys_data[M]['OD']['Integral'] = 0.0
        self.sys_data[M]['OD']['Integral2'] = 0.0
        channels = ['nm410', 'nm440', 'nm470', 'nm510', 'nm550', 'nm583', 'nm620', \
                'nm670', 'CLEAR', 'NIR', 'DARK', 'ExtGPIO', 'ExtINT', 'FLICKER']
        for channel in channels:
            self.sys_data[M]['AS7341']['channels'][channel] = 0
            self.sys_data[M]['AS7341']['spectrum'][channel] = 0
        adcs = ['adc0', 'adc1', 'adc2', 'adc3', 'adc4', 'adc5']
        for adc in adcs:
            self.sys_data[M]['AS7341']['current'][adc] = 0

        self.sys_data[M]['ThermometerInternal']['current'] = 0.0
        self.sys_data[M]['ThermometerExternal']['current'] = 0.0
        self.sys_data[M]['ThermometerIR']['current'] = 0.0

        #Get Thermometer on Bus 2!
        self.sys_devices[M]['ThermometerInternal']['device'] = I2C.get_i2c_device(0x18, 2)
        #Get Thermometer on Bus 2!
        self.sys_devices[M]['ThermometerExternal']['device'] = I2C.get_i2c_device(0x1b, 2)
        self.sys_devices[M]['DAC']['device'] = I2C.get_i2c_device(0x48, 2) #Get DAC on Bus 2!
        self.sys_devices[M]['AS7341']['device'] = I2C.get_i2c_device(0x39, 2) #Get OD Chip on Bus 2!
        self.sys_devices[M]['Pumps']['device'] = I2C.get_i2c_device(0x61, 2)
        self.sys_devices[M]['Pumps']['startup'] = 0
        self.sys_devices[M]['Pumps']['frequency'] = 0x1e #200Hz PWM frequency
        self.sys_devices[M]['PWM']['device'] = I2C.get_i2c_device(0x60, 2)
        self.sys_devices[M]['PWM']['startup'] = 0
        # 0x14  =  300hz, 0x03 is 1526 Hz PWM frequency for fan/LEDs, maximum possible.
        # Potentially dial this down if you are getting audible ringing in the device!
        self.sys_devices[M]['PWM']['frequency'] = 0x03
        # There is a tradeoff between large frequencies which can make capacitors
        # in the 6V power regulation oscillate audibly, and small frequencies which result
        # in the number of LED "ON" cycles varying during measurements.
        # Set up SMBus thermometer
        self.sys_devices[M]['ThermometerIR']['device'] = smbus.SMBus(bus=2)
        self.sys_devices[M]['ThermometerIR']['address'] = 0x5a

        # This section of commented code is used for testing I2C communication integrity.
        # self.sys_data[M]['present']=1
        # getData=i2c_com(M,'ThermometerInternal',1,16,0x05,0,0)
        # i=0
        # while (1==1):
        #     i=i+1
        #     if (i%1000==1):
        #         print(str(i))
        #     self.sys_devices[M]['ThermometerInternal']['device'].readU8(int(0x05))
        # getData=i2c_com(M,which,1,16,0x05,0,0)

        self.scan_devices(M)
        if self.sys_data[M]['present'] == 1:
            self.turnEverythingOff(M)
            self.log(" Initialised " + str(M) +', Device ID: ' + self.sys_data[M]['DeviceID'])

    def initialise_all(self):
        # Initialisation function which runs at when software is started for the first time.
        self.mux = I2C.get_i2c_device(0x74, 2)
        self.hwmap['FailCount'] = 0
        time.sleep(2.0) #This wait is to allow the watchdog circuit to boot.
        self.log(str(datetime.now()) + ' Initialising devices')
        for M in ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
            self.initialise(M)
        #self.scan_devices("all")

    def set_pwm(self, M, device, channels, fraction, consecutive_fails):
        #Sets up the PWM chip (either the one in the reactor or on the pump board)
        if self.sys_devices[M][device]['startup'] == 0:
            # The following boots up the respective PWM device to the correct frequency.
            # Potentially there is a bug here; if the device loses power after this code
            # is run for the first time it may revert to default PWM frequency.
            self.i2c_com(M, device, 0, 8, 0x00, 0x11, 0) #Turns off device.
            # Sets frequency of PWM oscillator.
            self.i2c_com(M, device, 0, 8, 0xfe, self.sys_devices[M][device]['frequency'], 0)
            self.sys_devices[M][device]['startup'] = 1
        self.i2c_com(M, device, 0, 8, 0x00, 0x01, 0) #Turns device on for sure!

        time_on = int(fraction * 4095.99)
        self.i2c_com(M, device, 0, 8, channels['ONL'], 0x00, 0)
        self.i2c_com(M, device, 0, 8, channels['ONH'], 0x00, 0)

        off_vals = bin(time_on)[2:].zfill(12)
        high_vals = '0000' + off_vals[0:4]
        low_vals = off_vals[4:12]

        self.i2c_com(M, device, 0, 8, channels['OFFL'], int(low_vals, 2), 0)
        self.i2c_com(M, device, 0, 8, channels['OFFH'], int(high_vals, 2), 0)

        check_low = self.i2c_com(M, device, 1, 8, channels['OFFL'], -1, 0)
        check_high = self.i2c_com(M, device, 1, 8, channels['OFFH'], -1, 0)
        check_low_on = self.i2c_com(M, device, 1, 8, channels['ONL'], -1, 0)
        check_high_on = self.i2c_com(M, device, 1, 8, channels['ONH'], -1, 0)

        # We check to make sure it has been set to appropriate values.
        if check_low != (int(low_vals, 2)) or check_high != (int(high_vals, 2)) or \
                check_high_on != int(0x00) or check_low_on != int(0x00):
            consecutive_fails = consecutive_fails + 1
            self.log(str(datetime.now()) + ' Failed transmission test on ' \
                    + str(device) + ' ' + str(consecutive_fails) \
                    + ' times consecutively on device '  + str(M))
            if consecutive_fails > 10:
                self.log('Failed to communicate to PWM 10 times. Disabling hardware and software!')
                self.running.set() # Basically this will crash all the electronics and the software.
            else:
                time.sleep(0.1)
                self.hwmap['FailCount'] = self.hwmap['FailCount'] + 1
                self.set_pwm(M, device, channels, fraction, consecutive_fails)

    def turnEverythingOff(self, M):
        # Function which turns off all actuation/hardware.
        for LED in ['LEDA', 'LEDB', 'LEDC', 'LEDD', 'LEDE', 'LEDF', 'LEDG']:
            self.sys_data[M][LED]['ON'] = 0
        self.sys_data[M]['LASER650']['ON'] = 0
        self.sys_data[M]['Pump1']['ON'] = 0
        self.sys_data[M]['Pump2']['ON'] = 0
        self.sys_data[M]['Pump3']['ON'] = 0
        self.sys_data[M]['Pump4']['ON'] = 0
        self.sys_data[M]['Stir']['ON'] = 0
        self.sys_data[M]['Heat']['ON'] = 0
        self.sys_data[M]['UV']['ON'] = 0
        #Sets all DAC Channels to zero!
        self.i2c_com(M, 'DAC', 0, 8, int('00000000', 2), int('00000000', 2), 0)
        self.set_pwm(M, 'PWM', self.hwmap['All'], 0, 0)
        self.set_pwm(M, 'Pumps', self.hwmap['All'], 0, 0)
        self.set_stir(M, 0.0)
        self.set_heater(M, 0.0)
        self.set_uv(M, 0.0)
        self.set_pump(M, 'Pump1', 0.0, '')
        self.set_pump(M, 'Pump2', 0.0, '')
        self.set_pump(M, 'Pump3', 0.0, '')
        self.set_pump(M, 'Pump4', 0.0, '')

# This section of code is responsible for the watchdog circuit. The circuit is implemented
# in hardware on the control computer, and requires the watchdog pin be toggled low->high
# each second, otherwise it will power down all connected devices.
# This section is therefore critical to operation of the device.
class Watchdog(Process):
    def __init__(self, log_q, hwlock, running):
        (Process.__init__(self))
        self.log_q = log_q
        self.hwlock = hwlock
        self.running = running
        self.daemon = True
        with open('sysitems.json', 'r') as f:
            self.hwmap = simplejson.load(f)
    def run(self):
        self.log_q.put(LogPacket("Starting watchdog"))
        with self.hwlock:
            GPIO.setup(self.hwmap['Watchdog']['pin'], GPIO.OUT)
        while not self.running.is_set():
            try:
                with self.hwlock:
                    GPIO.output(self.hwmap['Watchdog']['pin'], GPIO.HIGH)
                time.sleep(0.1)
                with self.hwlock:
                    GPIO.output(self.hwmap['Watchdog']['pin'], GPIO.LOW)
                time.sleep(0.4)
            except:
                self.running.set()
