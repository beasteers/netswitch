import glob
import itertools
import serial
from contextlib import contextmanager


DEFAULT_DEVICE_PATTERN = '/dev/ttyUSB*'
DEFAULT_DEVICE = '/dev/ttyUSB2'
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 0.01
OK = 'OK'



class Cell(serial.Serial):
    def __init__(self, device=DEFAULT_DEVICE, baudrate=DEFAULT_BAUDRATE,
                 timeout=DEFAULT_TIMEOUT, **kw):
        super(Cell, self).__init__(device, baudrate, timeout=timeout, **kw)

    def msgsend(self, cmd, length=64, end='\r', add_at=True):
        cmd = cmd.upper()
        if not cmd.startswith('AT'):
            cmd = 'AT'+cmd
        self.write((cmd + end).encode())
        return self.read(length).decode("utf-8")

    def send(self, cmd, length=64, end='\r', raw=False):
        lines = self.msgsend(cmd, length, end=end).splitlines()
        if lines and OK in lines:
            if not raw:
                msg = '\n'.join(
                    l for l in lines if l not in ('', cmd, OK)) or True
            return msg

    def sendn(self, *cmds, **kw):
        return list(itertools.takewhile(
            lambda x: x is not None,
            (self.send(c, **kw) for c in cmds)))

    def ping(self):
        return self.send('AT')

    @property
    def quality(self):
        '''Return signal quality (in dB).'''
        msg = self.ping() and self.send("AT+CSQ")
        if msg:
            value = int(msg.split(': ')[1].split(',')[0].strip())
            return 2 * value - 112

    @property
    def ccid(self):
        '''Return SIM CCID.'''
        msg = self.ping() and self.send("AT+CCID")
        if msg:
            ccid = msg.split(': ')[1].strip()
            return ccid

    def chat(self):
        try:
            import readline
            import atexit, os
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode vi')
            histfile = os.path.join(os.path.expanduser("~"), ".netswitch_at_history")
            try:
                readline.read_history_file(histfile)
                # default history len is -1 (infinite), which may grow unruly
                readline.set_history_length(1000)
            except FileNotFoundError:
                pass
            atexit.register(readline.write_history_file, histfile)
        except ImportError:
            pass
        try:
            print('''
AT Chat! Reference: https://en.wikipedia.org/wiki/Hayes_command_set
         (AT prefix optional, e.g. +csq -> AT+CSQ)
Examples:
*** +csq     # Get signal strength. (rssi(more=better), ber(less=better))
*** +ccid    # Get sim CCID
*** # ummmm I mean I don't really know what to do so..
            '''.lstrip())

            while True:
                cmd = input('*** ')
                if cmd.lower() == 'exit':
                    break
                print(self.msgsend(cmd))
        except KeyboardInterrupt:
            print()
        print('bye!')
    
    @classmethod
    def find_device(cls, device_pattern=DEFAULT_DEVICE_PATTERN, retry=3, *a, **kw):
        for dev in sorted(glob.glob(device_pattern)):
            try:
                cell = cls(dev, *a, **kw)
                if any(cell.send('ATZ') for _ in range(retry or 1)):
                    return cell
                cell.close()
            except BrokenPipeError:
                pass
        raise OSError('No device found matching {}.'.format(device_pattern))

    @staticmethod
    def list_devices(device_pattern=DEFAULT_DEVICE_PATTERN):
        return glob.glob(device_pattern)

devices = Cell.list_devices
cell_device = Cell.find_device

def signal_strength(com_device=DEFAULT_DEVICE):
    with Cell.find_device(com_device) as cell:
        return cell.quality

def sim_ccid(com_device=DEFAULT_DEVICE):
    with Cell.find_device(com_device) as cell:
        return cell.ccid


if __name__ == '__main__':
    import fire
    fire.Fire(Cell)
