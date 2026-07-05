class DataCheck:
    """Class for general data checks
    """
    @staticmethod
    def check_input_fields(text):
        """Check if an input field is a number and not empty
        
        Arguments:
            text {str} -- The value of the input field
        
        Returns:
            bool -- True - Valid Input; False - Invalid Input
        """
        empty = text is not ""
        try:
            num = float(text)
        except ValueError:
            return False
        return True and empty

    @staticmethod
    def check_flight_parameters(text, min, max):
        """Check if an input field is a valid entry for the flight parameters
        
        Arguments:
            text {str} -- The value of the input field
            min {float} -- The lower end of the range
            max {float} -- The maximum of the range
        """
        empty = text is not ""
        num = float(text)
        if num < min or num > max:
            raise EnvironmentError("Not inside range")
        return True and empty