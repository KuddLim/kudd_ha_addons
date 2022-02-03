# -*- coding: utf-8 -*-
'''
python -m pip install pyserial
python -m pip install paho-mqtt
'''

# v1.2.0

import os
import os.path
import serial
import socket
import time
import threading
import json
import configparser
import paho.mqtt.client as mqtt
from collections import OrderedDict

# refactored
from strings import *
from settings import *
from utility import *
from grex import *

class rs485:
    def __init__(self):
        self._mqtt_config = {}
        self._port_url = {}
        self._device_list = {}
        self._wp_list = {}
        self.type = None
        self.socketLock = threading.Lock()
        self.connected = True
        self.connecting = False

        if not os.path.exists(configPath()):
            raise "Configuration file not exists"

        config = configparser.ConfigParser()
        config.read(configPath())

        get_conf_wallpad = config.items(ConfString.WALLPAD)
        for item in get_conf_wallpad:
            self._wp_list.setdefault(item[0], item[1])
            logger().info('[CONFIG] {} {} : {}'.format(ConfString.WALLPAD, item[0], item[1]))

        get_conf_mqtt = config.items(ConfString.MQTT)
        for item in get_conf_mqtt:
            self._mqtt_config.setdefault(item[0], item[1])
            logger().info('[CONFIG] {} {} : {}'.format(ConfString.MQTT, item[0], item[1]))

        d_type = config.get(ConfString.LOGNAME, ConfString.TYPE).lower()
        if d_type == 'serial':
            self.type = d_type
            get_conf_serial = config.items(ConfString.SERIAL)
            port_i = 1
            for item in get_conf_serial:
                if item[1] != '':
                    self._port_url.setdefault(port_i, item[1])
                    logger().info('[CONFIG] {} {} : {}'.format(ConfString.SERIAL, item[0], item[1]))
                port_i += 1

            get_conf_serial_device = config.items(ConfString.SERIAL_DEVICE)
            port_i = 1
            for item in get_conf_serial_device:
                if item[1] != '':
                    self._device_list.setdefault(port_i, item[1])
                    logger().info('[CONFIG] {} {} : {}'.format(ConfString.SERIAL_DEVICE, item[0], item[1]))
                port_i += 1
            self._con = self.connect_serial(self._port_url)
        elif d_type == 'socket':
            self.type = d_type
            self.serial_server_address = config.get(ConfString.SOCKET, 'server')
            self.serial_server_port = config.get(ConfString.SOCKET, 'port')
            self._socket_device = config.get(ConfString.SOCKET_DEVICE, 'device')
            self._con = self.connect_socket(self.serial_server_address, self.serial_server_port)
        else:
            logger().info('[CONFIG] SERIAL / SOCKET IS NOT VALID')
            logger().info('[CONFIG] EXIT RS485')
            exit(1)

    @property
    def _wp_light(self):
        return True if self._wp_list[Device.LIGHT] == BooleanStr.TRUE else False

    @property
    def _wp_fan(self):
        return True if self._wp_list[Device.FAN] == BooleanStr.TRUE else False

    @property
    def _wp_thermostat(self):
        return True if self._wp_list[Device.THERMOSTAT] == BooleanStr.TRUE else False

    @property
    def _wp_plug(self):
        return True if self._wp_list[Device.PLUG] == BooleanStr.TRUE else False

    @property
    def _wp_gas(self):
        return True if self._wp_list[Device.GAS] == BooleanStr.TRUE else False

    @property
    def _wp_elevator(self):
        return True if self._wp_list[Device.ELEVATOR] == BooleanStr.TRUE else False

    @property
    def _device(self):
        if self.type == 'serial':
            return self._device_list
        elif self.type == 'socket':
            return self._socket_device

    @property
    def _type(self):
        return self.type

    @property
    def _connect(self):
        return self._con

    @property
    def _mqtt(self):
        return self._mqtt_config

    def reconnect_serial(self):
        self._con = self.connect_serial(self._port_url)

    def connect_serial(self, port):
        ser = {}
        opened = 0
        for p in port:
            try:
                ser[p] = serial.Serial(port[p], 9600, timeout=None)
                if ser[p].isOpen():
                    ser[p].bytesize = 8
                    ser[p].stopbits = 1
                    ser[p].autoOpen = False
                    logger().info('Port {} : {}'.format(p, port[p]))
                    opened += 1
                else:
                    logger().info('Failed to open serial port.[{}]'.format(port[p]))
            except serial.serialutil.SerialException:
                logger().info('Failed to open serial port.[{}]'.format(port[p]))
        if opened == 0: return False
        return ser

    def reconnect_socket(self):
        self._con = self.connect_socket(self.serial_server_address, self.serial_server_port)

    def connect_socket(self, server, port):
        logger().info('connect to... {}:{}'.format(server, port))

        self.socketLock.acquire()
        self.connecting = True
        self.socketLock.release()

        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
        except socket.error as e:
            logger().info('Connection via socket failed.[{}][{}:{}]'.format(e, server, port))
            self.socketLock.acquire()
            self.connected = False
            self.connecting = False
            self.socketLock.release()
            return False
        except Exception as e:
            logger().info('connection failed with unkonwo exception : {}'.format(e))

        logger().info('set socket timeout to 2 hours')
        soc.settimeout(7200)

        self.socketLock.acquire()
        self.connected = True
        self.connecting = False
        self.socketLock.release()

        return soc

    def read(self):
        connected = False
        connecting = False

        self.socketLock.acquire()
        connected = self.connected
        connecting = self.connecting
        self.socketLock.release()

        if self._connect == False or not connected or connecting:
            return None

        ret = None
        try:
            fail = False
            if self.type == 'serial':
                if self._con.readable():
                    ret = self._con.read()
                else:
                    ret = None
                # TODO: serial 통신 fail 조건.
                return ret
            elif self.type == 'socket':
                # TODO: 여러 바이트 읽도록 변경 필요. (코콤 시리얼 통신의 경우 메시지가 21바이트 고정길이이다)
                ret =  self._con.recv(1)
        except socket.error as e:
            logger().info('orderly shutdown on server end : {}'.format(e))
        except Exception as e:
            logger().info('[Serial Read] Connection Error : {}'.format(e))
            fail = True

        if fail:
            self.socketLock.acquire()
            self.connected = False
            self.socketLock.release()
            self._con.close()
            return None
        else:
            return ret

    def write(self, data):
        if data == False:
            return

        connected = False

        self.socketLock.acquire()
        connected = self.connected
        connecting = self.connecting
        self.socketLock.release()

        self.tick = time.time()
        if self._con == False or not connected or connecting:
            return

        self.socketLock.acquire()

        res = 0
        try:
            if self.type == 'serial':
                res = self._con.write(bytearray.fromhex((data)))
            elif self.type == 'socket':
                res = self._con.send(bytearray.fromhex((data)))
        except socket.timeout as e:
            logger().info('recv timed out, retry later')
            return
        except Exception as e:
            logger().info('[Serial Write] Connection Error : {}'.format(e))
            res = 0

        # TODO: serial 통신일때 조건이 무엇인지.
        if res == 0:
            self.connected = False
            self._con.close()

        self.socketLock.release()

    def is_connected(self):
        connected = False
        self.socketLock.acquire()
        connected = self.connected
        self.socketLock.release()

        return connected
