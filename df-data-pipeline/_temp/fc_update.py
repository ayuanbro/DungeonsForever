#!/usr/bin/env python3
"""Unified profession update: stage, validate all three languages, then publish."""
import sys
sys.dont_write_bytecode = True
from fc_pipeline import main

if __name__ == '__main__':
    sys.exit(main())
