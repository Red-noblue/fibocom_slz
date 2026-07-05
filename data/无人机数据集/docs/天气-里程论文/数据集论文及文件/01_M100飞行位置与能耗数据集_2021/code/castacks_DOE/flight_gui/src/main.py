import sys
import atexit
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon
from ConnectRunner import ConnectRunner
from PreferenceDialog import PreferenceDialog
from MainWidget import MainWidget
import Plots

"""Main Class for Flight GUI, starts the Application
DOE Project at Carnegie Mellon University's Robotics Institute
Year: 2019
Author: Bastian Wagner
"""
class MyWindow(QMainWindow):
    """Main Window Class, Wrapper for all Widgets
    """
    def __init__(self):
        """Constructor
        """
        super().__init__()
        self.settings = QSettings("CMU_RI", "DOE_FLIGHT_GUI")
        self.initUI()

    def settings_menu_triggered(self):
        """Opens the Settings Menu and reloads the Settings when they changed
        """
        preference_dialog = PreferenceDialog(self.settings, self)

        if preference_dialog.exec():
            self.settings = QSettings("CMU_RI", "DOE_FLIGHT_GUI")

    def initUI(self):
        """Initializes the UI of the Program
        """
        settingsAct = QAction(QIcon('settings.png'), '&Settings', self) # Menu Action for opening the Settings
        settingsAct.triggered.connect(self.settings_menu_triggered)

        self.statusBar() # Status bar showing whether the program is connected or not

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        fileMenu.addAction(settingsAct)

        self.setCentralWidget(MainWidget(self))
        self.setWindowTitle('DOE Flight GUI')
        self.showMaximized() # Show the GUI in Fullscreen

def render_plots_on_exit():
    print("Rendering plots")
    Plots.make_plots()

if __name__ == '__main__':
    app = QApplication(sys.argv) # Start the App
    win = MyWindow()
    atexit.register(render_plots_on_exit)
    sys.exit(app.exec_())
