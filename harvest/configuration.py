def load_configuration() -> dict:
    filename = _find_first_valid_path('~/.harvest/data-collector-aws/harvest.yaml',
                                      '/etc/harvest.d/harvest.yaml',
                                      'harvest/harvest.yaml',
                                      'harvest.yaml')

    from yaml import load, FullLoader
    with open(filename, 'r') as file_stream:
        result = load(file_stream, Loader=FullLoader)

    return result


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
