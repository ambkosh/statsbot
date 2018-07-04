import sys, logging

def prepare_logger(name):
    """prepares a new logger with given name"""
    l = logging.getLogger(name)
    l.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s %(levelname)s | %(module)s | %(name)s %(lineno)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    l.addHandler(ch)

    file_logger_bot = logging.FileHandler('bot.log', encoding='UTF8')
    file_logger_bot.setLevel(logging.DEBUG)
    file_logger_bot.setFormatter(formatter)
    l.addHandler(file_logger_bot)
