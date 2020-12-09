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

    def send(self, cmd, raw=False, end='\r', length=64):
        self.write((cmd + end).encode())
        msg = self.read(length).decode("utf-8")
        lines = msg.splitlines()
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

    def chat(self):
        try:
            print('Opened Chat:')
            while True:
                cmd = input('*** ')
                if cmd.lower() == 'exit':
                    break
                print(self.send(cmd))
        except KeyboardInterrupt:
            pass



def devices(device_pattern=DEFAULT_DEVICE_PATTERN):
    return glob.glob(device_pattern)

@contextmanager
def cell_device(device_pattern=DEFAULT_DEVICE_PATTERN, *a, **kw):
    for dev in glob.glob(device_pattern):
        with Cell(dev, *a, **kw) as cell:
            if cell.send('ATZ'):
                yield cell
                return
    raise OSError('No device found matching {}.'.format(device_pattern))

def signal_strength(com_device=DEFAULT_DEVICE):
    with cell_device(com_device) as cell:
        return cell.quality


if __name__ == '__main__':
    import fire
    fire.Fire(cell_device)
