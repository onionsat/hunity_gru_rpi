# hunity_gru_rpi

## Description ##

This code emulates the [OBC's interfacing with the student experiments](https://github.com/user-attachments/assets/b3c06d97-d05c-451f-9955-80785f9aa16f) on the Hunity 3PQ satellite. The datas read from the experiments(32character, 16byte) are uploaded into a database. The write commands are sent to the experiments from the same database.

### Database ###

The database's name is "hunitytester" and it has 5 tables.

#### experimentdata ####
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
|experimentid|INT|A number from 1 to 6, which identifies an experiment|
|expdata|VACRHAR(255)|The data read from the experiment, 32character, 16bytes|
|success|TINYINT|1 if read were successful, 0 if read were unsuccessful|
|timestamp|TIMESTAMP|The time of the operation|

#### writecommands ####
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
|experimentid|INT|A number from 1 to 6, which identifies an experiment|
|sent|INT|0 if it is to be sent,2 if raspberry saved it and rpi will try to send it, 1 if sending was successful, -1 id sending wadós unsuccessful|
|command|VARCHAR(255)|The command, 16caharcters, 8bytes|
|sent_to_master|DATETIME|The time when the record were inserted into the table|
|sent_to_experiment|DATETIME|The time when sent were updated|

#### raspberry_alive ####
It has only one record.
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
|unixtiemstamp|TIMESTAMP|It is updated every time at the and of the infinite while loop|

#### bmedata ####
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
|temperature|INT|Temperature|
|pressure|INT|Pressure|
|humidity|INT|Humidity|
|timestamp|TIMESTAMP|Timestamp when data was inserted|

#### switch_exp ####
It has 6 records(for each experiment).
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
|experimentid|INT|A number from 1 to 6, which identifies an experiment|
|switch|TINYINT|if 0 experiment is off, if 1 experiment is on|
|timestamp|TIMESTAMP|The time when it was updated|

#### experiments ####
It has 6 records(for each experiment). Not used in this code.
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey(experimentid)|
|name|VARCHAR(255)|Name of the experiment|
|description|TEXT|Description of the experiment|
|api_keys|LONGTEXT|Api keys for the experiment|
|allowed_ips|LONGTEXT|White list of the IPs for the experiment|
