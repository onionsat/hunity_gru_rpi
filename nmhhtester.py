import functions
import time
import atexit
import RPi.GPIO as GPIO
from smbus2 import SMBus, i2c_msg


# intialization parameters
i2cAddresses = [0x50, 0x51, 0x52, 0x53, 0x54, 0x55]
pins = [13,6,5,11,9,10]
filename = "credentials.json"
bus_number = 1

# full intialization
conn, cursor, bus, bme_calibration, successBme = functions.fullInit(filename, pins, bus_number)

atexit.register(GPIO.cleanup)
atexit.register(bus.close)

experimentId = 1

while True:
    functions.switchExperiment(conn, cursor, experimentId, pins)

    functions.readExperiment(conn, cursor, experimentId, i2cAddresses, bus)

    functions.writeCommand(conn, cursor, bus, experimentId, i2cAddresses)

    if experimentId < 6:
        time.sleep(1)
        experimentId += 1
    elif experimentId == 6:
        functions.timesyncCommand(bus)

        time.sleep(1)
        #reinitialize I2C
        time.sleep(1)

        experimentId = 1
    
    if successBme:
        functions.pushBMEdata(conn, cursor, bme_calibration, bus)

    # check if database cononection is still alive
    if not conn.is_connected():
        print("Not connected to the database. Trying to reconnect to the database.")
        try:
            conn.reconnect(attempts=1)
            cursor = conn.cursor()
            print("Reconnected to the database.")
        except:
            print("Error reconnecting to the database.")

    # keeps track if the program is alive
    functions.raspberryAlive(conn, cursor)