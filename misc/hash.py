import hashlib


def generate_hash(*args) -> str:
    arg_str = ' '.join([f'{a}' for a in args])
    return hashlib.md5(arg_str.encode('utf-8')).hexdigest()
