from abc import abstractmethod, ABC

class MemoryLevel(ABC):
    def __init__(self, name, lower_level=None):
        self.name = name
        self.lower_level = lower_level

    @abstractmethod
    def get_stats(self):
       return dict()

    @abstractmethod
    def access(self, operation, address, line):
        raise NotImplementedError("This method should be overridden by subclasses")
