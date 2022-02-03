from rs485 import *


from utility import *
from settings import *
from kocom import *
from threading import Thread


def connection_checker_proc(r):
    while True:
        try:
            if not r.is_connected():
                logger().info("Serial communication unavailable. Try to reconnect...")
                if r._type == 'serial':
                    r.reconnect_serial()
                elif r._type == 'socket':
                    r.reconnect_socket()
        except Exception as ex:
            logger().info("exception occured : {}".format(ex))
        time.sleep(0.5)

if __name__ == '__main__':
    readConfiguration()

    #logging.info('{} 시작'.format(conf().SW_VERSION))
    logger().info('{} Start'.format(conf().SW_VERSION))

    if conf().DEFAULT_SPEED not in [Speed.LOW, Speed.MEDIUM, Speed.HIGH]:
        logger().info('[Error] Failed to set DEFAULT_SPEED. Apply medium instead. {} -> medium'.format(conf().DEFAULT_SPEED))
        conf().DEFAULT_SPEED = Speed.MEDIUM

    _grex_ventilator = False
    _grex_controller = False

    connectionChecker = None

    r = rs485()
    kocom = None

    if r._type == 'serial':
        for device in r._device:
            if r._connect[device].isOpen():
                _name = r._device[device]
                try:
                    logger().info('[CONFIG] {} Initializing serial devices'.format(_name))
                    if _name == 'kocom':
                        kocom = Kocom(r, _name, device, 42)
                    elif _name == 'grex_ventilator':
                        _grex_ventilator = {'serial': r._connect[device], 'name': _name, 'length': 12}
                    elif _name == 'grex_controller':
                        _grex_controller = {'serial': r._connect[device], 'name': _name, 'length': 11}
                except:
                    logger().info('[CONFIG] {} Serial device initialization failed'.format(_name))
    elif r._type == 'socket':
        _name = r._device
        if _name == 'kocom':
            kocom = Kocom(r, _name, _name, 42)

    if _grex_ventilator is not False and _grex_controller is not False:
        _grex = Grex(r, _grex_controller, _grex_ventilator)

    connectionChecker = Thread(target=connection_checker_proc, args=(r,))
    connectionChecker.start()
