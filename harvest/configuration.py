from logging import Logger


def load_configuration_files() -> dict:
    from os import environ
    import yaml

    custom_config = {}

    # load the default file
    with open('harvest/harvest.yaml') as default_file:
        default_config = yaml.load(default_file, Loader=yaml.FullLoader)

    # prioritize user's directive, home directory, then the expected /etc/harvest.d/api (when mounted by docker-compose)
    custom_config_path = _find_first_valid_path(environ.get('HARVEST_API_CONFIG'),
                                                '~/.harvest/data-collector-aws/harvest.yaml',
                                                '/etc/harvest.d/harvest.yaml',
                                                'harvest/harvest.yaml',
                                                'harvest.yaml')
    # load custom configurations
    if custom_config_path:
        with open(custom_config_path) as custom_file:
            custom_config = yaml.load(custom_file, Loader=yaml.FullLoader)

    # load version file
    with open('version') as version_file:
        version = version_file.read().strip()

        custom_config['version'] = version

    return custom_config | default_config


def load_logger(location: str, name: str = 'harvest', log_level: str = 'debug', quiet: bool = False,
                **kwargs) -> Logger:
    """
    configures lagging for Harvest
    :param location: where log files should be stored
    :param name: internal log names
    :param log_level: sets the file and stream log levels
    :param quiet: hides stream output
    :return:
    """

    assert isinstance(log_level, str)
    assert isinstance(quiet, bool)

    from logging import getLogger, Formatter, StreamHandler
    from logging.handlers import RotatingFileHandler

    # startup
    logger = getLogger(name=name)

    from importlib import import_module
    lm = import_module('logging')
    log_level_attribute = getattr(lm, log_level.upper())

    # clear existing log handlers anytime this library is called
    [logger.removeHandler(handler) for handler in logger.handlers]

    # formatting
    log_format = Formatter(fmt='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s')

    # file handler
    from pathlib import Path
    from os.path import expanduser
    _location = expanduser(location)

    # make the destination log directory if it does not already exist
    Path(_location).mkdir(parents=True, exist_ok=True)

    # configure the file handler
    from os.path import join
    fh = RotatingFileHandler(join(_location, 'harvest.api.log'), maxBytes=10000000, backupCount=5)
    fh.setFormatter(fmt=log_format)
    fh.setLevel(log_level_attribute)

    logger.addHandler(fh)

    if not quiet:
        # stream handler
        sh = StreamHandler()
        sh.setFormatter(fmt=log_format)
        sh.setLevel(log_level_attribute)
        logger.addHandler(sh)

    logger.setLevel(log_level_attribute)

    logger.debug('logging: enabled')

    return logger


def _find_first_valid_path(*args) -> str or None:
    """
    returns the first path that exists given a list of paths
    performs os.path.expanduser() on each path
    """

    from os.path import abspath, expanduser, exists
    from os import PathLike

    for a in args:
        # expanduser() only expects str or PathLike
        if isinstance(a, (str, PathLike)):
            _a = abspath(expanduser(a))
            if exists(_a):
                return _a

    return None
