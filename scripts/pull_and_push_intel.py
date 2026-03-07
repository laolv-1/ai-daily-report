#!/usr/bin/env python3
import importlib.util
from pathlib import Path

SCRIPT = Path('/root/.openclaw/workspace/scripts/global_intel_dispatch.py')

spec = importlib.util.spec_from_file_location('global_intel_dispatch', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == '__main__':
    module.main()
