class AppError(Exception):
    def __init__(self, message: str = "application error") -> None:
        super().__init__(message)
        self.message = message
