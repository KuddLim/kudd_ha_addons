from rs485 import *

class Kocom(rs485):
    def __init__(self, client, name, device, packet_len):
        self.client = client
        self._name = name
        self.connected = True

        self.ha_registry = False
        self.kocom_scan = True
        self.scan_packet_buf = []

        self.tick = time.time()
        self.wp_list = {}
        self.wp_light = self.client._wp_light
        self.wp_fan = self.client._wp_fan
        self.wp_plug = self.client._wp_plug
        self.wp_gas = self.client._wp_gas
        self.wp_elevator = self.client._wp_elevator
        self.wp_thermostat = self.client._wp_thermostat
        for d_name in conf().KOCOM_DEVICE.values():
            if d_name == Device.ELEVATOR or d_name == Device.GAS:
                self.wp_list[d_name] = {}
                self.wp_list[d_name][Device.WALLPAD] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                self.wp_list[d_name][Device.WALLPAD][d_name] = {'state': OnOff.OFF, 'set': OnOff.OFF, 'last': 'state', 'count': 0}
            elif d_name == Device.FAN:
                self.wp_list[d_name] = {}
                self.wp_list[d_name][Device.WALLPAD] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                self.wp_list[d_name][Device.WALLPAD]['mode'] = {'state': OnOff.OFF, 'set': OnOff.OFF, 'last': 'state', 'count': 0}
                self.wp_list[d_name][Device.WALLPAD]['speed'] = {'state': OnOff.OFF, 'set': OnOff.OFF, 'last': 'state', 'count': 0}
            elif d_name == Device.THERMOSTAT:
                self.wp_list[d_name] = {}
                for r_name in conf().KOCOM_ROOM_THERMOSTAT.values():
                    self.wp_list[d_name][r_name] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                    self.wp_list[d_name][r_name]['mode'] = {'state': OnOff.OFF, 'set': OnOff.OFF, 'last': 'state', 'count': 0}
                    self.wp_list[d_name][r_name]['current_temp'] = {'state': 0, 'set': 0, 'last': 'state', 'count': 0}
                    self.wp_list[d_name][r_name]['target_temp'] = {'state': conf().INIT_TEMP, 'set': conf().INIT_TEMP, 'last': 'state', 'count': 0}
            elif d_name == Device.LIGHT or d_name == Device.PLUG:
                self.wp_list[d_name] = {}
                for r_name in conf().KOCOM_ROOM.values():
                    self.wp_list[d_name][r_name] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                    if d_name == Device.LIGHT:
                        for i in range(0, conf().KOCOM_LIGHT_SIZE[r_name] + 1):
                            self.wp_list[d_name][r_name][d_name + str(i)] = {'state': OnOff.OFF, 'set': OnOff.OFF, 'last': 'state', 'count': 0}
                    if d_name == Device.PLUG:
                        for i in range(0, conf().KOCOM_PLUG_SIZE[r_name] + 1):
                            self.wp_list[d_name][r_name][d_name + str(i)] = {'state': OnOff.ON, 'set': OnOff.ON, 'last': 'state', 'count': 0}

        self.d_type = client._type
        if self.d_type == "serial":
            self.d_serial = client._connect[device]
        elif self.d_type == "socket":
            self.d_serial = client._connect
        self.d_mqtt = self.connect_mqtt(self.client._mqtt, name)

        self._t1 = threading.Thread(target=self.get_serial, args=(name, packet_len))
        self._t1.start()
        self._t2 = threading.Thread(target=self.scan_list)
        self._t2.start()

    def connection_lost(self):
        self._t1.join()
        self._t2.join()
        if not self.connected:
            logger.debug('[ERROR] 서버 연결이 끊어져 kocom 클래스를 종료합니다.')
            return False

    def read(self):
        if self.client._connect == False:
            return ''
        try:
            if self.d_type == 'serial':
                if self.d_serial.readable():
                    return self.d_serial.read()
                else:
                    return ''
            elif self.d_type == 'socket':
                return self.d_serial.recv(1)
        except:
            logging.info('[Serial Read] Connection Error')

    def write(self, data):
        if data == False:
            return
        self.tick = time.time()
        if self.client._connect == False:
            return
        try:
            if self.d_type == 'serial':
                return self.d_serial.write(bytearray.fromhex((data)))
            elif self.d_type == 'socket':
                return self.d_serial.send(bytearray.fromhex((data)))
        except:
            logging.info('[Serial Write] Connection Error')

    def connect_mqtt(self, server, name):
        mqtt_client = mqtt.Client()
        mqtt_client.on_message = self.on_message
        #mqtt_client.on_publish = self.on_publish
        mqtt_client.on_subscribe = self.on_subscribe
        mqtt_client.on_connect = self.on_connect

        if server['anonymous'] != BooleanStr.TRUE:
            if server['server'] == '' or server['username'] == '' or server['password'] == '':
                logger.info('{} 설정을 확인하세요. Server[{}] ID[{}] PW[{}] Device[{}]'.format(ConfString.MQTT, server['server'], server['username'], server['password'], name))
                return False
            mqtt_client.username_pw_set(username=server['username'], password=server['password'])
            logger.debug('{} STATUS. Server[{}] ID[{}] PW[{}] Device[{}]'.format(ConfString.MQTT, server['server'], server['username'], server['password'], name))
        else:
            logger.debug('{} STATUS. Server[{}] Device[{}]'.format(ConfString.MQTT, server['server'], name))

        mqtt_client.connect(server['server'], 1883, 60)
        mqtt_client.loop_start()
        return mqtt_client

    def on_message(self, client, obj, msg):
        _topic = msg.topic.split('/')
        _payload = msg.payload.decode()

        if 'config' in _topic and _topic[0] == 'rs485' and _topic[1] == 'bridge' and _topic[2] == 'config':
            if _topic[3] == 'log_level':
                if _payload == "info": logger.setLevel(logging.INFO)
                if _payload == "debug": logger.setLevel(logging.DEBUG)
                if _payload == "warn": logger.setLevel(logging.WARN)
                logger.info('[From HA]Set Loglevel to {}'.format(_payload))
                return
            elif _topic[3] == 'restart':
                self.homeassistant_device_discovery()
                logger.info('[From HA]HomeAssistant Restart')
                return
            elif _topic[3] == 'remove':
                self.homeassistant_device_discovery(remove=True)
                logger.info('[From HA]HomeAssistant Remove')
                return
            elif _topic[3] == 'scan':
                for d_name in conf().KOCOM_DEVICE.values():
                    if d_name == Device.ELEVATOR or d_name == Device.GAS:
                        self.wp_list[d_name][Device.WALLPAD] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                    elif d_name == Device.FAN:
                        self.wp_list[d_name][Device.WALLPAD] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                    elif d_name == Device.THERMOSTAT:
                        for r_name in conf().KOCOM_ROOM_THERMOSTAT.values():
                            self.wp_list[d_name][r_name] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                    elif d_name == Device.LIGHT or d_name == Device.PLUG:
                        for r_name in conf().KOCOM_ROOM.values():
                            self.wp_list[d_name][r_name] = {'scan': {'tick': 0, 'count': 0, 'last': 0}}
                logger.info('[From HA]HomeAssistant Scan')
                return
            elif _topic[3] == 'packet':
                self.packet_parsing(_payload.lower(), name='HA')
            elif _topic[3] == 'check_sum':
                chksum = self.check_sum(_payload.lower())
                logger.info('[From HA]{} = {}({})'.format(_payload, chksum[0], chksum[1]))
        elif not self.kocom_scan:
            self.parse_message(_topic, _payload)
            return
        logger.info("Message: {} = {}".format(msg.topic, _payload))

        if self.ha_registry != False and self.ha_registry == msg.topic and self.kocom_scan:
            self.kocom_scan = False

    def parse_message(self, topic, payload):
        device = topic[1]
        command = topic[3]
        if device == HAStrings.LIGHT or device == HAStrings.SWITCH:
            room_device = topic[2].split('_')
            room = room_device[0]
            sub_device = room_device[1]
            if sub_device.find(Device.LIGHT) != -1:
                device = Device.LIGHT
            if sub_device.find(Device.PLUG) != -1:
                device = Device.PLUG
            if sub_device.find(Device.ELEVATOR) != -1:
                device = Device.ELEVATOR
            if sub_device.find(Device.GAS) != -1:
                device = Device.GAS
            try:
                if device == Device.GAS:
                    if payload == OnOff.ON:
                        payload = OnOff.OFF
                        logger.info('[From HA]Error GAS Cannot Set to ON')
                    else:
                        self.wp_list[device][room][sub_device][command] = payload
                        self.wp_list[device][room][sub_device]['last'] = command
                elif device == Device.ELEVATOR:
                    if payload == OnOff.OFF:
                        self.wp_list[device][room][sub_device][command] = payload
                        self.wp_list[device][room][sub_device]['last'] = 'state'
                        self.send_to_homeassistant(device, Device.WALLPAD, payload)
                    else:
                        self.wp_list[device][room][sub_device][command] = payload
                        self.wp_list[device][room][sub_device]['last'] = command
                else:
                    self.wp_list[device][room][sub_device][command] = payload
                    self.wp_list[device][room][sub_device]['last'] = command
                logger.info('[From HA]{}/{}/{}/{} = {}'.format(device, room, sub_device, command, payload))
            except:
                logger.info('[From HA]Error {} = {}'.format(topic, payload))
        elif device == HAStrings.CLIMATE:
            device = Device.THERMOSTAT
            room = topic[2]
            try:
                if command != 'mode':
                    self.wp_list[device][room]['target_temp']['set'] = int(float(payload))
                    self.wp_list[device][room]['mode']['set'] = 'heat'
                    self.wp_list[device][room]['target_temp']['last'] = 'set'
                    self.wp_list[device][room]['mode']['last'] = 'set'
                elif command == 'mode':
                    self.wp_list[device][room]['mode']['set'] = payload
                    self.wp_list[device][room]['mode']['last'] = 'set'
                ha_payload = {
                    'mode': self.wp_list[device][room]['mode']['set'],
                    'target_temp': self.wp_list[device][room]['target_temp']['set'],
                    'current_temp': self.wp_list[device][room]['current_temp']['state']
                }
                logger.info('[From HA]{}/{}/set = [mode={}, target_temp={}]'.format(device, room, self.wp_list[device][room]['mode']['set'], self.wp_list[device][room]['target_temp']['set']))
                self.send_to_homeassistant(device, room, ha_payload)
            except:
                logger.info('[From HA]Error {} = {}'.format(topic, payload))
        elif device == HAStrings.FAN:
            device = Device.FAN
            room = topic[2]
            try:
                if command != 'mode':
                    self.wp_list[device][room]['speed']['set'] = payload
                    self.wp_list[device][room]['mode']['set'] = OnOff.ON
                elif command == 'mode':
                    self.wp_list[device][room]['speed']['set'] = conf().DEFAULT_SPEED if payload == OnOff.ON else OnOff.OFF
                    self.wp_list[device][room]['mode']['set'] = payload
                self.wp_list[device][room]['speed']['last'] = 'set'
                self.wp_list[device][room]['mode']['last'] = 'set'
                ha_payload = {
                    'mode': self.wp_list[device][room]['mode']['set'],
                    'speed': self.wp_list[device][room]['speed']['set']
                }
                logger.info('[From HA]{}/{}/set = [mode={}, speed={}]'.format(device, room, self.wp_list[device][room]['mode']['set'], self.wp_list[device][room]['speed']['set']))
                self.send_to_homeassistant(device, room, ha_payload)
            except:
                logger.info('[From HA]Error {} = {}'.format(topic, payload))

    def on_publish(self, client, obj, mid):
        logger.info("Publish: {}".format(str(mid)))

    def on_subscribe(self, client, obj, mid, granted_qos):
        logger.info("Subscribed: {} {}".format(str(mid),str(granted_qos)))

    def on_connect(self, client, userdata, flags, rc):
        if int(rc) == 0:
            logger.info("[MQTT] connected OK")
            self.homeassistant_device_discovery(initial=True)
        elif int(rc) == 1:
            logger.info("[MQTT] 1: Connection refused – incorrect protocol version")
        elif int(rc) == 2:
            logger.info("[MQTT] 2: Connection refused – invalid client identifier")
        elif int(rc) == 3:
            logger.info("[MQTT] 3: Connection refused – server unavailable")
        elif int(rc) == 4:
            logger.info("[MQTT] 4: Connection refused – bad username or password")
        elif int(rc) == 5:
            logger.info("[MQTT] 5: Connection refused – not authorised")
        else:
            logger.info("[MQTT] {} : Connection refused".format(rc))

    def homeassistant_device_discovery(self, initial=False, remove=False):
        subscribe_list = []
        subscribe_list.append(('rs485/bridge/#', 0))
        publish_list = []

        self.ha_registry = False
        self.kocom_scan = True

        if self.wp_elevator:
            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad', Device.ELEVATOR)
            ha_payload = {
                'name': '{}_{}_{}'.format(self._name, 'wallpad', Device.ELEVATOR),
                'cmd_t': '{}/{}/{}_{}/set'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad', Device.ELEVATOR),
                'stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad'),
                'val_tpl': '{{ value_json.' + Device.ELEVATOR + ' }}',
                'ic': 'mdi:elevator',
                'pl_on': OnOff.ON,
                'pl_off': OnOff.OFF,
                'uniq_id': '{}_{}_{}'.format(self._name, 'wallpad', Device.ELEVATOR),
                'device': {
                    'name': 'Kocom {}'.format('wallpad'),
                    'ids': 'kocom_{}'.format('wallpad'),
                    'mf': 'KOCOM',
                    'mdl': 'Wallpad',
                    'sw': conf().SW_VERSION
                }
            }
            subscribe_list.append((ha_topic, 0))
            subscribe_list.append((ha_payload['cmd_t'], 0))
            #subscribe_list.append((ha_payload['stat_t'], 0))
            if remove:
                publish_list.append({ha_topic : ''})
            else:
                publish_list.append({ha_topic : json.dumps(ha_payload)})
        if self.wp_gas:
            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad', Device.GAS)
            ha_payload = {
                'name': '{}_{}_{}'.format(self._name, 'wallpad', Device.GAS),
                'cmd_t': '{}/{}/{}_{}/set'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad', Device.GAS),
                'stat_t': '{}/{}/{}_{}/state'.format(HAStrings.PREFIX, HAStrings.SWITCH, 'wallpad', Device.GAS),
                'val_tpl': '{{ value_json.' + Device.GAS + ' }}',
                'ic': 'mdi:gas-cylinder',
                'pl_on': OnOff.ON,
                'pl_off': OnOff.OFF,
                'uniq_id': '{}_{}_{}'.format(self._name, 'wallpad', Device.GAS),
                'device': {
                    'name': 'Kocom {}'.format('wallpad'),
                    'ids': 'kocom_{}'.format('wallpad'),
                    'mf': 'KOCOM',
                    'mdl': 'Wallpad',
                    'sw': conf().SW_VERSION
                }
            }
            subscribe_list.append((ha_topic, 0))
            subscribe_list.append((ha_payload['cmd_t'], 0))
            #subscribe_list.append((ha_payload['stat_t'], 0))
            if remove:
                publish_list.append({ha_topic : ''})
            else:
                publish_list.append({ha_topic : json.dumps(ha_payload)})

            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'wallpad', Device.GAS)
            ha_payload = {
                'name': '{}_{}_{}'.format(self._name, 'wallpad', Device.GAS),
                'stat_t': '{}/{}/{}_{}/state'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'wallpad', Device.GAS),
                'val_tpl': '{{ value_json.' + Device.GAS + ' }}',
                'ic': 'mdi:gas-cylinder',
                'uniq_id': '{}_{}_{}'.format(self._name, 'wallpad', Device.GAS),
                'device': {
                    'name': 'Kocom {}'.format('wallpad'),
                    'ids': 'kocom_{}'.format('wallpad'),
                    'mf': 'KOCOM',
                    'mdl': 'Wallpad',
                    'sw': conf().SW_VERSION
                }
            }
            subscribe_list.append((ha_topic, 0))
            #subscribe_list.append((ha_payload['stat_t'], 0))
            publish_list.append({ha_topic : json.dumps(ha_payload)})
        if self.wp_fan:
            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.FAN, 'wallpad', Device.FAN)
            ha_payload = {
                'name': '{}_{}_{}'.format(self._name, 'wallpad', Device.FAN),
                'cmd_t': '{}/{}/{}/mode'.format(HAStrings.PREFIX, HAStrings.FAN, 'wallpad'),
                'stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.FAN, 'wallpad'),
                'spd_cmd_t': '{}/{}/{}/speed'.format(HAStrings.PREFIX, HAStrings.FAN, 'wallpad'),
                'spd_stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.FAN, 'wallpad'),
                'stat_val_tpl': '{{ value_json.mode }}',
                'spd_val_tpl': '{{ value_json.speed }}',
                'pl_on': OnOff.ON,
                'pl_off': OnOff.OFF,
                'spds': [Speed.LOW, Speed.MEDIUM, Speed.HIGH, OnOff.OFF],
                'uniq_id': '{}_{}_{}'.format(self._name, 'wallpad', Device.FAN),
                'device': {
                    'name': 'Kocom {}'.format('wallpad'),
                    'ids': 'kocom_{}'.format('wallpad'),
                    'mf': 'KOCOM',
                    'mdl': 'Wallpad',
                    'sw': conf().SW_VERSION
                }
            }
            subscribe_list.append((ha_topic, 0))
            subscribe_list.append((ha_payload['cmd_t'], 0))
            #subscribe_list.append((ha_payload['stat_t'], 0))
            subscribe_list.append((ha_payload['spd_cmd_t'], 0))
            if remove:
                publish_list.append({ha_topic : ''})
            else:
                publish_list.append({ha_topic : json.dumps(ha_payload)})
        if self.wp_light:
            for room, r_value in self.wp_list[Device.LIGHT].items():
                if type(r_value) == dict:
                    for sub_device, d_value in r_value.items():
                        if type(d_value) == dict:
                            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.LIGHT, room, sub_device)
                            ha_payload = {
                                'name': '{}_{}_{}'.format(self._name, room, sub_device),
                                'cmd_t': '{}/{}/{}_{}/set'.format(HAStrings.PREFIX, HAStrings.LIGHT, room, sub_device),
                                'stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.LIGHT, room),
                                'val_tpl': '{{ value_json.' + str(sub_device) + ' }}',
                                'pl_on': OnOff.ON,
                                'pl_off': OnOff.OFF,
                                'uniq_id': '{}_{}_{}'.format(self._name, room, sub_device),
                                'device': {
                                    'name': 'Kocom {}'.format(room),
                                    'ids': 'kocom_{}'.format(room),
                                    'mf': 'KOCOM',
                                    'mdl': 'Wallpad',
                                    'sw': conf().SW_VERSION
                                }
                            }
                            subscribe_list.append((ha_topic, 0))
                            subscribe_list.append((ha_payload['cmd_t'], 0))
                            #subscribe_list.append((ha_payload['stat_t'], 0))
                            if remove:
                                publish_list.append({ha_topic : ''})
                            else:
                                publish_list.append({ha_topic : json.dumps(ha_payload)})
        if self.wp_plug:
            for room, r_value in self.wp_list[Device.PLUG].items():
                if type(r_value) == dict:
                    for sub_device, d_value in r_value.items():
                        if type(d_value) == dict:
                            ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.SWITCH, room, sub_device)
                            ha_payload = {
                                'name': '{}_{}_{}'.format(self._name, room, sub_device),
                                'cmd_t': '{}/{}/{}_{}/set'.format(HAStrings.PREFIX, HAStrings.SWITCH, room, sub_device),
                                'stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.SWITCH, room),
                                'val_tpl': '{{ value_json.' + str(sub_device) + ' }}',
                                'ic': 'mdi:power-socket-eu',
                                'pl_on': OnOff.ON,
                                'pl_off': OnOff.OFF,
                                'uniq_id': '{}_{}_{}'.format(self._name, room, sub_device),
                                'device': {
                                    'name': 'Kocom {}'.format(room),
                                    'ids': 'kocom_{}'.format(room),
                                    'mf': 'KOCOM',
                                    'mdl': 'Wallpad',
                                    'sw': conf().SW_VERSION
                                }
                            }
                            subscribe_list.append((ha_topic, 0))
                            subscribe_list.append((ha_payload['cmd_t'], 0))
                            #subscribe_list.append((ha_payload['stat_t'], 0))
                            if remove:
                                publish_list.append({ha_topic : ''})
                            else:
                                publish_list.append({ha_topic : json.dumps(ha_payload)})
        if self.wp_thermostat:
            for room, r_list in self.wp_list[Device.THERMOSTAT].items():
                if type(r_list) == dict:
                    ha_topic = '{}/{}/{}/config'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room)
                    ha_payload = {
                        'name': '{}_{}_{}'.format(self._name, room, Device.THERMOSTAT),
                        'mode_cmd_t': '{}/{}/{}/mode'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room),
                        'mode_stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room),
                        'mode_stat_tpl': '{{ value_json.mode }}',
                        'temp_cmd_t': '{}/{}/{}/target_temp'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room),
                        'temp_stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room),
                        'temp_stat_tpl': '{{ value_json.target_temp }}',
                        'curr_temp_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.CLIMATE, room),
                        'curr_temp_tpl': '{{ value_json.current_temp }}',
                        'min_temp': 5,
                        'max_temp': 40,
                        'temp_step': 1,
                        'modes': [OnOff.OFF, 'heat', 'fan_only'],
                        'uniq_id': '{}_{}_{}'.format(self._name, room, Device.THERMOSTAT),
                        'device': {
                            'name': 'Kocom {}'.format(room),
                            'ids': 'kocom_{}'.format(room),
                            'mf': 'KOCOM',
                            'mdl': 'Wallpad',
                            'sw': conf().SW_VERSION
                        }
                    }
                    subscribe_list.append((ha_topic, 0))
                    subscribe_list.append((ha_payload['mode_cmd_t'], 0))
                    #subscribe_list.append((ha_payload['mode_stat_t'], 0))
                    subscribe_list.append((ha_payload['temp_cmd_t'], 0))
                    #subscribe_list.append((ha_payload['temp_stat_t'], 0))
                    if remove:
                        publish_list.append({ha_topic : ''})
                    else:
                        publish_list.append({ha_topic : json.dumps(ha_payload)})

        if initial:
            self.d_mqtt.subscribe(subscribe_list)
        for ha in publish_list:
            for topic, payload in ha.items():
                self.d_mqtt.publish(topic, payload)
        self.ha_registry = ha_topic

    def send_to_homeassistant(self, device, room, value):
        v_value = json.dumps(value)
        if device == Device.LIGHT:
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.LIGHT, room), v_value)
            logger.info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.LIGHT, room, v_value))
        elif device == Device.PLUG:
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.SWITCH, room), v_value)
            logger.info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.SWITCH, room, v_value))
        elif device == Device.THERMOSTAT:
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.CLIMATE, room), v_value)
            logger.info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.CLIMATE, room, v_value))
        elif device == Device.ELEVATOR:
            v_value = json.dumps({device: value})
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.SWITCH, room), v_value)
            logger.info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.SWITCH, room, v_value))
        elif device == Device.GAS:
            v_value = json.dumps({device: value})
            self.d_mqtt.publish("{}/{}/{}_{}/state".format(HAStrings.PREFIX, HAStrings.SENSOR, room, Device.GAS), v_value)
            logger.info("[To HA]{}/{}/{}_{}/state = {}".format(HAStrings.PREFIX, HAStrings.SENSOR, room, Device.GAS, v_value))
            self.d_mqtt.publish("{}/{}/{}_{}/state".format(HAStrings.PREFIX, HAStrings.SWITCH, room, Device.GAS), v_value)
            logger.info("[To HA]{}/{}/{}_{}/state = {}".format(HAStrings.PREFIX, HAStrings.SWITCH, room, Device.GAS, v_value))
        elif device == Device.FAN:
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.FAN, room), v_value)
            logger.info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.FAN, room, v_value))

    def get_serial(self, packet_name, packet_len):
        packet = ''
        start_flag = False
        while True:
            row_data = self.read()
            hex_d = row_data.hex()
            start_hex = ''
            if packet_name == 'kocom':  start_hex = 'aa'
            elif packet_name == 'grex_ventilator':  start_hex = 'd1'
            elif packet_name == 'grex_controller':  start_hex = 'd0'
            if hex_d == start_hex:
                start_flag = True
            if start_flag:
                packet += hex_d

            if len(packet) >= packet_len:
                chksum = self.check_sum(packet)
                if chksum[0]:
                    self.tick = time.time()
                    logger.debug("[From {}]{}".format(packet_name, packet))
                    self.packet_parsing(packet)
                packet = ''
                start_flag = False
            if not self.connected:
                logger.debug('[ERROR] 서버 연결이 끊어져 get_serial Thread를 종료합니다.')
                break

    def check_sum(self, packet):
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        chk_sum = '{0:02x}'.format((sum_packet + 1 + v_sum) % 256)
        orgin_sum = packet[36:38] if len(packet) >= 38 else ''
        return (True, chk_sum) if chk_sum == orgin_sum else (False, chk_sum)

    def parse_packet(self, packet):
        p = {}
        try:
            p['header'] = packet[:4]
            p['type'] = packet[4:7]
            p['order'] = packet[7:8]
            if conf().KOCOM_TYPE.get(p['type']) == 'send':
                p['dst_device'] = packet[10:12]
                p['dst_room'] = packet[12:14]
                p['src_device'] = packet[14:16]
                p['src_room'] = packet[16:18]
            elif conf().KOCOM_TYPE.get(p['type']) == 'ack':
                p['src_device'] = packet[10:12]
                p['src_room'] = packet[12:14]
                p['dst_device'] = packet[14:16]
                p['dst_room'] = packet[16:18]
            p['command'] = packet[18:20]
            p['value'] = packet[20:36]
            p['checksum'] = packet[36:38]
            p['tail'] = packet[38:42]
            return p
        except:
            return False

    def value_packet(self, p):
        v = {}
        if not p:
            return False
        try:
            v['type'] = conf().KOCOM_TYPE.get(p['type'])
            v['command'] = conf().KOCOM_COMMAND.get(p['command'])
            v['src_device'] = conf().KOCOM_DEVICE.get(p['src_device'])
            v['src_room'] = conf().KOCOM_ROOM.get(p['src_room']) if v['src_device'] != Device.THERMOSTAT else conf().KOCOM_ROOM_THERMOSTAT.get(p['src_room'])
            v['dst_device'] = conf().KOCOM_DEVICE.get(p['dst_device'])
            v['dst_room'] = conf().KOCOM_ROOM.get(p['dst_room']) if v['src_device'] != Device.THERMOSTAT else conf().KOCOM_ROOM_THERMOSTAT.get(p['dst_room'])
            v['value'] = p['value']
            if v['src_device'] == Device.FAN:
                v['value'] = self.parse_fan(p['value'])
            elif v['src_device'] == Device.LIGHT or v['src_device'] == Device.PLUG:
                v['value'] = self.parse_switch(v['src_device'], v['src_room'], p['value'])
            elif v['src_device'] == Device.THERMOSTAT:
                v['value'] = self.parse_thermostat(p['value'], self.wp_list[v['src_device']][v['src_room']]['target_temp']['state'])
            elif v['src_device'] == Device.WALLPAD and v['dst_device'] == Device.ELEVATOR:
                v['value'] = OnOff.OFF
            elif v['src_device'] == Device.GAS:
                v['value'] = v['command']
            return v
        except:
            return False

    def packet_parsing(self, packet, name='kocom', from_to='From'):
        p = self.parse_packet(packet)
        v = self.value_packet(p)

        try:
            if v['command'] == "조회" and v['src_device'] == Device.WALLPAD:
                if name == 'HA':
                    self.write(self.make_packet(v['dst_device'], v['dst_room'], '조회', '', ''))
                logger.debug('[{} {}]{}({}) {}({}) -> {}({})'.format(from_to, name, v['type'], v['command'], v['src_device'], v['src_room'], v['dst_device'], v['dst_room']))
            else:
                logger.debug('[{} {}]{}({}) {}({}) -> {}({}) = {}'.format(from_to, name, v['type'], v['command'], v['src_device'], v['src_room'], v['dst_device'], v['dst_room'], v['value']))

            if (v['type'] == 'ack' and v['dst_device'] == Device.WALLPAD) or (v['type'] == 'send' and v['dst_device'] == Device.ELEVATOR):
                if v['type'] == 'send' and v['dst_device'] == Device.ELEVATOR:
                    self.set_list(v['dst_device'], Device.WALLPAD, v['value'])
                    self.send_to_homeassistant(v['dst_device'], Device.WALLPAD, v['value'])
                elif v['src_device'] == Device.FAN or v['src_device'] == Device.GAS:
                    self.set_list(v['src_device'], Device.WALLPAD, v['value'])
                    self.send_to_homeassistant(v['src_device'], Device.WALLPAD, v['value'])
                elif v['src_device'] == Device.THERMOSTAT or v['src_device'] == Device.LIGHT or v['src_device'] == Device.PLUG:
                    self.set_list(v['src_device'], v['src_room'], v['value'])
                    self.send_to_homeassistant(v['src_device'], v['src_room'], v['value'])
        except:
            logger.info('[{} {}]Error {}'.format(from_to, name, packet))

    def set_list(self, device, room, value, name='kocom'):
        try:
            logger.info('[From {}]{}/{}/state = {}'.format(name, device, room, value))
            if 'scan' in self.wp_list[device][room] and type(self.wp_list[device][room]['scan']) == dict:
                self.wp_list[device][room]['scan']['tick'] = time.time()
                self.wp_list[device][room]['scan']['count'] = 0
                self.wp_list[device][room]['scan']['last'] = 0
            if device == Device.GAS or device == Device.ELEVATOR:
                self.wp_list[device][room][device]['state'] = value
                self.wp_list[device][room][device]['last'] = 'state'
                self.wp_list[device][room][device]['count'] = 0
            elif device == Device.FAN:
                for sub, v in value.items():
                    try:
                        if sub == 'mode':
                            self.wp_list[device][room][sub]['state'] = v
                            self.wp_list[device][room]['speed']['state'] = OnOff.OFF if v == OnOff.OFF else conf().DEFAULT_SPEED
                        else:
                            self.wp_list[device][room][sub]['state'] = v
                            self.wp_list[device][room]['mode']['state'] = OnOff.OFF if v == OnOff.OFF else OnOff.ON
                        if (self.wp_list[device][room][sub]['last'] == 'set' or type(self.wp_list[device][room][sub]['last']) == float) and self.wp_list[device][room][sub]['set'] == self.wp_list[device][room][sub]['state']:
                            self.wp_list[device][room][sub]['last'] = 'state'
                            self.wp_list[device][room][sub]['count'] = 0
                    except:
                        logger.info('[From {}]Error SetListDevice {}/{}/{}/state = {}'.format(name, device, room, sub, v))
            elif device == Device.LIGHT or device == Device.PLUG:
                for sub, v in value.items():
                    try:
                        self.wp_list[device][room][sub]['state'] = v
                        if (self.wp_list[device][room][sub]['last'] == 'set' or type(self.wp_list[device][room][sub]['last']) == float) and self.wp_list[device][room][sub]['set'] == self.wp_list[device][room][sub]['state']:
                            self.wp_list[device][room][sub]['last'] = 'state'
                            self.wp_list[device][room][sub]['count'] = 0
                    except:
                        logger.info('[From {}]Error SetListDevice {}/{}/{}/state = {}'.format(name, device, room, sub, v))
            elif device == Device.THERMOSTAT:
                for sub, v in value.items():
                    try:
                        if sub == 'mode':
                            self.wp_list[device][room][sub]['state'] = v
                        else:
                            self.wp_list[device][room][sub]['state'] = int(float(v))
                            self.wp_list[device][room]['mode']['state'] = 'heat'
                        if (self.wp_list[device][room][sub]['last'] == 'set' or type(self.wp_list[device][room][sub]['last']) == float) and self.wp_list[device][room][sub]['set'] == self.wp_list[device][room][sub]['state']:
                            self.wp_list[device][room][sub]['last'] = 'state'
                            self.wp_list[device][room][sub]['count'] = 0
                    except:
                        logger.info('[From {}]Error SetListDevice {}/{}/{}/state = {}'.format(name, device, room, sub, v))
        except:
            logger.info('[From {}]Error SetList {}/{} = {}'.format(name, device, room, value))

    def scan_list(self):
        while True:
            if not self.kocom_scan:
                now = time.time()
                if now - self.tick > conf().KOCOM_INTERVAL / 1000:
                    try:
                        for device, d_list in self.wp_list.items():
                            if type(d_list) == dict and ((device == Device.ELEVATOR and self.wp_elevator) or (device == Device.FAN and self.wp_fan) or (device == Device.GAS and self.wp_gas) or (device == Device.LIGHT and self.wp_light) or (device == Device.PLUG and self.wp_plug) or (device == Device.THERMOSTAT and self.wp_thermostat)):
                                for room, r_list in d_list.items():
                                    if type(r_list) == dict:
                                        if 'scan' in r_list and type(r_list['scan']) == dict and now - r_list['scan']['tick'] > conf().SCAN_INTERVAL and ((device == Device.FAN and self.wp_fan) or (device == Device.GAS and self.wp_gas) or (device == Device.LIGHT and self.wp_light) or (device == Device.PLUG and self.wp_plug) or (device == Device.THERMOSTAT and self.wp_thermostat)):
                                            if now - r_list['scan']['last'] > 2:
                                                r_list['scan']['count'] += 1
                                                r_list['scan']['last'] = now
                                                self.set_serial(device, room, '', '', cmd='조회')
                                                time.sleep(conf().SCANNING_INTERVAL)
                                            if r_list['scan']['count'] > 4:
                                                r_list['scan']['tick'] = now
                                                r_list['scan']['count'] = 0
                                                r_list['scan']['last'] = 0
                                        else:
                                            for sub_d, sub_v in r_list.items():
                                                if sub_d != 'scan':
                                                    if sub_v['count'] > 4:
                                                        sub_v['count'] = 0
                                                        sub_v['last'] = 'state'
                                                    elif sub_v['last'] == 'set':
                                                        sub_v['last'] = now
                                                        if device == Device.GAS:
                                                            sub_v['last'] += 5
                                                        elif device == Device.ELEVATOR:
                                                            sub_v['last'] = 'state'
                                                        self.set_serial(device, room, sub_d, sub_v['set'])
                                                    elif type(sub_v['last']) == float and now - sub_v['last'] > 1:
                                                        sub_v['last'] = 'set'
                                                        sub_v['count'] += 1
                    except:
                        logger.debug('[Scan]Error')
            if not self.connected:
                logger.debug('[ERROR] 서버 연결이 끊어져 scan_list Thread를 종료합니다.')
                break
            time.sleep(0.2)

    def set_serial(self, device, room, target, value, cmd='상태'):
        if (time.time() - self.tick) < conf().KOCOM_INTERVAL / 1000:
            return
        if cmd == '상태':
            logger.info('[To {}]{}/{}/{} -> {}'.format(self._name, device, room, target, value))
        elif cmd == '조회':
            logger.info('[To {}]{}/{} -> 조회'.format(self._name, device, room))
        packet = self.make_packet(device, room, '상태', target, value) if cmd == '상태' else  self.make_packet(device, room, '조회', '', '')
        v = self.value_packet(self.parse_packet(packet))

        logger.debug('[To {}]{}'.format(self._name, packet))
        if v['command'] == "조회" and v['src_device'] == Device.WALLPAD:
            logger.debug('[To {}]{}({}) {}({}) -> {}({})'.format(self._name, v['type'], v['command'], v['src_device'], v['src_room'], v['dst_device'], v['dst_room']))
        else:
            logger.debug('[To {}]{}({}) {}({}) -> {}({}) = {}'.format(self._name, v['type'], v['command'], v['src_device'], v['src_room'], v['dst_device'], v['dst_room'], v['value']))
        if device == Device.ELEVATOR:
            self.send_to_homeassistant(Device.ELEVATOR, Device.WALLPAD, OnOff.ON)
        self.write(packet)

    def make_packet(self, device, room, cmd, target, value):
        p_header = 'aa5530bc00'
        p_device = conf().KOCOM_DEVICE_REV.get(device)
        p_room = conf().KOCOM_ROOM_REV.get(room) if device != Device.THERMOSTAT else  conf().KOCOM_ROOM_THERMOSTAT_REV.get(room)
        p_dst = conf().KOCOM_DEVICE_REV.get(Device.WALLPAD) + conf().KOCOM_ROOM_REV.get(Device.WALLPAD)
        p_cmd = conf().KOCOM_COMMAND_REV.get(cmd)
        p_value = ''
        if cmd == '조회':
            p_value = '0000000000000000'
        else:
            if device == Device.ELEVATOR:
                p_device = conf().KOCOM_DEVICE_REV.get(Device.WALLPAD)
                p_room = conf().KOCOM_ROOM_REV.get(Device.WALLPAD)
                p_dst = conf().KOCOM_DEVICE_REV.get(device) + conf().KOCOM_ROOM_REV.get(Device.WALLPAD)
                p_cmd = conf().KOCOM_COMMAND_REV.get(OnOff.ON)
                p_value = '0000000000000000'
            elif device == Device.GAS:
                p_cmd = conf().KOCOM_COMMAND_REV.get(OnOff.OFF)
                p_value = '0000000000000000'
            elif device == Device.LIGHT or device == Device.PLUG:
                try:
                    all_device = device + str('0')
                    for i in range(1,9):
                        sub_device = device + str(i)
                        if target != sub_device:
                            if target == all_device:
                                if sub_device in self.wp_list[device][room]:
                                    p_value += 'ff' if value == OnOff.ON else str('00')
                                else:
                                    p_value += '00'
                            else:
                                if sub_device in self.wp_list[device][room] and self.wp_list[device][room][sub_device]['state'] == OnOff.ON:
                                    p_value += 'ff'
                                else:
                                    p_value += '00'
                        else:
                            p_value += 'ff' if value == OnOff.ON else str('00')
                except:
                    logger.debug('[Make Packet] Error on Device.LIGHT or Device.PLUG')
            elif device == Device.THERMOSTAT:
                try:
                    mode = self.wp_list[device][room]['mode']['set']
                    target_temp = self.wp_list[device][room]['target_temp']['set']
                    if mode == 'heat':
                        p_value += '1100'
                    elif mode == OnOff.OFF:
                        # p_value += '0001'
                        p_value += '0100'
                    else:
                        p_value += '1101'
                    p_value += '{0:02x}'.format(int(float(target_temp)))
                    p_value += '0000000000'
                except:
                    logger.debug('[Make Packet] Error on Device.THERMOSTAT')
            elif device == Device.FAN:
                try:
                    mode = self.wp_list[device][room]['mode']['set']
                    speed = self.wp_list[device][room]['speed']['set']
                    if mode == OnOff.ON:
                        p_value += '1100'
                    elif mode == OnOff.OFF:
                        p_value += '0001'
                    p_value += conf().KOCOM_FAN_SPEED_REV.get(speed)
                    p_value += '00000000000'
                except:
                    logger.debug('[Make Packet] Error on Device.THERMOSTAT')
        if p_value != '':
            packet = p_header + p_device + p_room + p_dst + p_cmd + p_value
            chk_sum = self.check_sum(packet)[1]
            packet += chk_sum + '0d0d'
            return packet
        return False

    def parse_fan(self, value='0000000000000000'):
        fan = {}
        fan['mode'] = OnOff.ON if value[:2] == '11' else OnOff.OFF
        fan['speed'] = conf().KOCOM_FAN_SPEED.get(value[4:5])
        return fan

    def parse_switch(self, device, room, value='0000000000000000'):
        switch = {}
        on_count = 0
        to_i = conf().KOCOM_LIGHT_SIZE.get(room) + 1 if device == Device.LIGHT else conf().KOCOM_PLUG_SIZE.get(room) + 1
        for i in range(1, to_i):
            switch[device + str(i)] = OnOff.OFF if value[i*2-2:i*2] == '00' else OnOff.ON
            if value[i*2-2:i*2] != '00':
                on_count += 1
        switch[device + str('0')] = OnOff.ON if on_count > 0 else OnOff.OFF
        return switch

    def parse_thermostat(self, value='0000000000000000', init_temp=False):
        thermo = {}
        heat_mode = 'heat' if value[:2] == '11' else OnOff.OFF
        away_mode = OnOff.ON if value[2:4] == '01' else OnOff.OFF
        thermo['current_temp'] = int(value[8:10], 16)
        if heat_mode == 'heat' and away_mode == OnOff.ON:
            thermo['mode'] = 'fan_only'
            thermo['target_temp'] = conf().INIT_TEMP if not init_temp else int(init_temp)
        elif heat_mode == 'heat' and away_mode == OnOff.OFF:
            thermo['mode'] = 'heat'
            thermo['target_temp'] = int(value[4:6], 16)
        elif heat_mode == OnOff.OFF:
            thermo['mode'] = OnOff.OFF
            thermo['target_temp'] = conf().INIT_TEMP if not init_temp else int(init_temp)
        return thermo

