from PyQt5 import QtCore
from bash import bash
import csv

"""Simple threaded Class to process the data in the background
"""


class DataRunner(QtCore.QThread):
    """Simple Threaded class to run the data post-processing
    """
    line = QtCore.pyqtSignal(str)  # The signal which emits the next line

    def __init__(self, workspace_path, file_path):
        """Constructor

        Arguments:
            workspace_path {string} -- The Path to the workspace containing the filtering package
            file_path {string} -- File Path to the folder containing the data
        """
        QtCore.QThread.__init__(self)

        self.workspace_path = workspace_path
        self.file_path = file_path

    def clean_line(self, line):
        """Cleans a line of unnecessary control characters
        
        Arguments:
            line {str} -- The line to be cleaned
        
        Returns:
            str -- The cleaned line
        """
        line = line.replace('[0m', '')
        line = line.replace('[1m', '')
        line = line.replace(']2;', '')
        line = line.replace('[31m', '')
        line = line.replace('[33m', '')
        line = line.replace('', '')
        return line

    def run_filter(self):
        """Runs the ROS filtering/synchronization script
        
        Returns:
            [type] -- [description]
        """
        src_command = "source {}/devel/setup.bash".format(self.workspace_path)
        run_command = "roslaunch filtering convert.launch file:={0}/raw.bag outpath:={0}".format(
            self.file_path)
        cmd = "bash -c \"" + src_command + " && " + run_command + "\""
        sh = bash(cmd)
        line = self.clean_line(sh.value())
        self.line.emit(line)
        return line

    def run_reindex(self):
        """Runs ```rosbag reindex``` on the current bagfile
        """
        reindex_cmd = "rosbag reindex {}/raw.bag".format(self.file_path)
        src_command = "source {}/devel/setup.bash".format(self.workspace_path)
        cmd = "bash -c \"" + src_command + " && " + reindex_cmd + "\""
        sh = bash(cmd)
        line = self.clean_line(sh.value())
        self.line.emit(line)

    def run(self):
        """Method to run in background
        """
        text = self.run_filter()
        if "Run rosbag reindex" in text: # Data corrupted
            self.line.emit("Error in CSV-File, reindexing")
            self.run_reindex()
            self.run_filter()
        self.line.emit("Data postprocessing finished successfully")
