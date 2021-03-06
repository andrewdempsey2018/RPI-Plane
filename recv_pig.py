#receiver program that utilizes pigpio

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import pigpio
from subprocess import call #for shutdown

pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]

radio2 = NRF24(GPIO, spidev.SpiDev())

#Start listening on SPI 1 and GPIO17
radio2.begin(1, 17)

radio2.setRetries(15,15)

radio2.setPayloadSize(32)
radio2.setChannel(0x60)
radio2.setDataRate(NRF24.BR_2MBPS)
radio2.setPALevel(NRF24.PA_MIN)

radio2.setAutoAck(True)
radio2.enableDynamicPayloads()
radio2.enableAckPayload()

radio2.openWritingPipe(pipes[0])
radio2.openReadingPipe(1, pipes[1])

radio2.startListening()
radio2.stopListening()

radio2.printDetails()

radio2.startListening()

#setup the servos
pi = pigpio.pi() # Connect to local Pi.

elevatorPulse = 1500
rudderPulse = 1500

elevatorServo = 13
rudderServo = 12

pi.set_servo_pulsewidth(rudderServo, rudderPulse)
pi.set_servo_pulsewidth(elevatorServo, elevatorPulse)

#delay for allowing servos time to move
delay = 0.1

#min servo is 1000
#max servo is 2000
#mid servo is 1500

MAX_MOTOR_SPEED = 2000
MIN_MOTOR_SPEED = 1000

motorSpeed = MIN_MOTOR_SPEED

#Import emum for clean switching of program state
from enum import Enum

class State(Enum):
    MENU = 1
    CALIBRATE = 2
    EXIT = 3
    FLY = 4
    RANGE_TEST = 5

#set the initial state of the program to FLY mode
programState = State.FLY

oncePerLoop = False #this variable is used to initialise some settings once everytime a menu is navigated

motorPin = 16

#to ensure max and min motor value is only set once per caibration
maxSet = False
minSet = False

def getMillis():
    return int(round(time.time() * 1000))

while True:

    pipe = [0]

    while not radio2.available(pipe):
        time.sleep(10000/1000000.0)

    recv_buffer = []
    radio2.read(recv_buffer, radio2.getDynamicPayloadSize())

    print("recv_buffer")
    print(recv_buffer)

    #Change the state of the plane program based on menu input from transmitter

    if(recv_buffer[0] == 102): # 'f' received, go to FLY state
        programState = State.FLY
        oncePerLoop = False

    if(recv_buffer[0] == 99): # 'c' received, go to CALIBRATE state
        programState = State.CALIBRATE
        oncePerLoop = False

    if(recv_buffer[0] == 103): # 'g' received, go to RANGE_TEST state
        programState = State.RANGE_TEST
        oncePerLoop = False

        #RANGE_TEST State
    if(programState == State.RANGE_TEST):
        radio2.write('!')
        print("!")
        time.sleep(3)

    #FLY State
    if(programState == State.FLY):

        motorStartTime = getMillis()

        if not(oncePerLoop):
            print("Plane in FLY mode")
            oncePerLoop = True

        if(recv_buffer[0] == 114): #right
            print('up')
            if(rudderPulse>1000):
                rudderPulse-=50
                pi.set_servo_pulsewidth(rudderServo, rudderPulse)
            time.sleep(delay)

        if(recv_buffer[0] == 108): #left
            print('down')
            if(rudderPulse<2000):
                rudderPulse+=50
                pi.set_servo_pulsewidth(rudderServo, rudderPulse)
            time.sleep(delay)

        if(recv_buffer[0] == 100): #down
            print('left')
            if(elevatorPulse>1000):
                elevatorPulse-=50
                pi.set_servo_pulsewidth(elevatorServo, elevatorPulse)
            time.sleep(delay)

        if(recv_buffer[0] == 117): #up
            print('right')
            if(elevatorPulse<2000):
                elevatorPulse+=50
                pi.set_servo_pulsewidth(elevatorServo, elevatorPulse)
            time.sleep(delay)

        #if(recv_buffer[0] == 97): #a
            #print('a')
            #rudderPulse = 1500
            #pi.set_servo_pulsewidth(rudderServo, rudderPulse)
            #time.sleep(delay)

        if(recv_buffer[0] == 98): #b
            print('a&b')
            elevatorPulse = 1500
            pi.set_servo_pulsewidth(elevatorServo, elevatorPulse)
            rudderPulse = 1500
            pi.set_servo_pulsewidth(rudderServo, rudderPulse)
            time.sleep(delay)

        if(recv_buffer[0] == 111): #received 'o' from transmitter, trigger shutdown
            print('Shutting down plane')
            call("sudo shutdown -h now", shell=True)

        if(recv_buffer[0] == 43): #plus
            print('increase motor speed')
            if(motorSpeed < MAX_MOTOR_SPEED):
                motorSpeed = motorSpeed + 10
                print(motorSpeed)
                #pi.set_servo_pulsewidth(motorPin, motorSpeed)
                time.sleep(delay)

        if(recv_buffer[0] == 45): #minus
            print('decrease motor speed')
            if(motorSpeed > MIN_MOTOR_SPEED):
                motorSpeed = motorSpeed - 10
                print(motorSpeed)
                #pi.set_servo_pulsewidth(motorPin, motorSpeed)
                time.sleep(delay)

        if(recv_buffer[0] == 104): #user has pressed home button, stop motor
            print('Turn off motor quickly')
            if(motorSpeed > MIN_MOTOR_SPEED):
                motorSpeed = motorSpeed - 100
                if(motorSpeed < MIN_MOTOR_SPEED):
                    motorSpeed = MIN_MOTOR_SPEED
                #pi.set_servo_pulsewidth(motorPin, motorSpeed)

        #if(recv_buffer[0] == 49): #user has pressed button 1

        pi.set_servo_pulsewidth(motorPin, motorSpeed)
        
    #CALIBRATE State
    if(programState == State.CALIBRATE):

        if not(oncePerLoop):
            print("Plane in CALIBRATE mode")
            oncePerLoop = True
            maxSet = False
            minSet = False

            #make sure motor is off by default before calibrating
            motorSpeed = MIN_MOTOR_SPEED
            pi.set_servo_pulsewidth(motorPin, motorSpeed)

            #set servos to center
            elevatorPulse = 1500
            pi.set_servo_pulsewidth(elevatorServo, elevatorPulse)
            rudderPulse = 1500
            pi.set_servo_pulsewidth(rudderServo, rudderPulse)
            time.sleep(delay)

        if(recv_buffer[0] == 43): #plus
           if not(maxSet):
               maxSet = True
               print('Max set, plug in lipo')
               motorSpeed = MAX_MOTOR_SPEED
               pi.set_servo_pulsewidth(motorPin, motorSpeed)
               time.sleep(delay)

        if(recv_buffer[0] == 45): #minus
           if not(minSet):
               minSet = True
               print('min set, motor ready')
               motorSpeed = MIN_MOTOR_SPEED
               pi.set_servo_pulsewidth(motorPin, motorSpeed)
               time.sleep(delay)

