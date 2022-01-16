import threading
import paho.mqtt.client as mqtt

from strings import *
from utility import *

class Grex:
    def __init__(self, client, cont, vent):
        self._name = 'grex'
        self.contoller = cont
        self.ventilator = vent
        self.grex_cont = {'mode': OnOff.OFF, 'speed': OnOff.OFF}
        self.vent_cont = {'mode': OnOff.OFF, 'speed': OnOff.OFF}
        self.mqtt_cont = {'mode': OnOff.OFF, 'speed': OnOff.OFF}

        self.d_mqtt = self.connect_mqtt(client._mqtt, 'GREX')

        _t4 = threading.Thread(target=self.get_serial, args=(self.contoller['serial'], self.contoller['name'], self.contoller['length']))
        _t4.daemon = True
        _t4.start()
        _t5 = threading.Thread(target=self.get_serial, args=(self.ventilator['serial'], self.ventilator['name'], self.ventilator['length']))
        _t5.daemon = True
        _t5.start()

    def connect_mqtt(self, server, name):
        mqtt_client = mqtt.Client()
        mqtt_client.on_message = self.on_message
        #mqtt_client.on_publish = self.on_publish
        mqtt_client.on_subscribe = self.on_subscribe
        mqtt_client.on_connect = self.on_connect

        if server['anonymous'] != BooleanStr.TRUE:
            if server['server'] == '' or server['username'] == '' or server['password'] == '':
                logger().info('{} 설정을 확인하세요. Server[{}] ID[{}] PW[{}] Device[{}]'.format(ConfString.MQTT, server['server'], server['username'], server['password'], name))
                return False
            mqtt_client.username_pw_set(username=server['username'], password=server['password'])
            logger().debug('{} STATUS. Server[{}] ID[{}] PW[{}] Device[{}]'.format(ConfString.MQTT, server['server'], server['username'], server['password'], name))
        else:
            logger().debug('{} STATUS. Server[{}] Device[{}]'.format(ConfString.MQTT, server['server'], name))

        mqtt_client.connect(server['server'], 1883, 60)
        mqtt_client.loop_start()
        return mqtt_client

    def on_message(self, client, obj, msg):
        _topic = msg.topic.split('/')
        _payload = msg.payload.decode()

        if 'config' in _topic:
            if _topic[0] == 'rs485' and _topic[3] == 'restart':
                self.homeassistant_device_discovery()
                return
        elif _topic[0] == HAStrings.PREFIX and _topic[1] == HAStrings.FAN and _topic[2] == 'grex':
            logger().info("Message Fan: {} = {}".format(msg.topic, _payload))
            if _topic[3] == 'speed' or _topic[3] == 'mode':
                if _topic[3] == 'mode' and self.mqtt_cont[_topic[3]] == OnOff.OFF and _payload == OnOff.ON and self.mqtt_cont['speed'] == OnOff.OFF:
                    self.mqtt_cont['speed'] = Speed.LOW
                self.mqtt_cont[_topic[3]] = _payload

                if self.mqtt_cont['mode'] == OnOff.OFF and self.mqtt_cont['speed'] == OnOff.OFF:
                    self.send_to_homeassistant(HAStrings.FAN, self.mqtt_cont)

    def on_publish(self, client, obj, mid):
        logger().info("Publish: {}".format(str(mid)))

    def on_subscribe(self, client, obj, mid, granted_qos):
        logger().info("Subscribed: {} {}".format(str(mid),str(granted_qos)))

    def on_connect(self, client, userdata, flags, rc):
        if int(rc) == 0:
            logger().info("MQTT connected OK")
            self.homeassistant_device_discovery(initial=True)
        elif int(rc) == 1:
            logger().info("1: Connection refused – incorrect protocol version")
        elif int(rc) == 2:
            logger().info("2: Connection refused – invalid client identifier")
        elif int(rc) == 3:
            logger().info("3: Connection refused – server unavailable")
        elif int(rc) == 4:
            logger().info("4: Connection refused – bad username or password")
        elif int(rc) == 5:
            logger().info("5: Connection refused – not authorised")
        else:
            logger().info(rc, ": Connection refused")

    def homeassistant_device_discovery(self, initial=False):
        subscribe_list = []
        publish_list = []
        subscribe_list.append(('rs485/bridge/#', 0))
        ha_topic = '{}/{}/{}_{}/config'.format(HAStrings.PREFIX, HAStrings.FAN, 'grex', Device.FAN)
        ha_payload = {
            'name': '{}_{}'.format(self._name, Device.FAN),
            'cmd_t': '{}/{}/{}/mode'.format(HAStrings.PREFIX, HAStrings.FAN, 'grex'),
            'stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.FAN, 'grex'),
            'spd_cmd_t': '{}/{}/{}/speed'.format(HAStrings.PREFIX, HAStrings.FAN, 'grex'),
            'spd_stat_t': '{}/{}/{}/state'.format(HAStrings.PREFIX, HAStrings.FAN, 'grex'),
            'stat_val_tpl': '{{ value_json.mode }}',
            'spd_val_tpl': '{{ value_json.speed }}',
            'pl_on': OnOff.ON,
            'pl_off': OnOff.OFF,
            'spds': [Speed.LOW, Speed.MEDIUM, Speed.HIGH, OnOff.OFF],
            'uniq_id': '{}_{}_{}'.format(self._name, 'grex', Device.FAN),
            'device': {
                'name': 'Grex Ventilator',
                'ids': 'grex_ventilator',
                'mf': 'Grex',
                'mdl': 'Ventilator',
                'sw': conf().SW_VERSION
            }
        }
        subscribe_list.append((ha_topic, 0))
        subscribe_list.append((ha_payload['cmd_t'], 0))
        subscribe_list.append((ha_payload['spd_cmd_t'], 0))
        #subscribe_list.append((ha_payload['stat_t'], 0))
        publish_list.append({ha_topic : json.dumps(ha_payload)})

        ha_topic = '{}/{}/{}_{}_mode/config'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN)
        ha_payload = {
            'name': '{}_{}_mode'.format(self._name, Device.FAN),
            'stat_t': '{}/{}/{}_{}/state'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN),
            'val_tpl': '{{ value_json.' + Device.FAN + '_mode }}',
            'ic': 'mdi:play-circle-outline',
            'uniq_id': '{}_{}_{}_mode'.format(self._name, 'grex', Device.FAN),
            'device': {
                'name': 'Grex Ventilator',
                'ids': 'grex_ventilator',
                'mf': 'Grex',
                'mdl': 'Ventilator',
                'sw': conf().SW_VERSION
            }
        }
        subscribe_list.append((ha_topic, 0))
        #subscribe_list.append((ha_payload['stat_t'], 0))
        publish_list.append({ha_topic : json.dumps(ha_payload)})
        ha_topic = '{}/{}/{}_{}_speed/config'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN)
        ha_payload = {
            'name': '{}_{}_speed'.format(self._name, Device.FAN),
            'stat_t': '{}/{}/{}_{}/state'.format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN),
            'val_tpl': '{{ value_json.' + Device.FAN + '_speed }}',
            'ic': 'mdi:speedometer',
            'uniq_id': '{}_{}_{}_speed'.format(self._name, 'grex', Device.FAN),
            'device': {
                'name': 'Grex Ventilator',
                'ids': 'grex_ventilator',
                'mf': 'Grex',
                'mdl': 'Ventilator',
                'sw': conf().SW_VERSION
            }
        }
        subscribe_list.append((ha_topic, 0))
        #subscribe_list.append((ha_payload['stat_t'], 0))
        publish_list.append({ha_topic : json.dumps(ha_payload)})

        if initial:
            self.d_mqtt.subscribe(subscribe_list)
        for ha in publish_list:
            for topic, payload in ha.items():
                self.d_mqtt.publish(topic, payload)

    def send_to_homeassistant(self, target, value):
        if target == HAStrings.FAN:
            self.d_mqtt.publish("{}/{}/{}/state".format(HAStrings.PREFIX, HAStrings.FAN, 'grex'), json.dumps(value))
            logger().info("[To HA]{}/{}/{}/state = {}".format(HAStrings.PREFIX, HAStrings.FAN, 'grex', json.dumps(value)))
        elif target == HAStrings.SENSOR:
            self.d_mqtt.publish("{}/{}/{}_{}/state".format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN), json.dumps(value, ensure_ascii = False))
            logger().info("[To HA]{}/{}/{}_{}/state = {}".format(HAStrings.PREFIX, HAStrings.SENSOR, 'grex', Device.FAN, json.dumps(value, ensure_ascii = False)))

    def get_serial(self, ser, packet_name, packet_len):
        buf = []
        start_flag = False
        while True:
            if ser.readable():
                row_data = ser.read()
                hex_d = row_data.hex()
                start_hex = ''
                if packet_name == 'kocom':  start_hex = 'aa'
                elif packet_name == 'grex_ventilator':  start_hex = 'd1'
                elif packet_name == 'grex_controller':  start_hex = 'd0'
                if hex_d == start_hex:
                    start_flag = True
                if start_flag == True:
                    buf.append(hex_d)

                if len(buf) >= packet_len:
                    joindata = ''.join(buf)
                    chksum = self.validate_checksum(joindata, packet_len - 1)
                    #logger().debug("[From {}]{} {} {}".format(packet_name, joindata, str(chksum[0]), str(chksum[1])))
                    if chksum[0]:
                        self.packet_parsing(joindata, packet_name)
                    buf = []
                    start_flag = False

    def packet_parsing(self, packet, packet_name):
        p_prefix = packet[:4]

        if p_prefix == 'd00a':
            m_packet = self.make_response_packet(0)
            m_chksum = self.validate_checksum(m_packet, 11)
            if m_chksum[0]:
                self.contoller['serial'].write(bytearray.fromhex(m_packet))
            logger().debug('[From Grex]error code : E1')
        elif p_prefix == 'd08a':
            control_packet = ''
            response_packet = ''
            p_mode = packet[8:12]
            p_speed = packet[12:16]

            if self.grex_cont['mode'] != conf().GREX_MODE[p_mode] or self.grex_cont['speed'] != conf().GREX_SPEED[p_speed]:
                self.grex_cont['mode'] = conf().GREX_MODE[p_mode]
                self.grex_cont['speed'] = conf().GREX_SPEED[p_speed]
                logger().info('[From {}]mode:{} / speed:{}'.format(packet_name, self.grex_cont['mode'], self.grex_cont['speed']))
                send_to_ha_fan = {'mode': OnOff.OFF, 'speed': OnOff.OFF}
                if self.grex_cont['mode'] != OnOff.OFF or (self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON):
                    send_to_ha_fan['mode'] = OnOff.ON
                    send_to_ha_fan['speed'] = self.grex_cont['speed']
                self.send_to_homeassistant(HAStrings.FAN, send_to_ha_fan)

                send_to_ha_sensor = {'fan_mode': OnOff.OFF, 'fan_speed': OnOff.OFF}
                if self.grex_cont['mode'] != OnOff.OFF or (self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON):
                    if self.grex_cont['mode'] == GrexMode.AUTO:
                        send_to_ha_sensor['fan_mode'] = '자동'
                    elif self.grex_cont['mode'] == GrexMode.MANUAL:
                        send_to_ha_sensor['fan_mode'] = '수동'
                    elif self.grex_cont['mode'] == GrexMode.SLEEP:
                        send_to_ha_sensor['fan_mode'] = '취침'
                    elif self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON:
                        send_to_ha_sensor['fan_mode'] = 'HA'
                    if self.grex_cont['speed'] == Speed.LOW:
                        send_to_ha_sensor['fan_speed'] = '1단'
                    elif self.grex_cont['speed'] == Speed.MEDIUM:
                        send_to_ha_sensor['fan_speed'] = '2단'
                    elif self.grex_cont['speed'] == Speed.HIGH:
                        send_to_ha_sensor['fan_speed'] = '3단'
                    elif self.grex_cont['speed'] == OnOff.OFF:
                        send_to_ha_sensor['fan_speed'] = '대기'
                self.send_to_homeassistant(HAStrings.SENSOR, send_to_ha_sensor)

            if self.grex_cont['mode'] == OnOff.OFF:
                response_packet = self.make_response_packet(0)
                if self.mqtt_cont['mode'] == OnOff.OFF or (self.mqtt_cont['mode'] == OnOff.ON and self.mqtt_cont['speed'] == OnOff.OFF):
                    control_packet = self.make_control_packet(OnOff.OFF, OnOff.OFF)
                elif self.mqtt_cont['mode'] == OnOff.ON and self.mqtt_cont['speed'] != OnOff.OFF:
                    control_packet = self.make_control_packet(GrexMode.MANUAL, self.mqtt_cont['speed'])
            else:
                control_packet = self.make_control_packet(self.grex_cont['mode'], self.grex_cont['speed'])
                if self.grex_cont['speed'] == Speed.LOW:
                    response_packet = self.make_response_packet(1)
                elif self.grex_cont['speed'] == Speed.MEDIUM:
                    response_packet = self.make_response_packet(2)
                elif self.grex_cont['speed'] == Speed.HIGH:
                    response_packet = self.make_response_packet(3)
                elif self.grex_cont['speed'] == OnOff.OFF:
                    response_packet = self.make_response_packet(0)

            if response_packet != '':
                self.contoller['serial'].write(bytearray.fromhex(response_packet))
                #logger().debug("[Tooo grex_controller]{}".format(response_packet))
            if control_packet != '':
                self.ventilator['serial'].write(bytearray.fromhex(control_packet))
                #logger().debug("[Tooo grex_ventilator]{}".format(control_packet))

        elif p_prefix == 'd18b':
            p_speed = packet[8:12]
            if self.vent_cont['speed'] != conf().GREX_SPEED[p_speed]:
                self.vent_cont['speed'] = conf().GREX_SPEED[p_speed]
                logger().info('[From {}]speed:{}'.format(packet_name, self.vent_cont['speed']))

                send_to_ha_fan = {'mode': OnOff.OFF, 'speed': OnOff.OFF}
                if self.grex_cont['mode'] != OnOff.OFF or (self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON):
                    send_to_ha_fan['mode'] = OnOff.ON
                    send_to_ha_fan['speed'] = self.vent_cont['speed']
                self.send_to_homeassistant(HAStrings.FAN, send_to_ha_fan)

                send_to_ha_sensor = {'fan_mode': OnOff.OFF, 'fan_speed': OnOff.OFF}
                if self.grex_cont['mode'] != OnOff.OFF or (self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON):
                    if self.grex_cont['mode'] == GrexMode.AUTO:
                        send_to_ha_sensor['fan_mode'] = '자동'
                    elif self.grex_cont['mode'] == GrexMode.MANUAL:
                        send_to_ha_sensor['fan_mode'] = '수동'
                    elif self.grex_cont['mode'] == GrexMode.SLEEP:
                        send_to_ha_sensor['fan_mode'] = '취침'
                    elif self.grex_cont['mode'] == OnOff.OFF and self.mqtt_cont['mode'] == OnOff.ON:
                        send_to_ha_sensor['fan_mode'] = 'HA'
                    if self.vent_cont['speed'] == Speed.LOW:
                        send_to_ha_sensor['fan_speed'] = '1단'
                    elif self.vent_cont['speed'] == Speed.MEDIUM:
                        send_to_ha_sensor['fan_speed'] = '2단'
                    elif self.vent_cont['speed'] == Speed.HIGH:
                        send_to_ha_sensor['fan_speed'] = '3단'
                    elif self.vent_cont['speed'] == OnOff.OFF:
                        send_to_ha_sensor['fan_speed'] = '대기'
                self.send_to_homeassistant(HAStrings.SENSOR, send_to_ha_sensor)

    def make_control_packet(self, mode, speed):
        prefix = 'd08ae022'
        if mode == OnOff.OFF:
            packet_mode = '0000'
        elif mode == GrexMode.AUTO:
            packet_mode = '0100'
        elif mode == GrexMode.MANUAL:
            packet_mode = '0200'
        elif mode == GrexMode.SLEEP:
            packet_mode = '0300'
        else:
            return ''
        if speed == OnOff.OFF:
            packet_speed = '0000'
        elif speed == Speed.LOW:
            packet_speed = '0101'
        elif speed == Speed.MEDIUM:
            packet_speed = '0202'
        elif speed == Speed.HIGH:
            packet_speed = '0303'
        else:
            return ''
        if ((mode == GrexMode.AUTO or mode == GrexMode.SLEEP) and (speed == OnOff.OFF)) or (speed == Speed.LOW or speed == Speed.MEDIUM or speed == Speed.HIGH):
            postfix = '0001'
        else:
            postfix = '0000'

        packet = prefix + packet_mode + packet_speed + postfix
        packet_checksum = self.make_checksum(packet, 10)
        packet = packet + packet_checksum
        return packet

    def make_response_packet(self, speed):
        prefix = 'd18be021'
        if speed == 0:
            packet_speed = '0000'
        elif speed == 1:
            packet_speed = '0101'
        elif speed == 2:
            packet_speed = '0202'
        elif speed == 3:
            packet_speed = '0303'
        if speed == 0:
            postfix = '0000000000'
        elif speed > 0:
            postfix = '0000000100'

        packet = prefix + packet_speed + postfix
        packet_checksum = self.make_checksum(packet, 11)
        packet = packet + packet_checksum
        return packet

    def hex_to_list(self, hex_string):
        slide_windows = 2
        start = 0
        buf = []
        for x in range(int(len(hex_string) / 2)):
            buf.append('0x{}'.format(hex_string[start: slide_windows].lower()))
            slide_windows += 2
            start += 2
        return buf

    def validate_checksum(self, packet, length):
        hex_list = self.hex_to_list(packet)
        sum_buf = 0
        for ix, x in enumerate(hex_list):
            if ix > 0:
                hex_int = int(x, 16)
                if ix == length:
                    chksum_hex = '0x{0:02x}'.format((sum_buf % 256))
                    if hex_list[ix] == chksum_hex:
                        return (True, hex_list[ix])
                    else:
                        return (False, hex_list[ix])
                sum_buf += hex_int

    def make_checksum(self, packet, length):
        hex_list = self.hex_to_list(packet)
        sum_buf = 0
        chksum_hex = 0
        for ix, x in enumerate(hex_list):
            if ix > 0:
                hex_int = int(x, 16)
                sum_buf += hex_int
                if ix == length - 1:
                    chksum_hex = '{0:02x}'.format((sum_buf % 256))
        return str(chksum_hex)