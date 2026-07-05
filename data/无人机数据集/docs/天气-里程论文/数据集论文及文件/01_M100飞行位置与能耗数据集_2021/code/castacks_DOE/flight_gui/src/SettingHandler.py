from PyQt5.QtCore import QSettings


class SettingHandler:
    """Class for Handling the Settings of the program
    """
    def __init__(self):
        self.settings = QSettings("CMU_RI", "DOE_FLIGHT_GUI")

    def get_ssh_settings(self):
        """Returns the current SSH Parameters in a dict

        Returns:
            dict<str> -- The current SSH Parameters for the TX2 and RPI
        """
        tx2_ip = self.settings.value(
            "TX2_IP", defaultValue="192.168.8.10", type=str)
        tx2_user = self.settings.value(
            "TX2_USER", defaultValue="ubuntu", type=str)
        tx2_pw = self.settings.value(
            "TX2_PW", defaultValue="ubuntu", type=str)
        rpi_ip = self.settings.value(
            "RPI_IP", defaultValue="192.168.8.93", type=str)
        rpi_user = self.settings.value("RPI_USER", defaultValue="pi", type=str)
        rpi_pw = self.settings.value(
            "RPI_PW", defaultValue="theairlab", type=str)
        return {'tx2_ip': tx2_ip, 'tx2_user': tx2_user, 'tx2_pw': tx2_pw, 'rpi_ip': rpi_ip, 'rpi_user': rpi_user, 'rpi_pw': rpi_pw}

    def get_rpi_settings(self):
        """Get the SSH Parameters for the Raspberry Pi
        
        Returns:
            dict<str> -- The SSH Parameters for the Raspberry Pi
        """
        rpi_ip = self.settings.value(
            "RPI_IP", defaultValue="192.168.8.93", type=str)
        rpi_user = self.settings.value("RPI_USER", defaultValue="pi", type=str)
        rpi_pw = self.settings.value(
            "RPI_PW", defaultValue="IFORGOTTHEPASSWORD", type=str)
        return {'host': rpi_ip, 'user': rpi_user, 'pw': rpi_pw}
    
    def get_tx2_settings(self):
        """Get the SSH Parameters for the TX2
        
        Returns:
            dict<str> -- The SSH Parameters for the Tx2
        """
        tx2_ip = self.settings.value(
            "TX2_IP", defaultValue="192.168.8.10", type=str)
        tx2_user = self.settings.value(
            "TX2_USER", defaultValue="ubuntu", type=str)
        tx2_pw = self.settings.value(
            "TX2_PW", defaultValue="theairlab", type=str)
        return {'host': tx2_ip, 'user': tx2_user, 'pw': tx2_pw}

    def get_workspace_path(self):
        """Get the currently set workspace path
        
        Returns:
            str -- The workspace path
        """
        return self.settings.value("WS_PATH", defaultValue="NO PATH SET", type=str)

    def get_possible_keys(self):
        """Get all valid Setting keys
        
        Returns:
            [type] -- [description]
        """
        return ["TX2_IP", "TX2_USER", "TX2_PW", "RPI_IP", "RPI_USER", "RPI_PW", "WS_PATH"]

    def set_setting_value(self, key, value):
        """Sets a setting key with value
        
        Arguments:
            key {str} -- The key of the setting
            value {str} -- The value of the setting
        
        Raises:
            KeyError: The Key is not valid
            TypeError: The type of the value is not str
        """
        if key not in self.get_possible_keys():
            raise KeyError("Unsupported Setting Key")
            return
        if type(value) is not str:
            raise TypeError("Setting value must be of type str")
            return
        self.settings.setValue(key, value)

    def set_settings(self, tx2_ip, tx2_user, tx2_pw, rpi_ip, rpi_user, rpi_pw, ws_path):
        """Sets all settings
        
        Arguments:
            tx2_ip {str} -- TX2 IP
            tx2_user {str} -- TX2 User
            tx2_pw {str} -- TX2 Password
            rpi_ip {str} -- RPI IP
            rpi_user {str} -- RPI User
            rpi_pw {str} -- RPI Password
            ws_path {str} -- Workspace path
        """
        self.settings.setValue("TX2_IP", tx2_ip)
        self.settings.setValue("TX2_USER", tx2_user)
        self.settings.setValue("TX2_PW", tx2_pw)
        self.settings.setValue("RPI_IP", rpi_ip)
        self.settings.setValue("RPI_USER", rpi_user)
        self.settings.setValue("RPI_PW", rpi_pw)
        self.settings.setValue("WS_PATH", ws_path)
        del self.settings
        self.settings = QSettings("CMU_RI", "DOE_FLIGHT_GUI")
