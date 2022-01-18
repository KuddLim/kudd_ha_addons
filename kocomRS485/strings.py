from collections import namedtuple

# v.1.2.0

OnOffTup = namedtuple('OnOff', ['ON', 'OFF'])
OnOff = OnOffTup('on', 'off')

DeviceTup = namedtuple('Device', ['WALLPAD', 'LIGHT', 'THERMOSTAT', 'PLUG', 'GAS', 'ELEVATOR', 'FAN'])
Device = DeviceTup('wallpad', 'light', 'thermostat', 'plug', 'gas', 'elevator', 'fan')

SpeedTup = namedtuple('Speed', ['LOW', 'MEDIUM', 'HIGH'])
Speed = SpeedTup('low', 'medium', 'high')

CommandTup = namedtuple('Command', ['QUERY', 'STATUS', 'MASTER_LIGHT_ON', 'MASTER_LIGHT_OFF'])
Command = CommandTup('query', 'status', 'master_light_on', 'master_light_off')

RoomTup = namedtuple('Room', ['LIVINGROOM', 'BEDROOM', 'ROOM1', 'ROOM2', 'KITCHEN', 'MASTER_LIGHT'])
Room = RoomTup('livingroom', 'bedroom', 'room1', 'room2', 'kitchen', 'master_light')

GrexModeTup = namedtuple('GrexMode', ['AUTO', 'MANUAL', 'SLEEP'])
GrexMode = GrexModeTup('auto', 'manual', 'sleep')

HAStringsTup = namedtuple('HAStrings', ['PREFIX','SWITCH','LIGHT','CLIMATE','SENSOR','FAN'])
HAStrings = HAStringsTup('homeassistant', 'switch', 'light', 'climate', 'sensor', 'fan')

ConfStringTup = namedtuple('ConfStringTup', ['CONF_FILE', 'LOGFILE', 'LOGNAME', 'WALLPAD', 'MQTT', 'DEVICE',\
                                             'SERIAL', 'SERIAL_DEVICE', 'SOCKET', 'SOCKET_DEVICE', 'ADVANCED',\
                                             'INIT_TEMP', 'SCAN_INTERVAL', 'SCANNING_INTERVAL', 'DEFAULT_SPEED',\
                                             'LOGLEVEL', 'KOCOM_LIGHT_SIZE', 'KOCOM_PLUG_SIZE', 'KOCOM_ROOM',\
                                             'KOCOM_ROOM_THERMOSTAT', 'NAME', 'NUMBER', 'TYPE'])
ConfString = ConfStringTup('rs485.conf', 'rs485.log', 'RS485', 'Wallpad', 'MQTT', 'RS485',\
                           'Serial', 'SerialDevice', 'Socket', 'SocketDevice', 'Advanced',\
                           'INIT_TEMP', 'SCAN_INTERVAL', 'SCANNING_INTERVAL', 'DEFAULT_SPEED',\
                           'LOGLEVEL', 'KOCOM_LIGHT_SIZE', 'KOCOM_PLUG_SIZE', 'KOCOM_ROOM',\
                           'KOCOM_ROOM_THERMOSTAT', 'name', 'number', 'type')

BooleanStrTup = namedtuple('BooleanStrTup', ['TRUE', 'FALSE'])
BooleanStr = BooleanStrTup('True', 'False')

LogLevelTup = namedtuple('LogLevel', ['INFO', 'DEBUG', 'WARN'])
LogLevel = LogLevelTup('info', 'debug', 'warn')
