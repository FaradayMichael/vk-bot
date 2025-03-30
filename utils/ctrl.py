import logging
import os

from utils import config

logger = logging.getLogger(__name__)
CONFIG_ENV_KEY = 'SRVC_CONFIG'


def main_with_parses(parser, entry_point):
    args = None
    config_path = None
    conf = None
    if parser:
        args = parser.parse_args()

        config_path = args.config
        conf = config.read_config(config_path)
    else:
        try:
            config_path = os.environ[CONFIG_ENV_KEY]
            conf = config.read_config(config_path)
        except Exception as e:
            logger.exception(e)
            logger.error(f'Configuration file path not provided at environment [{CONFIG_ENV_KEY}]')
            return None

    if conf is None:
        logger.error(f'Configuration file at path {config_path} not found')
    else:
        return entry_point(args, conf)
