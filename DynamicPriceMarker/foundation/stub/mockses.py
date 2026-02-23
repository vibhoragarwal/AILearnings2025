""" Versy siple class to mock SES - but only from caller side. Does nto publish anuthing for real """




class MockSES:
    """ Simple Mock for SES -- for now one mail"""

    def __init__(self, settings):
        self.configSet = settings.get("configSet", "ses-mockConfigSet") if settings else "ses-mockConfigSet"
        self.message_id = 0

    def send_mail(self, message):
        """ SES to send mock mail
        Returns:
            valid Message ID
        """
        message = "This is mock mail"
        self.message_id = 1
        print(f"Sending to Mock SES {self.configSet}: {message}")
        return str(self.message_id)
