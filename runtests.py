# -*- coding: utf-8 -*-

from eslog.testsuite import suite
import unittest
import logging
import sys

if __name__ == '__main__':
    r = unittest.TextTestRunner()
    s = suite()
    r.run(s)
