import subprocess
import socket
import re
import paramiko
import os
from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QLineEdit, QFrame, QSplitter, QTextEdit)
from PyQt5.QtCore import QSettings
from bash import bash
from ConnectRunner import ConnectRunner
from DataRunner import DataRunner
from DataCheck import DataCheck
from SettingHandler import SettingHandler
from InfoDialog import InfoDialog

"""Package containing the Main Layout of the GUI
"""


class MainWidget(QWidget):
    """The main widget of the GUI itself, contains all interaction elements
    """

    def __init__(self, parent):
        """Constructor

        Arguments:
            parent {QWidget} -- [The Parent of the Widget]
        """
        super().__init__()
        self.info_dialog = InfoDialog()
        self.cwd = os.getcwd()
        self.command_runner = None
        self.record_runner = None
        self.fly_runner = None
        self.parent = parent
        self.fly_cnt = 0
        self.setting_handler = SettingHandler()
        self.initUI()

    def command_line(self, line):
        """Append the console output to the control Window

        Arguments:
            line {str} -- The next line to add
        """
        if not self.connected:  # Set the Buttons and Messages to indicate the connected status
            self.connected = True
            self.bt_connect.setText("Disconnect")
            self.parent.statusBar().showMessage("Connected")
            self.bt_connect.setDisabled(False)
        self.t_control.append(line)
        if "telemetry" in line:
            self.bt_fly.setDisabled(False)
            self.t_control.append("Ready to fly")

    def ssh_error(self, error):
        """Handles an Error line coming from one of the SSH Clients

        Arguments:
            error {str} -- The Error message
        """
        self.parent.statusBar().showMessage("Disconnected")
        self.bt_connect.setDisabled(False)
        self.close_connection()
        self.info_dialog.show_dialog(error, ok_only=True)

    def read_data_action(self):
        """Action triggered when pushing the "Read Data" button
        """
        self.t_record.append("Reading data from drone")
        self.bt_read_data.setDisabled(True)
        self.recording = False
        try:
            del self.fly_runner
        except:
            pass
        # Stop the Recording
        rpi_parameters = self.setting_handler.get_rpi_settings()
        self.record_disconnect_runner = ConnectRunner(
            rpi_parameters, "bash -c \"source ./rosbots_catkin_ws/devel/setup.bash; /home/pi/stop.sh\"")
        self.record_disconnect_runner.line.connect(self.read_data_line)
        self.record_disconnect_runner.error.connect(self.ssh_error)
        self.record_disconnect_runner.start()

    def record_line(self, line):
        """Append the Line to the record window and continue with further steps if necessary

        Arguments:
            line {str} -- The next line to append
        """
        self.t_record.append(line)
        if "Recording started" in line:  # The record script was successfully started
            self.record_runner.disconnect()  # Disconnect the record runner from appending lines
            alt = self.t_alt.text()  # Get altitude and speed information from textfields
            speed = self.t_speed.text()
            self.t_record.append("Starting Fly Script")
            # Start the Fly Script on the TX2
            tx2_parameters = self.setting_handler.get_tx2_settings()
            self.fly_runner = ConnectRunner(
                tx2_parameters, "bash -c \"source ~/doe_ws/devel/setup.bash; roslaunch dji_doe flight.launch alt:={} speed:={} 2>&1\"".format(alt, speed))
            self.fly_runner.line.connect(self.record_plain_line)
            self.fly_runner.error.connect(self.ssh_error)
            self.fly_runner.start()

            self.bt_read_data.setDisabled(False)  # Enable the Read Data Button
        elif "Starting sequence for flight" in line:
            # Get the current flight number
            regex_match = re.search("\d+", line)
            self.t_current_flight.setText(regex_match.group(0))

    def read_data(self):
        """Reads the current flight data from the Raspberry Pi and runs the Post-Processing
        """
        current = self.t_current_flight.text()
        self.t_record.append("Saving data to folder ./data")
        # Copy the latest bagfile to ./data/{FLIGHTNUMBER}
        mkdir = bash(
            'mkdir -p {}/data/{}'.format(self.cwd, current))
        rpi_parameters = self.setting_handler.get_rpi_settings()
        scp = bash('scp {0}@{1}:/home/pi/data/{2}.bag {3}/data/{2}/raw.bag'.format(
            rpi_parameters['user'], rpi_parameters['host'], current, self.cwd))
        if scp.code != 0:
            scp = bash('scp {0}@{1}:/home/pi/data/{2}.active.bag {3}/data/{2}/raw.bag'.format(
            rpi_parameters['user'], rpi_parameters['host'], current, self.cwd))
            if scp.code != 0:
                self.info_dialog.show_dialog("Could not read data, please read data manually via ssh/scp.", ok_only=True, message_type=1)
        self.bt_connect.setDisabled(True)
        self.info_dialog.show_dialog(
            "Successfully read the data. You can now turn the drone off. Clicking OK will disconnect automatically", ok_only=True, message_type=2)
        self.t_record.append("Running the post processing on the data")

        # Invoke the synchronization script
        self.data_runner = DataRunner(
            self.setting_handler.get_workspace_path(), '{}/data/{}'.format(self.cwd, current))
        self.data_runner.line.connect(self.record_post_line)
        self.data_runner.start()

    def read_data_line(self, line):
        """Handles the lines coming from the script killing the recording

        Arguments:
            line {str} -- The line to be read
        """
        self.t_record.append(line)
        if "killed" in line:
            try:
                del self.record_runner
            except:
                pass
            try:
                del self.record_disconnect_runner
            except:
                pass
            self.read_data()
            self.close_connection()

    def record_post_line(self, line):
        """Handles lines coming from the post processing script

        Arguments:
            line {str} -- The line to be read
        """
        self.t_record.append(line)
        if "Data postprocessing finished successfully" in line:
            self.bt_connect.setDisabled(False)

    def record_plain_line(self, line):
        """Records a plain text line to the record textarea without any logic

        Arguments:
            line {str} -- The line to be read
        """
        self.t_record.append(line)

    def connect(self):
        """Connect to the TX2 and run the authority script
        """
        # Load the Settings
        setting_values = self.setting_handler.get_ssh_settings()
        tx2_parameters = self.setting_handler.get_tx2_settings()
        self.command_runner = ConnectRunner(
            tx2_parameters, "bash -c \"source ~/doe_ws/devel/setup.bash; roslaunch dji_sdk sdk.launch 2>&1\"")
        self.command_runner.line.connect(self.command_line)
        self.command_runner.error.connect(self.ssh_error)
        self.command_runner.start()

    def close_connection(self):
        """Close all connections
        """
        try:
            del self.command_runner
        except:
            pass
        try:
            del self.record_runner
        except:
            pass
        try:
            del self.fly_runner
        except:
            pass
        self.connected = False
        self.t_current_flight.setDisabled(False)
        self.bt_read_manual.setDisabled(False)
        self.bt_connect.setText("Connect")
        self.parent.statusBar().showMessage("Disconnected")

    def bt_connect_action(self):
        """Action triggered by the "Connect Button"
        """
        if self.connected:
            # Disconnect all Runners from their SSH
            self.close_connection()
        else:
            # Clear the console output
            self.t_record.clear()
            self.t_control.clear()
            error_text = None
            self.parent.statusBar().showMessage("Connecting")
            self.bt_connect.setDisabled(True)
            self.t_current_flight.setDisabled(True)
            self.bt_read_manual.setDisabled(True)
            self.connect()

    def clear_fields(self):
        """Clears all fields and resets the GUI to it's default state
        """
        self.t_alt.clear()
        self.t_speed.clear()
        self.t_control.clear()
        self.t_record.clear()
        self.bt_connect.setDisabled(False)
        self.bt_fly.setDisabled(True)
        self.bt_read_data.setDisabled(True)
        self.bt_read_manual.setDisabled(False)
        self.t_current_flight.setDisabled(False)

    def bt_reset_action(self):
        """Action triggered by the "Reset" Button
        """
        # If still connected, disconnect all SSH connections
        self.close_connection()
        # Clear all textfields
        self.clear_fields()

    def start_recording(self):
        """Starts the Recording on the Raspberry Pi
        """
        rpi_parameters = self.setting_handler.get_rpi_settings()
        self.record_runner = ConnectRunner(
            rpi_parameters, "bash -c \"source ./rosbots_catkin_ws/devel/setup.bash; ~/record.sh flight 2>&1\"")
        self.record_runner.line.connect(self.record_line)
        self.record_runner.error.connect(self.ssh_error)
        self.record_runner.start()

    def try_start(self):
        """Try to start Recording giving the User 4 tries to switch to functional mode
        """
        res = self.info_dialog.show_dialog(
            "Starting. Please switch drone to Functional mode", message_type=1)
        if res:  # If the user said he is in functional mode
            self.bt_fly.setDisabled(True)
            self.bt_read_data.setDisabled(True)
            self.fly_cnt = 0
            self.start_recording()
        else:  # If the user still is not in functional mode
            self.fly_cnt = self.fly_cnt + 1  # Increase the counter
            self.t_record.append(
                "You have to switch the drone to functional mode first!")
            if self.fly_cnt > 3:  # 4th try did not succeed too
                self.fly_cnt = 0
                self.t_record.append(
                    "Too many failed attempts, please try again")
            else:
                self.try_start()

    def bt_fly_action(self):
        """Action triggered by the "Fly!" button
        """
        check_alt = False
        check_spd = False
        try:
            check_alt = DataCheck.check_flight_parameters(
                self.t_alt.text(), 25, 100)
            check_spd = DataCheck.check_flight_parameters(
                self.t_speed.text(), 4, 15)
        except ValueError:
            self.info_dialog.show_dialog(
                "You need to specify a valid altitude and speed first!", ok_only=True)
            return
        except EnvironmentError:
            answer = self.info_dialog.show_dialog("You specified parameters outside of the normal operating range.\nAltitude: {}\nSpeed: {}\nDo you want to continue?".format(
                self.t_alt.text(), self.t_speed.text()))
            if not answer:
                return
            check_alt = answer
            check_spd = answer
        feasible_data = check_alt and check_spd
        if self.connected and feasible_data:
            self.try_start()
        else:
            self.info_dialog.show_dialog(
                "You must connect to the drone first!", ok_only=True)

    def bt_read_manual_action(self):
        """Action triggered by the Read Data manually button
        """
        res = self.info_dialog.show_dialog(
            "This button is only meant for usage after a connection loss/Program crash and will read the data of flight number {}".format(self.t_current_flight.text()), message_type=1)
        if res:  # If user accepts message
            # Check if Flight number is a valid number
            if not DataCheck.check_input_fields(self.t_current_flight.text()):
                self.info_dialog.show_dialog(
                    "Invalid Flight Number", ok_only=True)
                return
            rpi_parameters = self.setting_handler.get_rpi_settings()
            self.record_disconnect_runner = ConnectRunner(
                rpi_parameters, "bash -c \"source ./rosbots_catkin_ws/devel/setup.bash; /home/pi/stop.sh\"")
            self.record_disconnect_runner.line.connect(self.read_data_line)
            self.record_disconnect_runner.error.connect(self.ssh_error)
            self.record_disconnect_runner.start()

    def initUI(self):
        """Initialize the UI
        """
        grid = QGridLayout()
        grid.setSpacing(10)

        self.parent.statusBar().showMessage("Disconnected")
        self.connected = False

        self.setLayout(grid)

        label_alt = QLabel("Altitude (m):")
        label_speed = QLabel("Speed (m/s):")
        label_current_flight = QLabel("Current flight:")

        self.t_alt = QLineEdit()
        self.t_speed = QLineEdit()
        self.t_current_flight = QLineEdit()

        grid.addWidget(label_alt, 0, 0)
        grid.addWidget(self.t_alt, 1, 0)

        grid.addWidget(label_speed, 2, 0)
        grid.addWidget(self.t_speed, 3, 0)

        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.VLine)
        vertical_line.setFrameShadow(QFrame.Sunken)

        grid.addWidget(vertical_line, 0, 1, 5, 1)

        self.bt_connect = QPushButton('Connect', self)
        self.bt_connect.clicked.connect(self.bt_connect_action)
        self.bt_fly = QPushButton("Fly!", self)
        self.bt_fly.clicked.connect(self.bt_fly_action)
        self.bt_fly.setDisabled(True)
        self.bt_read_data = QPushButton("Read Data", self)
        self.bt_read_data.clicked.connect(self.read_data_action)
        self.bt_read_data.setDisabled(True)
        self.bt_reset = QPushButton("Reset", self)
        self.bt_reset.clicked.connect(self.bt_reset_action)

        self.bt_read_manual = QPushButton(
            "Read Data manually (Broken Flight/Disconnected)", self)
        self.bt_read_manual.clicked.connect(self.bt_read_manual_action)

        grid.addWidget(self.bt_connect, 0, 2, 1, 2)
        grid.addWidget(self.bt_fly, 1, 2, 1, 2)
        grid.addWidget(self.bt_read_data, 2, 2, 1, 2)
        grid.addWidget(self.bt_reset, 3, 2, 1, 2)
        grid.addWidget(self.t_current_flight, 5, 2, 1, 2)
        grid.addWidget(self.bt_read_manual, 6, 2, 1, 2)

        splitter = QSplitter()

        self.t_control = QTextEdit()
        self.t_control.setReadOnly(True)
        splitter.addWidget(self.t_control)
        self.t_record = QTextEdit()
        self.t_record.setReadOnly(True)
        splitter.addWidget(self.t_record)

        grid.addWidget(splitter, 4, 0)
