import functions
import time


# intialization parameters
i2cAddresses = [0x50, 0x51, 0x52, 0x53, 0x54, 0x55]
pins = [13,6,5,11,9,10]
filename = "credentials.json"
bus_number = 1

# full intialization
conn, cursor, bus, bme_calibration = functions.fullInit(filename, pins, bus_number)

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
        functions.reinitI2C(bus)
        time.sleep(1)

        experimentId = 1
    
    functions.pushBMEdata(conn, cursor, bme_calibration, bus)

    # keeps treck if the program is alive
    functions.raspberryAlive(conn, cursor)