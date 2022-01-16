import os
import os.path
import json

from strings import *

class Globals:
    def __init__(self):
        # Version
        self.SW_VERSION = 'RS485 Compilation 1.0.3b'
        # Log Level
        self.CONF_LOGLEVEL = 'info' # debug, info, warn

        # 보일러 초기값
        self.INIT_TEMP = 22
        # 환풍기 초기속도 [Speed.LOW, Speed.MEDIUM, Speed.HIGH]
        self.DEFAULT_SPEED = Speed.MEDIUM
        # 조명 / 플러그 갯수
        self.KOCOM_LIGHT_SIZE            = {Room.LIVINGROOM: 3, Room.BEDROOM: 2, Room.ROOM1: 2, Room.ROOM2: 2, Room.KITCHEN: 3}
        self.KOCOM_PLUG_SIZE             = {Room.LIVINGROOM: 2, Room.BEDROOM: 2, Room.ROOM1: 2, Room.ROOM2: 2, Room.KITCHEN: 2}

        # 방 패킷에 따른 방이름 (패킷1: 방이름1, 패킷2: 방이름2 . . .)
        # 월패드에서 장치를 작동하며 방이름(livingroom, bedroom, room1, room2, kitchen 등)을 확인하여 본인의 상황에 맞게 바꾸세요
        # 조명/콘센트와 난방의 방패킷이 달라서 두개로 나뉘어있습니다.
        self.KOCOM_ROOM                  = {'00': Room.LIVINGROOM, '01': Room.BEDROOM, '02': Room.ROOM2, '03': Room.ROOM1, '04': Room.KITCHEN}
        self.KOCOM_ROOM_THERMOSTAT       = {'00': Room.LIVINGROOM, '01': Room.BEDROOM, '02': Room.ROOM1, '03': Room.ROOM2}

        # TIME 변수(초)
        self.SCAN_INTERVAL = 300         # 월패드의 상태값 조회 간격
        self.SCANNING_INTERVAL = 0.8     # 상태값 조회 시 패킷전송 간격

        # KOCOM 코콤 패킷 기본정보
        self.KOCOM_DEVICE                = {'01': Device.WALLPAD, '0e': Device.LIGHT, '36': Device.THERMOSTAT, '3b': Device.PLUG, '44': Device.ELEVATOR, '2c': Device.GAS, '48': Device.FAN}
        self.KOCOM_COMMAND               = {'3a': '조회', '00': '상태', '01': OnOff.ON, '02': OnOff.OFF}
        self.KOCOM_TYPE                  = {'30b': 'send', '30d': 'ack'}
        self.KOCOM_FAN_SPEED             = {'4': Speed.LOW, '8': Speed.MEDIUM, 'c': Speed.HIGH, '0': OnOff.OFF}
        self.KOCOM_DEVICE_REV            = {v: k for k, v in self.KOCOM_DEVICE.items()}
        self.KOCOM_ROOM_REV              = {v: k for k, v in self.KOCOM_ROOM.items()}
        self.KOCOM_ROOM_THERMOSTAT_REV   = {v: k for k, v in self.KOCOM_ROOM_THERMOSTAT.items()}
        self.KOCOM_COMMAND_REV           = {v: k for k, v in self.KOCOM_COMMAND.items()}
        self.KOCOM_TYPE_REV              = {v: k for k, v in self.KOCOM_TYPE.items()}
        self.KOCOM_FAN_SPEED_REV         = {v: k for k, v in self.KOCOM_FAN_SPEED.items()}
        self.KOCOM_ROOM_REV[Device.WALLPAD] = '00'

        # KOCOM TIME 변수
        self.KOCOM_INTERVAL = 100
        self.VENTILATOR_INTERVAL = 150

        # GREX 그렉스 전열교환기 패킷 기본정보
        self.GREX_MODE                   = {'0100': GrexMode.AUTO, '0200': GrexMode.MANUAL, '0300': GrexMode.SLEEP, '0000': OnOff.OFF}
        self.GREX_SPEED                  = {'0101': Speed.LOW, '0202': Speed.MEDIUM, '0303': Speed.HIGH, '0000': OnOff.OFF}

g = Globals()

def conf():
    return g

def readConfiguration():
    option_file = '/data/options.json'
    if os.path.isfile(option_file):
        with open(option_file) as json_file:
            json_data = json.load(json_file)
            conf().INIT_TEMP = json_data[ConfString.ADVANCED][ConfString.INIT_TEMP]
            conf().SCAN_INTERVAL = json_data[ConfString.ADVANCED][ConfString.SCAN_INTERVAL]
            conf().SCANNING_INTERVAL = json_data[ConfString.ADVANCED][ConfString.SCANNING_INTERVAL]
            conf().DEFAULT_SPEED = json_data[ConfString.ADVANCED][ConfString.DEFAULT_SPEED]
            conf().CONF_LOGLEVEL = json_data[ConfString.ADVANCED][ConfString.LOGLEVEL]
            conf().KOCOM_LIGHT_SIZE = {}
            dict_data = json_data[ConfString.KOCOM_LIGHT_SIZE]
            for i in dict_data:
                conf().KOCOM_LIGHT_SIZE[i[ConfString.NAME]] = i[ConfString.NUMBER]
            conf().KOCOM_PLUG_SIZE = {}
            dict_data = json_data[ConfString.KOCOM_PLUG_SIZE]
            for i in dict_data:
                conf().KOCOM_PLUG_SIZE[i[ConfString.NAME]] = i[ConfString.NUMBER]
            num = 0
            conf().KOCOM_ROOM = {}
            list_data = json_data[ConfString.KOCOM_ROOM]
            for i in list_data:
                if num < 10:
                    num_key = "0%d" % (num)
                else:
                    num_key = "%d" % (num)
                conf().KOCOM_ROOM[num_key] = i
                num += 1
            num = 0
            conf().KOCOM_ROOM_THERMOSTAT = {}
            list_data = json_data[ConfString.KOCOM_ROOM_THERMOSTAT]
            for i in list_data:
                if num < 10:
                    num_key = "0%d" % (num)
                else:
                    num_key = "%d" % (num)
                conf().KOCOM_ROOM_THERMOSTAT[num_key] = i
                num += 1
