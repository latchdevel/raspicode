"""
Dummy wiringpiook module to simulate GPIO usage in non-Raspberry Pi systems.
"""

from time import sleep as _sleep

# TX limits from https://github.com/latchdevel/pilight-usb-nano
_MAX_PULSE_LENGHT          = 100000
_MAX_PULSE_COUNT           =   1000
_MAX_TX_TIME               =   2000
_MAX_TX_REPEATS            =     20
_DEFAULT_REPEATS           =      4


# Error return codes for wiringpiook.tx(bcm_gpio,pulse_list,repeats=4)
_NO_ERROR                   =   0
_ERROR_UNKNOW               =  -1
_ERROR_INVALID_PULSE_COUNT  =  -2
_ERROR_PULSETRAIN_OOD       =  -3
_ERROR_INVALID_PULSE_LENGHT =  -4
_ERROR_INVALID_TX_TIME      =  -5

print("WARNING! DUMMY WIRINGPIOOK MODULE LOADED!")

def tx(bcm_gpio:int, pulse_list:list, repeats:int=_DEFAULT_REPEATS):
    """Dummy tx to simulate GPIO pulse train transmission
    """
    
    if not isinstance(bcm_gpio,int):
        raise TypeError ("bcm_gpio must be an integer number.")

    if not isinstance(pulse_list,list):
        raise TypeError ("pulse_list must be a list.")

    if not isinstance(repeats,int):
        raise TypeError ("repeats must be an integer number.")

    if ((bcm_gpio < 2) or (bcm_gpio > 27)):
        raise ValueError ("invalid gpio number, must be >=2 and <=27.")

    if ((repeats < 1) or (repeats > _MAX_TX_REPEATS)):
        raise ValueError ("invalid repeats, must be >=1 and <=%d.",_MAX_TX_REPEATS)
    
    for pulse in pulse_list:
        if not isinstance(pulse,int):
            raise TypeError ("list items must be integer numbers.")
    
    if ((len(pulse_list)) < 1 or (len(pulse_list)) > _MAX_PULSE_COUNT):
        return _ERROR_INVALID_PULSE_COUNT

    if (len(pulse_list) % 2 != 0):
        return _ERROR_PULSETRAIN_OOD

    tx_time = 0

    for pulse in pulse_list:
        if ((pulse > 0) and (pulse < _MAX_PULSE_LENGHT)):
            tx_time = tx_time + pulse
            if (tx_time > _MAX_TX_TIME*1000):
                return _ERROR_INVALID_TX_TIME
        else:
            return _ERROR_INVALID_PULSE_LENGHT

    tx_time = tx_time * repeats

    _sleep(tx_time/1000000.0)

    return int(tx_time/1000)
