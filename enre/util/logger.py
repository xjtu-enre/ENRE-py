import logging
import colorlog


class Logging(object):
    def getLogger(self, name, level='INFO'):

        log_colors_config = {
            'DEBUG': 'white',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }

        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not logger.handlers:
            sh = logging.StreamHandler()

            sh_fmt = colorlog.ColoredFormatter(
                fmt='%(log_color)s[%(asctime)s.%(msecs)03d] %(filename)s:%(lineno)d [%(levelname)s]: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors=log_colors_config)

            sh.setFormatter(fmt=sh_fmt)
            logger.addHandler(sh)
        return logger


if __name__ == '__main__':
    logger = Logging().getLogger(__name__)
    logger.debug("11111111111")
    logger.info("22222222")
    logger.warning("33333333")