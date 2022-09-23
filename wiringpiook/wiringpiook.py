# Force error if not build Python C Extension Module "wiringpiook"

try:
    from . import wiringpiook
except:
    raise("Must build wiringpiook module.")