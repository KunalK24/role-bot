import logging
import datetime
import bot_config

logging.basicConfig(filename='{0}{1:%Y%m%d%H%M%S}-BackersBot-Discord.out'.format(bot_config.log_folder,
                                                                                    datetime.datetime.now()),
                    level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%Y/%m/%d-%H:%M:%S')

logging.info("This is a test")
