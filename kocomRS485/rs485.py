# -*- coding: utf-8 -*-
'''
python -m pip install pyserial
python -m pip install paho-mqtt
'''
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
            server = config.get(ConfString.SOCKET, 'server')
            port = config.get(ConfString.SOCKET, 'port')
            self._socket_device = config.get(ConfString.SOCKET_DEVICE, 'device')
            self._con = self.connect_socket(server, port)
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
                    logger().info('시리얼포트가 열려있지 않습니다.[{}]'.format(port[p]))
            except serial.serialutil.SerialException:
                logger().info('시리얼포트에 연결할 수 없습니다.[{}]'.format(port[p]))
        if opened == 0: return False
        return ser

    def connect_socket(self, server, port):
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
        except Exception as e:
            logger().info('소켓에 연결할 수 없습니다.[{}][{}:{}]'.format(e, server, port))
            return False
        soc.settimeout(None)
        return soc

