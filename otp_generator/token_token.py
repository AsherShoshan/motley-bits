#!/bin/python

import hmac
import base64
import struct
import hashlib
import time
import os
import sys
import getopt

from configobj import ConfigObj
from subprocess import Popen, PIPE


# HOTP: HMAC based One Time Password Algorithm
# TOTP: Time-Based One Time Password (algorithm)
# http://stackoverflow.com/questions/8529265/google-authenticator-implementation-in-python

# token.conf example:
#
#secret = PCTRRUH75NL5QQUUE2EDQALHNM7KQALL
##############################################################################
DEFAULT_CONF_FILE = '.token.conf'

class Token(object):
    def __init__(self, conf=DEFAULT_CONF_FILE):
        self.conf = os.path.join(os.path.expanduser('~'), conf)

        if not os.path.isfile(self.conf):
            print "No such file: %s" % conf
            sys.exit(1)

        self.config = ConfigObj(self.conf)
        self.secret = self.config.get('secret')
        self.token = ''
        self.pin = self.config.get('pin')

    def get_hotp_token(self, intervals_no):
        key = base64.b32decode(self.secret, True)
        msg = struct.pack(">Q", intervals_no)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = ord(h[19]) & 15
        h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
        self.token = h
        return h

    def generate_totp_token(self):
        return self.get_hotp_token(intervals_no=int(time.time())//30)

    def copy_to_clipboard(self, with_pin=False):
        p = Popen(["xsel","-bi"], stdin=PIPE)
        if with_pin:
            p.communicate(input='%s%s' % (self.pin, self.token))
        else:
            p.communicate(input=str(self.token))

    # def set_pin_encoded(self, pin):
    #     self.pin = pin.encode('base64', 'strict')
    #     self.config['pin'] = self.pin
    #     self.config.write()

    # def get_decoded_pin(self):
    #     return self.pin.decode('base64', 'strict')

    def print_token(self, with_pin=False):
        print self.token


def print_usage_and_die(exit_code=0):
    print 'token.py -x or --xsel:  will copy $OTP to clip board'
    print 'token.py --xsel-with-pin:  will copy $PIN$OTP to clip board'
    print 'token.py: print OTP to stdout'
    print 'token.py --print-with-pin: will print $PIN$OTP to stdout'
    # print 'token.py -s <pin>: will set your pin encoded into ~/token.conf'
    print 'token.py -h: will print the message'
    sys.exit(exit_code)


if __name__ == "__main__":

    if len(sys.argv[1:]) == 0:
        t = Token()
        t.generate_totp_token()
        t.print_token()
        sys.exit()
    else:
        opts, remainder = getopt.gnu_getopt(
            sys.argv[1:],
            'hxs:',
            ['help', 'xsel', 'setpin=', 'print-with-pin', 'xsel-with-pin']
        )
        t = Token()
        t.generate_totp_token()

    for opt, arg in opts:
        if opt in ('--help', '-h'):
            print_usage_and_die()
        elif opt in ('--xsel', '-x'):
            print('OTP is copied in clipboard')
            t.copy_to_clipboard(with_pin=False)
        elif opt in ('--xsel-with-pin'):
            print('PIN+OTP are copied in clipboard')
            t.copy_to_clipboard(with_pin=True)
        elif opt in ('--print-with-pin'):
            t.print_token()
        # elif opt in ('--setpin', '-s'):
        #     print('You have your PIN encoded in ~/.token.conf')
        #     t.set_pin_encoded(arg)
        else:
            print_usage_and_die()
