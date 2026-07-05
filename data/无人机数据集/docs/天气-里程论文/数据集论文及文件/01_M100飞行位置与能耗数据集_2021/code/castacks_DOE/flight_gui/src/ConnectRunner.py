import traceback
from PyQt5 import QtCore
import paramiko

"""Simple threaded SSH Connection manager using signals to communicate with the main program
"""


class ConnectRunner(QtCore.QThread):
    """Simple Threaded class to run a command on a remote host
    """
    line = QtCore.pyqtSignal(str)  # The signal which emits the next line
    error = QtCore.pyqtSignal(str)  # The signal which emits error messages

    def __init__(self, ssh_parameters, command):
        """Constructor

        Arguments:
            ssh_parameters {dict<str>} -- The SSH parameters to use
            command {str} -- The command to execute on the remote host
        """
        QtCore.QThread.__init__(self)
        # Initialize the SSH Client
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Connect to SSH
        self.command = command
        self.ssh_parameters = ssh_parameters

    def __del__(self):
        self.client.close()

    def run(self):
        """Method to run in background
        """
        try:
            self.client.connect(
                hostname=self.ssh_parameters['host'], username=self.ssh_parameters['user'], password=self.ssh_parameters['pw'])
        except Exception as err:
            traceback.print_exc()
            self.error.emit(err.__str__())
            return
        # Execute the Command
        stdin, stdout, stderr = self.client.exec_command(
            self.command, get_pty=True)
        # Emit all lines in stdout via the signal
        for line in stdout:
            if "set dev:0:0" in line or "blink" in line:
                continue
            line = line.replace('\n', '')
            line = line.replace('\r', '')
            line = line.replace('[0m', '')
            line = line.replace('[1m', '')
            line = line.replace('[33m', '')
            line = line.replace(']2;', '')
            line = line.replace('', '')
            self.line.emit(line)
