"""
Artisan External Output Receiver
Artisan gọi script này mỗi lần sample với args: ET BT ETB BTB
Script ghi data vào file shared để RoasterMonitor đọc.
"""

import sys
import json
import time
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artisan_data.json')

def main():
    try:
        # Artisan truyền: ET BT ETB BTB
        args = sys.argv[1:]
        if len(args) < 2:
            return

        et  = float(args[0])
        bt  = float(args[1])
        etb = float(args[2]) if len(args) > 2 else -1.0
        btb = float(args[3]) if len(args) > 3 else -1.0

        data = {
            'ts':  time.time(),
            'ET':  et,
            'BT':  bt,
            'ETB': etb,
            'BTB': btb,
        }

        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)

    except Exception:
        pass  # silent fail — không làm phiền Artisan

if __name__ == '__main__':
    main()
