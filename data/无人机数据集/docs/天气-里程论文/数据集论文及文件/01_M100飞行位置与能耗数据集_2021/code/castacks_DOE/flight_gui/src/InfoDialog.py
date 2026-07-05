from PyQt5.QtWidgets import QMessageBox


class InfoDialog(QMessageBox):
    """Simple Class to show a QMessageBox
    """
    def show_dialog(self, message, ok_only=False, message_type=0):
        """Shows a QMessageBox
        Possible Message Types:
            0 (Default/Fallback) - Error
            1 - Warning
            2 - Info
        Arguments:
            message {str} -- The message to be shown in the Message box
        
        Keyword Arguments:
            ok_only {bool} -- Only show the "OK" Button? (default: {False})
            message_type {int} -- The Message type (default: {0})
        
        Returns:
            bool -- True - "OK"; False - "Abort"
        """
        options = self.Ok | self.Abort
        if ok_only:
            options = self.Ok
        ret = self.Abort

        if message_type is 1:
            ret = self.warning(self, "Warning", message, options)
        elif message_type is 2:
            ret = self.information(self, "Info", message, options)
        else:
            ret = self.critical(self, "Error", message, options)
        
        if ret == self.Ok:
            return True
        else:
            return False
