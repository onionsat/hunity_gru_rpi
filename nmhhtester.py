from smbus2 import SMBus, i2c_msg
import mysql.connector
import time
import json
import RPi.GPIO as GPIO

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
            conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            success = True
        except:
            print("Unable to connect to the database! Retry in 1 second!")
            time.sleep(1)

    cursor = conn.cursor()

    return conn, cursor

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

def initEn(pins):
    success = False

    while success == False:
        try:
            GPIO.setmode(GPIO.BCM) # uses gpio numbering
            success = True
        except:
            print("Error settting up GPIOs! Retry in 1 second!")
            time.sleep(1)
    
        try:
            GPIO.cleanup() # cleaning up gpios
    
            # Setting all gpios to output in the pins list
            for i in pins:
                GPIO.setup(i, GPIO.OUT)
                GPIO.set(GPIO.LOW)
            
            success = True
        except:
            print("Error settting up GPIOs! Retry in 1 second!")
            time.sleep(1)

# makeing a list of gpio pins
gpio_pins = []
# getting credentials from json file
credentials = loadCredentials("credentials_dev.json")
# initializing database connection
conn, cursor = initDB(credentials["db"]["host"], credentials["db"]["user"], credentials["db"]["password"], credentials["db"]["database"])
# initializing I2C bus 1
bus = initI2C(1)


address = 0x50 # start address

while True:
    # read operation
    successReading = True

    try:
        readCommand = i2c_msg.read(address, 16)
        bus.i2c_rdwr(readCommand)
        experimentData = list(readCommand)
        print(f"Succesfully read from experiment {address - 0x50 + 1} data: ")

        for i in range(0, 16):
            print(f"{experimentData[i]:02X}", end="")

        print()
    except:
        print(f"Error reading from experiment {address - 0x50 + 1}")
        successReading = False
    
    # trying to add the result of the read operation to the database
    if successReading:
        experimentDataString = ""

        for i in range(0, 16):
            experimentDataString = experimentDataString + f"{experimentData[i]:02x}"

        try:
            # snsert the data into the experimentdata table
            cursor.execute("INSERT INTO experimentdata (experimentid, expdata, success, timestamp) VALUES (%s, %s, %s, current_timestamp())", (address - 0x50 + 1, experimentDataString, 1))
            conn.commit()
        except:
            print("Error pushing successful read to the database")
    else:
        # reading failed
        try:
            # Insert the data into the experiment_data table
            cursor.execute("INSERT INTO experimentdata (experimentid, success, timestamp) VALUES (%s, %s, current_timestamp())", (address - 0x50 + 1, 0))
            conn.commit()
        except:
            print("Error pushing unsuccessful read to the database")
    
    # if reading was unsuccessful, wait for 1 second
    if not successReading:
        time.sleep(1)
    
    # sending write command is there is any for current experiment
    # checking for command
    getNewCommandSuccess = True
    try:
        # get command from writecommands table
        queryWritecommand = "SELECT id, command FROM writecommands WHERE experimentid = %s and sent = 0 ORDER BY sent_to_master ASC LIMIT 1"
        cursor.execute(queryWritecommand, (address - 0x50 + 1,))
        writeCommand = cursor.fetchall()

        # if there is new command, update the sent in the writecommands table to 2
        if len(writeCommand) == 1:
            cursor.execute("UPDATE writecommands SET sent = %s WHERE id = %s", (2, writeCommand[0][0]))
            conn.commit()
    except:
        print("Error query command")
        getNewCommandSuccess = False

    # if query was succesful
    successWrite = True
    if getNewCommandSuccess:
        # if there is a command, send it
        if len(writeCommand) == 1:
            currentCommandString = writeCommand[0][1]
            currentCommand = []

            # make th command into a list of integers
            vaildCommand = True
            try:
                for i in range(0, 8):
                    currentCommand.append(int(currentCommandString[i*2:i*2+2], 16))
            except:
                vaildCommand = False
                successWrite = False

            # trying to send the command
            if vaildCommand:
                try:
                    # send the command to the device
                    writeCommandi2c = i2c_msg.write(address, currentCommand)
                    bus.i2c_rdwr(writeCommandi2c)

                    print(f"Succesfully sent command to experiment {address - 0x50 + 1}: {currentCommandString}")
                except:
                    print(f"Error sending command to experiment {address - 0x50 + 1}")
                    successWrite = False

            if successWrite == True:
                # if sending succesful, update the sent in the writecommands table to -1
                try:
                    # update sent in the writecommands table, 1 -> send successfully
                    cursor.execute("UPDATE writecommands SET sent = %s, sent_to_experiment = current_timestamp() WHERE id = %s", (1, writeCommand[0][0]))
                    conn.commit()
                except:
                    print("Error update write successful")
            else:
                # if sending failed, update the sent in the writecommands table to -1
                try:
                    # update sent in the writecommands table, -1 -> failed to send
                    cursor.execute("UPDATE writecommands SET sent = %s, sent_to_experiment = current_timestamp() WHERE id = %s", (-1, writeCommand[0][0]))
                    conn.commit()
                except:
                    print("Error update write unsuccessful")
            
    if not successWrite:
        # if write was unsuccessful, wait for 1 second
        time.sleep(1)

    # check if there is any experiment or new cycle
    if address == 0x55:
        # sending generall call timesync command
        timestamp = int(time.time())
        timestampCommand_onlytimestamp = list(timestamp.to_bytes(4, byteorder='little'))

        timestampCommand = [0x54]

        for i in range(0, 4):
            timestampCommand.append(timestampCommand_onlytimestamp[i])

        try:
            timeSyncCommand = i2c_msg.write(0x00, timestampCommand)
            bus.i2c_rdwr(timeSyncCommand)
        except:
            print(f"Timesync command were unsuccessful")
        
        time.sleep(2)

        address = 0x50
    else:
        time.sleep(1)
        address = address + 1
    
    # putting timestamp in raspberry_alive table
    aliveSQL = "UPDATE raspberry_alive SET unixtimestamp = current_timestamp() WHERE id = 1"
    aliveUpdateBool = True
    try:
        cursor.execute(aliveSQL)
        conn.commit()
    except:
        aliveUpdateBool = False
    
    if not aliveUpdateBool:
        print("Raspberry alive timestamp not updated successfully")