class ServiceUnavailable(Exception):
    def __init__(self, code='model_unavailable'):
        self.code = code


class Conflict(Exception):
    pass
