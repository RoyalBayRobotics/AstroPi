#!/usr/bin/env python

import ephem
from time import sleep

name = 'SS (ZARYA)'
line1 = '1 25544U 98067A   19362.71902896  .00001053  00000-0  26848-4 0  9994'
line2 = '2 25544  51.6443 116.9397 0005193  79.2376  62.1357 15.49524693205439'

iss = ephem.readtle(name, line1, line2)

while True:
    iss.compute()
    print(iss.sublat, iss.sublong)
    sleep(1)
