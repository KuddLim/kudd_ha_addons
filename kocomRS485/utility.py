
import logging
import logging.config
import logging.handlers

from strings import *
from settings import *

# Log 폴더 생성 (도커 실행 시 로그폴더 매핑)
def make_folder(folder_name):
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)

root_dir = str(os.path.dirname(os.path.realpath(__file__)))
log_dir = root_dir + '/log/'
make_folder(log_dir)
conf_path = str(root_dir + '/' + ConfString.CONF_FILE)
log_path = str(log_dir + '/' + ConfString.LOGFILE)

theLogger = None

def configPath():
    return conf_path

def make_logger(log_path):
    global theLogger
    if theLogger is None:
        #theLogger 인스턴스 생성 및 로그레벨 설정
        theLogger = logging.getLogger(ConfString.LOGNAME)
        theLogger.setLevel(logging.INFO)
        if conf().CONF_LOGLEVEL == LogLevel.INFO: theLogger.setLevel(logging.INFO)
        if conf().CONF_LOGLEVEL == LogLevel.DEBUG: theLogger.setLevel(logging.DEBUG)
        if conf().CONF_LOGLEVEL == LogLevel.WARN: theLogger.setLevel(logging.WARN)

        # formatter 생성
        logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : Line %(lineno)s - %(message)s')

        # fileHandler, StreamHandler 생성
        file_max_bytes = 100 * 1024 * 10 # 1 MB 사이즈
        logFileHandler = logging.handlers.RotatingFileHandler(filename=log_path, maxBytes=file_max_bytes, backupCount=10, encoding='utf-8')
        logStreamHandler = logging.StreamHandler()

        # handler 에 formatter 설정
        logFileHandler.setFormatter(logFormatter)
        logStreamHandler.setFormatter(logFormatter)
        logFileHandler.suffix = "%Y%m%d"

        theLogger.addHandler(logFileHandler)
        #theLogger.addHandler(logStreamHandler)
    return theLogger

def logger():
    return make_logger(log_path)