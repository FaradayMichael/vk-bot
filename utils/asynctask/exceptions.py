from .models import (
    ExceptionData
)


class TaskBaseException(Exception):
    pass


class TaskReturned(TaskBaseException):
    pass


class TaskCanceled(TaskBaseException):
    pass


class TaskNoHandler(TaskBaseException):
    pass


class TaskException(TaskBaseException):
    def __init__(self, exc: ExceptionData):
        super().__init__(f'{exc.t.value}:{exc.cls} {exc.message}')
        self.cls = exc.cls
        self.t = exc.t
        self.data = exc.data


class TaskError(TaskBaseException):
    pass
