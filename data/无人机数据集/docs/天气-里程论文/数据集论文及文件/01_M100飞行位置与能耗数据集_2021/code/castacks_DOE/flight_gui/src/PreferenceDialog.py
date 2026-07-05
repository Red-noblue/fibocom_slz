from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QLabel, QPushButton, QLineEdit, QFileDialog)
from PyQt5.QtCore import QSettings
from SettingHandler import SettingHandler

"""Package containing the Settings Dialog
"""


class PreferenceDialog(QDialog):
    """The Settings Dialog
    """

    def __init__(self, settings, parent=None):
        """Constructor

        Arguments:
            settings {QSettings} -- The QSettings to use

        Keyword Arguments:
            parent {QWidget} -- The parent widget (default: {None})
        """
        super().__init__()
        self.setting_handler = SettingHandler()
        self.initUI()

    def save_settings(self):
        """Save the stting values, triggered by the "Save" button
        """
        self.setting_handler.set_settings(self.t_tx2_ip.text(), 
                                          self.t_tx2_user.text(), 
                                          self.t_tx2_pw.text(), 
                                          self.t_rpi_ip.text(), 
                                          self.t_rpi_user.text(), 
                                          self.t_rpi_pw.text(), 
                                          self.t_ws_path.text()
                                        )
        self.accept()

    def select_path(self):
        """Select the workspace path
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)

        if dialog.exec_():
            filenames = dialog.selectedFiles()
            self.t_ws_path.setText(filenames[0])

    def initUI(self):
        """Initialize the UI
        """
        setting_values = self.setting_handler.get_ssh_settings()
        tx2_ip = setting_values['tx2_ip']
        tx2_user = setting_values['tx2_user']
        tx2_pw = setting_values['tx2_pw']
        rpi_ip = setting_values['rpi_ip']
        rpi_user = setting_values['rpi_user']
        rpi_pw = setting_values['rpi_pw']
        workspace_path = self.setting_handler.get_workspace_path()

        grid = QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        self.bt_save = QPushButton('Save Settings', self)
        self.bt_save.clicked.connect(self.save_settings)

        self.bt_path = QPushButton('Select Workspace Path', self)
        self.bt_path.clicked.connect(self.select_path)

        label_tx2_ip = QLabel("TX2 IP:")
        label_tx2_user = QLabel("TX2 User:")
        label_tx2_pw = QLabel("TX2 Password:")
        label_rpi_ip = QLabel("RPI IP:")
        label_rpi_user = QLabel("RPI User:")
        label_rpi_pw = QLabel("RPI Password:")
        label_ws_path = QLabel("Workspace Path:")

        self.t_tx2_ip = QLineEdit(tx2_ip)
        self.t_tx2_user = QLineEdit(tx2_user)
        self.t_tx2_pw = QLineEdit(tx2_pw)
        self.t_rpi_ip = QLineEdit(rpi_ip)
        self.t_rpi_user = QLineEdit(rpi_user)
        self.t_rpi_pw = QLineEdit(rpi_pw)
        self.t_ws_path = QLineEdit(workspace_path)
        self.t_ws_path.setReadOnly(True)

        grid.addWidget(label_tx2_ip, 0, 0)
        grid.addWidget(self.t_tx2_ip, 0, 1)
        grid.addWidget(label_tx2_user, 1, 0)
        grid.addWidget(self.t_tx2_user, 1, 1)
        grid.addWidget(label_tx2_pw, 2, 0)
        grid.addWidget(self.t_tx2_pw, 2, 1)
        grid.addWidget(label_ws_path, 3, 0)
        grid.addWidget(self.t_ws_path, 3, 1, 1, 2)

        grid.addWidget(label_rpi_ip, 0, 2)
        grid.addWidget(self.t_rpi_ip, 0, 3)
        grid.addWidget(label_rpi_user, 1, 2)
        grid.addWidget(self.t_rpi_user, 1, 3)
        grid.addWidget(label_rpi_pw, 2, 2)
        grid.addWidget(self.t_rpi_pw, 2, 3)
        grid.addWidget(self.bt_path, 3, 3)

        grid.addWidget(self.bt_save, 4, 0, 1, 4)

        self.setGeometry(300, 300, 600, 150)
        self.setWindowTitle("Settings")
        self.show()
