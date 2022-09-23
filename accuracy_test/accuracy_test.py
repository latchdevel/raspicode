#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Raspicode Accuracy Test

Connect a logic analyzer to one of Raspberry Pi GPIOs

See: https://github.com/latchdevel/raspicode

Copyright (c) 2022 Jorge Rivera. All right reserved.
License GNU Lesser General Public License v3.0.
"""

import wiringpiook
import math

# Raspberry Pi GPIO number (BCM)
gpio = 21

# Pulses length range (uSecs)
initial = 5
final = 100000

# Pulses list
pulses = list()

# Current pulse length
pulse = initial

# Populate pulse list
while pulse < final:
    pulses.append(round(pulse))    # HIGH state (3.3v)
    pulses.append(round(pulse))    # LOW state (0v/GND)
    pulse = pulse / math.log10(8)  # Logarithmic distribution of pulses length 

# Change last long pulse to initial pulse length
pulses.pop()
pulses.append(1)

# Show pulses list
print("len: %d %s" % (len(pulses),pulses))

# Print pulses for Excel cut&paste
for pulse in pulses:
    print("%d" % pulse)

# Send pulse train to Raspberry Pi GPIO
result = wiringpiook.tx(gpio,pulses,1)

# Show tx result
if result > 0:
    print("OK tx time: %d milliseconds" % result)
else:
    print("Error code: %d" % result)
