# -*- coding: utf-8 -*-

"""
Python native functions to picode string parse and convert to pulse list

See: https://github.com/latchdevel/PiCode

Copyright (c) 2022 Jorge Rivera. All right reserved.
License GNU Lesser General Public License v3.0.
"""

# TX limits must be the same as in "wiringpiook/wiringpiook.c" 
MAX_PULSE_LENGHT =  100000 # Max pulse lenght (microseconds) = 100 millis = 0.1 secs
MAX_PULSE_COUNT  =    1000 # Max pulse count
MAX_PULSE_TYPES  =      10 # pilight string pulse index from 0 to 9 like "c:0123456789;" */
MAX_T_PARAMETER  =      30 # seconds # pilight extended string format "t:"
MAX_TX_TIME      =    2000 # Max TX time (milliseconds)
MAX_TX_REPEATS   =      20 # Max TX repeats 
DEFAULT_REPEATS  =       4 # Default TX repeats

def picode_parse(picode:str):

    """
    Parse a picode string like as:
        "c:011010100101011010100110101001100110010101100110101010101010101012;p:1400,600,6800;r:5@"

    Return a dict like as:
        { 
            'c' : [0,1,1,0,1,0,1,0,0,1,0,1,0,1,1,0,1,0,1,0,0,1,1,0,1,0,1,0,0,1,1,0,0,1,1,0,0,1,0,1,0,1,1,0,0,1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,2],
            'p' : [1400, 600, 6800],
            'r' : 5
        }
    """

    pulses_type = list()
    pulses_length = list()

    result = dict()

    # Check if picode is str
    if isinstance(picode,str):

        # Check for picode length
        picode_len = len(picode)

        # minimal picode "c:01;p:10,90@"
        if picode_len > 13: 

            picode = picode.lower()

            # Check if picode end with @
            if picode[len(picode)-1] == '@':
                picode = picode.replace("@","")

                # Check for params
                params = picode.split(";")
                params_len = len(params)

                if params_len >= 2 and params_len <= 3:

                    # Check for param 3 if r: or t: valid value
                    if params_len == 3:
                        if len(params[2])>=3 and len(params[2])<= 5:
                            param3 = params[2].split(":")
                            if len(param3) == 2:
                                param3_type  = param3[0]
                                if param3_type == "r" or param3_type == "t":
                                    try:
                                        param3_value = int(param3[1])
                                    except:
                                        param3_value = -1
                                    if param3_value > 0:
                                        if ((param3_type == "t" and param3_value <= MAX_T_PARAMETER) or
                                           ( param3_type == "r" and param3_value <= MAX_TX_REPEATS)):
                                            # Add param3 to result dict
                                            result[param3_type] = param3_value
                                        else:
                                            # error: param3 value invalid >limits
                                            return
                                    else:
                                        # error: param3 value invalid <=0
                                        return
                                else:
                                    # error: param3 not r or t
                                    return
                            else:
                                # error: param3 invalid (:)
                                return
                        else:
                            # error: param3 length invalid
                            return

                    # Check for param 2 if p: pulses length valid values
                    param2 = params[1].split(":")
                    if len(param2) == 2:
                        if param2[0] == "p":
                            param2_values = param2[1].split(",")
                            if len(param2_values) > 0 and len(param2_values) < MAX_PULSE_TYPES:
                                for value in param2_values:
                                    try:
                                        value_int = int(value)
                                    except:
                                        value_int = -1
                                    if value_int > 0 and value_int <= MAX_PULSE_LENGHT:
                                        pulses_length.append(value_int)
                                    else:
                                        # error: param2 value invalid
                                        return
                            else:
                                # error: param2 value count invalid 
                                return
                        else:
                            # error: param2 not p
                            return
                    else:
                        # error: param2 length invalid
                        return

                    # Add param2 to result dict
                    result["p"] = pulses_length

                    # Check for param 1 if c: pulses type valid values
                    param1 = params[0].split(":")
                    if len(param1) == 2:
                        if param1[0] == "c":
                            if len(param1[1]) > 0:
                                for value in param1[1]:
                                    try:
                                        value_int = int(value)
                                    except:
                                        value_int = -1
                                    if value_int >= 0 and value_int < MAX_PULSE_TYPES:
                                        pulses_type.append(value_int)
                                    else:
                                        # error: param1 value invalid
                                        return
                                if len(pulses_type) % 2 != 0 :
                                    # Add another last pulse if pulse count is odd
                                    pulses_type.append(value_int)
                            else:
                                # error: param1 value count invalid 
                                return
                        else:
                            # error: param1 not c
                            return
                    else:
                        # error: param1 length invalid
                        return
                    
                    # Add param1 to result dict
                    result["c"] = pulses_type

                    # All checks OK
                    return result
                else:
                    # error: invalid params number (;)
                    return
            else:
                # error: picode not @ end
                return
        else:
            # error: picode length invalid
            return
    else:
        # error: picode not str
        return

def picode_pulselist(picode:dict):

    """
    Convert picode dict form picode_parse() to pulse list
    Repeats key 'r' or timed key 't' are ignored

    Convert a dict like as:
        { 
            'c' : [0,1,1,0,1,0,1,0,0,1,0,1,0,1,1,0,1,0,1,0,0,1,1,0,1,0,1,0,0,1,1,0,0,1,1,0,0,1,0,1,0,1,1,0,0,1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,2],
            'p' : [1400, 600, 6800],
            'r' : 5
        }

    To list like as:
        [
            1400,  600,  600, 1400,  600, 1400,  600, 1400, 1400,  600, 1400,  600, 1400,  600,  600, 1400, 600, 
            1400,  600, 1400, 1400,  600,  600, 1400,  600, 1400,  600, 1400, 1400,  600,  600, 1400, 1400, 600, 
             600, 1400, 1400,  600, 1400,  600, 1400,  600,  600, 1400, 1400,  600,  600, 1400,  600, 1400, 600, 
            1400,  600, 1400,  600, 1400,  600, 1400,  600, 1400,  600, 1400,  600, 1400,  600, 6800
        ]
    """

    pulse_list = list()
    
    # Check if picode is a dict
    if isinstance(picode,dict):
        # Check if picode dict has c and p keys
        if "c" in picode.keys() and "p" in picode.keys():
            # Check if c and p values are lists
            if isinstance(picode["c"], list) and isinstance(picode["p"], list):
                # Pulses loop
                for pulse_type in picode["c"]:
                    # Add pulse value to pulse list
                    pulse_list.append((picode["p"][pulse_type]))

                # All checks OK
                return pulse_list
            else:
                # error: c or p not a list
                return
        else:
            # error: picode dict not c or p key
            return
    else:
        # error: picode not a dict
        return

def find_picode(picode:str = ""):

    """
    Find picode sequences into a string.
    
    Returns a list of found picode strings or an empty list if none is found.
    """

    def search(picode,char,start=0):
        """Like an str.index() but returns -1 if not found"""
        try:
            return picode.index(char,start)
        except:
            return -1

    result = []

    if isinstance(picode,str):
        s = 0
        e = len(picode)
        while s < e:
            c = search(picode,"c",s)
            if c >= 0:
                a = search(picode,"@",s)
                if a > 0:
                    result.append(picode[c:a+1])
                    s = a+1
                else:
                    s = e
            else:
                s = e

    return result
