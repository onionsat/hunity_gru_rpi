# hunity_gru_rpi

## Description ##

This code emulates the OBC's interfacing with the student experiments on the Hunity 3PQ satellite. The datas read from the experiments(32character, 16byte) are uploaded into a database. The write commands are sent to the experiments from the same database.

### Database ###

The database's name is "hunitytester" and it has 5 tables.

#### experimentdata ####
|Column|Type|Description|
|------|----|-----------|
|id|INT|autoincrementing primarykey|
