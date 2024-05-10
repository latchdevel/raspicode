"""
   Python C Extension Module WiringPi OOK

   Send OOK pulse train to digital GPIO using wiringPi C library

   See: https://github.com/latchdevel/raspicode

   Copyright (c) 2022-2024 Jorge Rivera. All right reserved.
   License GNU Lesser General Public License v3.0.
"""

__version__ = "1.1"
__author__ = 'Jorge Rivera'
__doc__ = 'Python C Extension Module to send OOK pulse train to digital GPIO using wiringPi library.\nSee: https://github.com/latchdevel/raspicode'

# Force error if not build Python C Extension Module "wiringpiook"
try:
    from wiringpiook import wiringpiook as _wiringpiook_c
except:
    raise("Must build wiringpiook module.")

# Remove wiringpiook from namespace
if 'wiringpiook' in dir():
    del wiringpiook

# TX limits from 'wiringpiook.c'
MAX_PULSE_LENGTH = _wiringpiook_c.MAX_PULSE_LENGTH # Max pulse length (microseconds)
MAX_PULSE_COUNT  = _wiringpiook_c.MAX_PULSE_COUNT  # Max pulse count
MAX_TX_TIME      = _wiringpiook_c.MAX_TX_TIME      # Max TX time (milliseconds)
MAX_TX_REPEATS   = _wiringpiook_c.MAX_TX_REPEATS   # Max TX repeats
DEFAULT_REPEATS  = _wiringpiook_c.DEFAULT_REPEATS  # Default TX repeats

# Error return codes for tx(bcm_gpio, pulse_list, repeats = DEFAULT_REPEATS)
_NO_ERROR                   =   0
_ERROR_UNKNOWN              =  -1
_ERROR_INVALID_PULSE_COUNT  =  -2
_ERROR_PULSETRAIN_OOD       =  -3
_ERROR_INVALID_PULSE_LENGTH =  -4
_ERROR_INVALID_TX_TIME      =  -5

# Redefines the Python function tx() to add parameter checks and basic docstrings
def tx(bcm_gpio: int, pulse_list: list, repeats: int = DEFAULT_REPEATS) -> int:
    """
    Transmission of the pulse train to a GPIO

    Parameters:
     - bcm_gpio:   Native Broadcom GPIO number from 2 to 27
     - pulse_list: List of integers, whose length must be even
     - repeats:    Number of transmission repeats

    Returns:
     - Positive integer as transmission time in milliseconds or negative error code
    """
   
    if not isinstance(bcm_gpio,int):
        raise TypeError ("bcm_gpio must be an integer number.")

    if not isinstance(pulse_list,list):
        raise TypeError ("pulse_list must be a list.")

    if not isinstance(repeats,int):
        raise TypeError ("repeats must be an integer number.")

    if ((bcm_gpio < 2) or (bcm_gpio > 27)):
        raise ValueError ("invalid gpio number, must be >=2 and <=27.")

    if ((repeats < 1) or (repeats > MAX_TX_REPEATS)):
        raise ValueError ("invalid repeats, must be >=1 and <={}.".format(MAX_TX_REPEATS))
    
    for pulse in pulse_list:
        if not isinstance(pulse,int):
            raise TypeError ("list items must be integer numbers.")
    
    if ((len(pulse_list)) < 1 or (len(pulse_list)) > MAX_PULSE_COUNT):
        return _ERROR_INVALID_PULSE_COUNT

    if (len(pulse_list) % 2 != 0):
        return _ERROR_PULSETRAIN_OOD

    tx_time = 0

    for pulse in pulse_list:
        if ((pulse > 0) and (pulse < MAX_PULSE_LENGTH)):
            tx_time = tx_time + pulse
            if (tx_time*repeats > MAX_TX_TIME*1000):
                return _ERROR_INVALID_TX_TIME
        else:
            return _ERROR_INVALID_PULSE_LENGTH

    return _wiringpiook_c.tx(bcm_gpio, pulse_list, repeats)