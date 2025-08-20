from datetime import datetime



class AppDate:
    @staticmethod
    def get_current_date_header():
        """Returns current date string for display in the header."""
        return datetime.now().strftime('%d.%m.%Y')

    @staticmethod
    def get_transaction_timestamp():
        """Returns current datetime object for transaction records."""
        return datetime.now()


class FileHandling:
    @staticmethod
    def allowed_file(filename):
        ALLOWED_EXTENSIONS = {'xlsx'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
