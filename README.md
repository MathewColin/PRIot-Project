# PRIot-Project
## Project description:
There are two node in this network. One that reads the temperature, humidity and pressure from the BME280 sensor using I2C and sends it a database in AWS Timestream using MQTT.
The other node read data from BHT1750 sensor using I2C and sends it to the same database in AWS Timestream using MQTT.

Both nodes are subscribed to some topics and can receive messages from cloud services. Based on this messages, the nodes can initiate some actions. For example, the second node can turn on or off a fan based on the message received from the cloud.

## Links:
	To project report:
	https://docs.google.com/document/d/15OO-DAZ--Gz76SToKO407URWScyqzWFtg0vZ-OIpW58/edit?usp=sharing
	
	To Grafana dashboard:
	https://g-dbf66bb13f.grafana-workspace.eu-central-1.amazonaws.com/d/de680lnsdaq68b/current-dashboard?orgId=1

	To AWS IoT:
	https://eu-central-1.console.aws.amazon.com/iot/home?region=eu-central-1#/home

	To AWS Timestream:
	https://eu-central-1.console.aws.amazon.com/timestream/home?region=eu-central-1#welcome