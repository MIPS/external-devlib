import csv
import os
import signal
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile
from devlib.instrument import Instrument, CONTINUOUS, MeasurementsCsv
from devlib.exception import HostError
from devlib.host import PACKAGE_BIN_DIRECTORY
from devlib.utils.misc import which

INSTALL_INSTRUCTIONS="""
MonsoonInstrument requires the monsoon.py tool, available from AOSP:

https://android.googlesource.com/platform/cts/+/master/tools/utils/monsoon.py

Download this script and put it in your $PATH (or pass it as the monsoon_bin
parameter to MonsoonInstrument). `pip install gflags pyserial` to install the
dependencies.
"""

class MonsoonInstrument(Instrument):
    """Instrument for Monsoon Solutions power monitor

    To use this instrument, you need to install the monsoon.py script available
    from the Android Open Source Project. As of May 2017 this is under the CTS
    repository:

    https://android.googlesource.com/platform/cts/+/master/tools/utils/monsoon.py

    Collects power measurements only, from a selection of two channels, the USB
    passthrough channel and the main output channel.

    :param target: Ignored
    :param monsoon_bin: Path to monsoon.py executable. If not provided,
                        ``$PATH`` is searched.
    :param tty_device: TTY device to use to communicate with the Power
                       Monitor. If not provided, a sane default is used.
    """

    mode = CONTINUOUS

    def __init__(self, target, monsoon_bin=None, tty_device=None):
        super(MonsoonInstrument, self).__init__(target)
        self.monsoon_bin = monsoon_bin or which('monsoon.py')
        if not self.monsoon_bin:
            raise HostError(INSTALL_INSTRUCTIONS)

        self.tty_device = tty_device

        self.process = None
        self.output = None

        self.sample_rate_hz = 500
        self.add_channel('output', 'power')
        self.add_channel('USB', 'power')

    def reset(self, sites=None, kinds=None, channels=None):
        super(MonsoonInstrument, self).reset(sites, kinds)

    def start(self):
        if self.process:
            self.process.kill()

        os.system(self.monsoon_bin + ' --usbpassthrough off')

        cmd = [self.monsoon_bin,
               '--hz', str(self.sample_rate_hz),
               '--samples', '-1', # -1 means sample indefinitely
               '--includeusb']
        if self.tty_device:
            cmd += ['--device', self.tty_device]

        self.logger.debug(' '.join(cmd))
        self.buffer_file = NamedTemporaryFile(prefix='monsoon', delete=False)
        self.process = Popen(cmd, stdout=self.buffer_file, stderr=PIPE)

    def stop(self):
        process = self.process
        self.process = None
        if not process:
            raise RuntimeError('Monsoon script not started')

        process.poll()
        if process.returncode is not None:
            stdout, stderr = process.communicate()
            raise HostError(
                'Monsoon script exited unexpectedly with exit code {}.\n'
                'stdout:\n{}\nstderr:\n{}'.format(process.returncode,
                                                  stdout, stderr))

        process.send_signal(signal.SIGINT)

        stderr =  process.stderr.read()

        self.buffer_file.close()
        with open(self.buffer_file.name) as f:
            stdout = f.read()
        os.remove(self.buffer_file.name)
        self.buffer_file = None

        self.output = (stdout, stderr)
        os.system(self.monsoon_bin + ' --usbpassthrough on')

        # Wait for USB connection to be restored
        print ('waiting for usb connection to be back')
        os.system('adb wait-for-device')

    def get_data(self, outfile):
        if self.process:
            raise RuntimeError('`get_data` called before `stop`')

        stdout, stderr = self.output

        with open(outfile, 'wb') as f:
            writer = csv.writer(f)
            active_sites = [c.site for c in self.active_channels]

            # Write column headers
            row = []
            if 'output' in active_sites:
                row.append('output_power')
            if 'USB' in active_sites:
                row.append('USB_power')
            writer.writerow(row)

            # Write data
            for line in stdout.splitlines():
                # Each output line is a main_output, usb_output measurement pair.
                # (If our user only requested one channel we still collect both,
                # and just ignore one of them)
                output, usb = line.split()
                row = []
                if 'output' in active_sites:
                    row.append(output)
                if 'USB' in active_sites:
                    row.append(usb)
                writer.writerow(row)

        return MeasurementsCsv(outfile, self.active_channels)
