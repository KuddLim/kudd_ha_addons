from rs485 import *
from utility import *
from settings import *

if __name__ == '__main__':
    readConfiguration()

    #logging.info('{} 시작'.format(conf().SW_VERSION))
    logger().info('{} 시작'.format(conf().SW_VERSION))

    if conf().DEFAULT_SPEED not in [Speed.LOW, Speed.MEDIUM, Speed.HIGH]:
        logger().info('[Error] DEFAULT_SPEED 설정오류로 medium 으로 설정. {} -> medium'.format(conf().DEFAULT_SPEED))
        conf().DEFAULT_SPEED = Speed.MEDIUM

    _grex_ventilator = False
    _grex_controller = False
    connection_flag = False
    while not connection_flag:
        r = rs485()
        connection_flag = True
        if r._type == 'serial':
            for device in r._device:
                if r._connect[device].isOpen():
                    _name = r._device[device]
                    try:
                        logger().info('[CONFIG] {} 초기화'.format(_name))
                        if _name == 'kocom':
                            kocom = Kocom(r, _name, device, 42)
                        elif _name == 'grex_ventilator':
                            _grex_ventilator = {'serial': r._connect[device], 'name': _name, 'length': 12}
                        elif _name == 'grex_controller':
                            _grex_controller = {'serial': r._connect[device], 'name': _name, 'length': 11}
                    except:
                        logger().info('[CONFIG] {} 초기화 실패'.format(_name))
        elif r._type == 'socket':
            _name = r._device
            if _name == 'kocom':
                kocom = Kocom(r, _name, _name, 42)
                if not kocom.connection_lost():
                    logger().info('[ERROR] 서버 연결이 끊어져 1분 후 재접속을 시도합니다.')
                    time.sleep(60)
                    connection_flag = False
        if _grex_ventilator is not False and _grex_controller is not False:
            _grex = Grex(r, _grex_controller, _grex_ventilator)
