import json
import time
import mysql.connector
from smbus2 import SMBus, i2c_msg
import RPi.GPIO as GPIO
import bme280

# function to load credentials from json file
def loadCredentials(filename):
    success = False

    while success == False:
        try:
            with open(filename, "r") as credentials_file:
                try:
                    credentials = json.load(credentials_file)
                    success = True
                except:
                    print(f"Error loading credentials from {filename}! Retry in 1 second!")
                    time.sleep(1)
        except:
            print(f"Unable to open {filename}! Retry in 1 second!")
            time.sleep(1)

    return credentials

# function to initialize database connection
def initDB(host, user, password, database):
    success = False

    while success == False:
        try:
            conn = mysql.connector.connect(host=host, user=user, password=password, database=database)
            success = True
        except:
            print("Unable to connect to the database! Retry in 1 second!")
            time.sleep(1)

    cursor = conn.cursor()

    return conn, cursor

# function to initialize I2C bus
def initI2C(bus_number):
    success = False

    while success == False:
        try:
            bus = SMBus(bus_number)
            success = True
        except:
            print(f"Unable to initialize I2C bus {bus_number}! Retry in 1 second!")
            time.sleep(1)

    return bus

# function to initialize GPIOs for enabling experiments
def initEn(pins):
    GPIO.setmode(GPIO.BCM) # uses gpio numbering

    success = False
    
    while success == False:
        try:
            # Setting all gpios to output in the pins list, intial value is LOW
            for i in pins:
                GPIO.setup(i, GPIO.OUT, initial=GPIO.LOW)
            
            success = True
        except:
            print("Error settting up GPIOs! Retry in 1 second!")
            time.sleep(1)


# function to initialize BME280 sensor, it tries 5 times
def initBME280(bus):
    successBme = False
    bme_calibration = None

    for i in range(0, 5):
        try:
            # Initialize BME280 sensor
            bme_calibration = bme280.load_calibration_params(SMBus(1), 0x76)

            successBme = True

            return bme_calibration, successBme # if successful, return the calibration parameters and success status
        except:
            print("Error initializing BME280 sensor! Retry in 1 second!")
            time.sleep(1)
    
    return bme_calibration, successBme # if unsuccessful, return None and success status as False

# function to initialize everything
def fullInit(filename, pins, bus_number):
    # loading credentials
    credentials = loadCredentials(filename)

    # initializing database connection
    conn, cursor = initDB(credentials["db"]["host"], credentials["db"]["user"], credentials["db"]["password"], credentials["db"]["database"])

    # initializing I2C bus
    bus = initI2C(bus_number)

    # initializing Enable GPIOs
    initEn(pins)

    # trying to initializing BME280 sensor
    bme_calibration, successBme = initBME280(bus)

    if successBme:
        print("Initialization fully complete!")
    else:
        print("Everything initialized except BME280 sensor!")

    return conn, cursor, bus, bme_calibration, successBme

# function to switch experimentId on and off
def switchExperiment(conn, cursor, experimentId, pins):
    # try to get switch state from the database
    try:
        onOffQuery = "SELECT switch FROM switch_exp WHERE experimentid = %s"
        cursor.execute(onOffQuery, (experimentId,))
        switchState = cursor.fetchall()
    except:
        print(f"Error querying switch for experiment {experimentId}")
        return # stop the function if there is an error
    
    try:
        if switchState[0][0] == 1:
            GPIO.output(pins[experimentId-1], GPIO.HIGH) # turn on the experiment
        elif switchState[0][0] == 0:
            GPIO.output(pins[experimentId-1], GPIO.LOW) # turn off the experiment
    except:
        print(f"Error switching experiment {experimentId}")

# function to read from experimentId
def readExperiment(conn, cursor, experimentId, i2cAddresses, bus):
    successReading = True

    try:
        readCommand = i2c_msg.read(i2cAddresses[experimentId-1], 16)
        bus.i2c_rdwr(readCommand)
        experimentData = list(readCommand)

        print(f"Succesfully read from experiment {experimentId} data: ")
        for i in range(0, 16):
            print(f"{experimentData[i]:02X}", end="")
        print()
    except:
        print(f"Error reading from experiment {experimentId}")
        successReading = False
    
    # trying to add the result of the successful read operation to the database
    if successReading:
        experimentDataString = ""
        for i in range(0, 16):
            experimentDataString = experimentDataString + f"{experimentData[i]:02x}"

        # insert the data into the experimentdata table
        try:    
            cursor.execute("INSERT INTO experimentdata (experimentid, expdata, success, timestamp) VALUES (%s, %s, %s, current_timestamp())", (experimentId, experimentDataString, 1))
            conn.commit()
        except:
            print("Error pushing successful read to the database")
    # trying to add the result of the unsuccessful read operation to the database
    else:
        try:
            # Insert unsuccessful read into the experiment_data table
            cursor.execute("INSERT INTO experimentdata (experimentid, success, timestamp) VALUES (%s, %s, current_timestamp())", (experimentId, 0))
            conn.commit()
        except:
            print("Error pushing unsuccessful read to the database")
    
    # if reading was unsuccessful, wait for 1 second
    if not successReading:
        time.sleep(1)

def writeCommand(conn, cursor, bus, experimentId, i2cAddresses):
    commandAvailbale = False

    try:
        # get command from writecommands table
        queryWritecommand = "SELECT id, command FROM writecommands WHERE experimentid = %s and sent = 0 ORDER BY sent_to_master ASC LIMIT 1"
        cursor.execute(queryWritecommand, (experimentId,))
        writeCommand = cursor.fetchall()

        # if there is new command, update the sent in the writecommands table to 2
        if len(writeCommand) == 1:
            cursor.execute("UPDATE writecommands SET sent = %s WHERE id = %s", (2, writeCommand[0][0]))
            conn.commit()
        # if there isn't a command stop the function
        else:
            print(f"No command available for experiment {experimentId}")
            return
    except:
        print("Error querying command")
        return
    
    sendingStatus = 2

    # check if the command is valid
    currentCommandString = writeCommand[0][1]
    currentCommand = []
    
    try:
        for i in range(0, 8):
            currentCommand.append(int(currentCommandString[i*2:i*2+2], 16))
    except:
        sendingStatus = -1
    
    if sendingStatus == 2:
        # try to send the command to the device
        try:
            writeCommandi2c = i2c_msg.write(i2cAddresses[experimentId-1], currentCommand)
            bus.i2c_rdwr(writeCommandi2c)

            print(f"Succesfully sent command to experiment {experimentId}: {currentCommandString}")
            sendingStatus = 1
        except:
            print(f"Error sending command to experiment {experimentId}")            
            sendingStatus = -1

            time.sleep(1) # if sending was unsuccessful, wait for 1 second
    
    # update the sent in the writecommands table
    try:
        cursor.execute("UPDATE writecommands SET sent = %s, sent_to_experiment = current_timestamp() WHERE id = %s", (sendingStatus, writeCommand[0][0]))
        conn.commit()
    except:
        print("Error updating writecommands table")

# function to send timesync command
def timesyncCommand(bus):
    timestamp = int(time.time())
    timestampCommandOnlytimestamp = list(timestamp.to_bytes(4, byteorder='little'))

    timestampCommand = [0x54]

    for i in range(0, 4):
        timestampCommand.append(timestampCommandOnlytimestamp[i])

    try:
        timeSyncCommand = i2c_msg.write(0x00, timestampCommand)
        bus.i2c_rdwr(timeSyncCommand)
        print("Timesync command sent successfully")
    except:
        print("Error sending timesync command")

def pushBMEdata(conn, cursor, bme_calibration, bus):
    try:
        bme280_data = bme280.sample(bus, 0x76, bme_calibration)
        temperature = bme280_data.temperature
        pressure = bme280_data.pressure
        humidity = bme280_data.humidity
    except:
        print("Error reading BME280 sensor data")

        return

    print(f"temperature: {temperature} pressure: {pressure} humidity: {humidity}")

    try:
        insertBME280 = "INSERT INTO bmedata (temperature, pressure, humidity, timestamp) VALUES (%s, %s, %s, current_timestamp())"
        cursor.execute(insertBME280, (temperature, pressure, humidity))
        conn.commit()
    except:
        print("Error puting BME280 sensor data into database")

# function to update code time
def raspberryAlive(conn, cursor):
    aliveSQL = "UPDATE raspberry_alive SET unixtimestamp = current_timestamp() WHERE id = 1"

    try:
        cursor.execute(aliveSQL)
        conn.commit()
    except:
        print("Error updating raspberry_alive table")