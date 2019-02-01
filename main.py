import ctypes
import sys
import traceback
import os
from os.path import abspath, dirname, join, exists
import logging
from logging.handlers import TimedRotatingFileHandler
import common
from common import uac_plan_task
from controller import setting_instance

os.chdir(abspath(dirname(sys.argv[0])))

if not exists('log'):
    os.mkdir('log')
formatter = logging.Formatter("%(asctime)s %(levelname)s - %(funcName)s line %(lineno)d : %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# 控制台日志
console_log = logging.StreamHandler()
console_log.setLevel(logging.DEBUG)
console_log.setFormatter(formatter)
logger.addHandler(console_log)
# 文件日志 按天生成
file_log = TimedRotatingFileHandler("log/runtime.log", when='D', encoding="utf-8")
file_log.setLevel(logging.DEBUG)
file_log.setFormatter(formatter)
logger.addHandler(file_log)

logging.debug("main params:"+','.join(sys.argv))

# 检查是否有额外参数
if len(sys.argv) > 1:
    logging.debug("params count:{0}, save.".format(len(sys.argv)))
    setting_instance.settings['args'] = sys.argv
    setting_instance.save_cfg()

# 获取管理员授权
if not common.is_admin():
    logging.debug("not yet admin, request admin start.")
    # 先检查计划任务是否存在 存在则启动计划任务
    uac_plan_task.start_plan_task()
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()
else:
    uac_plan_task.admin_plan()

try:
    from PyQt5.QtCore import QCoreApplication, Qt, QTranslator
    from PyQt5.QtGui import QGuiApplication, QIcon
    from PyQt5.QtQml import QQmlApplicationEngine

    # WEB Engine 需引入 Pyinstaller打包时会添加Engine相关的引用
    # noinspection PyUnresolvedReferences
    # from PyQt5.QtWebEngineWidgets import QWebEngineView

    from controller import mysql_configuration_instance, mysql_service_manager_instance, QmlLanguage, system_instance, \
        aria2_instance
    # noinspection PyUnresolvedReferences
    from ui.qml_rc import *
except Exception as e:
    traceback.print_exc()
    logging.error('Import catch exception :' + traceback.format_exc())
    raise Exception("Import catch exception!")

# 按照qml路径加载，主要由于5.10.1 qrc加载bug，导致qml页面不会刷新
# 使用qml路径加载可以解决页面没有刷新的问题，《5.10打包时关闭》

if sys.argv[0].endswith('.exe'):
    qml_path_load = False
else:
    qml_path_load = True

if __name__ == '__main__':

    # dll = ctypes.CDLL('lib/ScreenShot.dll')
    # dll.PrScrn()
    logging.debug("main start")
    logging.debug("workspace dir:" + os.getcwd())

    run_args = setting_instance.settings.pop('args', None)
    if run_args:
        if 'background' in run_args:
            logging.debug("background run!")
            setting_instance.background_run_param = True
            setting_instance.save_cfg()
    try:
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        # 加载的QML文件
        path = 'qrc:/Main.qml' if not qml_path_load else join(dirname(__file__), 'ui', "Main.qml")
        app = QGuiApplication(sys.argv)
        app.setWindowIcon(
            QIcon(':/img/icon.ico') if not qml_path_load else QIcon(
                join(dirname(__file__), 'ui', "img", "icon.ico")))
        engine = QQmlApplicationEngine()
        context = engine.rootContext()
        context.setContextProperty("mysqlServiceManager", mysql_service_manager_instance)
        context.setContextProperty("mysqlConfiguration", mysql_configuration_instance)
        context.setContextProperty("system", system_instance)
        context.setContextProperty("setting", setting_instance)
        context.setContextProperty("aria2", aria2_instance)
        # context.setContextProperty("uploadHandler", upload_instance)

        # 设置语言 初始化加载
        lang = QmlLanguage(app, engine)
        translator = QTranslator()
        # noinspection PyPropertyAccess
        lang.load_translator(translator, setting_instance.lang)
        app.installTranslator(translator)
        context.setContextProperty("lang", lang)
        logging.debug('begin time: {0}'.format(common.msec()))
        engine.load(path) if not qml_path_load else engine.load(abspath(path))
        if not engine.rootObjects():
            sys.exit(-1)
        sys.exit(app.exec_())
    except Exception as e:
        traceback.print_exc()
        logging.error('Main catch exception :' + traceback.format_exc())
