from .cache import DataCache, L2Cache
from trace_parser import TraceParser

class MemoryHierarchySimulator:
    def __init__(self, config):
        self.config = config
        self.bits = self.config.bits
        self.data_cache = DataCache(self.config)
        # setup L2 cache
        self.l2 = None
        if self.config.l2_enabled:
            self.l2 = L2Cache(self.config)

    def simulate(self, trace):
        for operation, address in TraceParser(trace):
            self.access_memory(operation, address)
        self.pprint_stats()


    def read_access(self, address):
        # check data cache first
        dc_read = self.data_cache.probe("R", address)
        if dc_read.hit:
            return
        # next check L2 if applicable
        if self.l2:
            l2_read = self.l2.probe("R", address)
            # handle l2 miss
            if not l2_read.hit:



    def access_memory(self, operation, address):
        if operation == 'R':
            self.read_access(address)
        elif operation == 'W':
            return self.data_cache.write(address)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def get_stats(self):
        stats = {"data_cache": self.data_cache.get_stats()}
        return stats

    def pprint_stats(self):
        stats = self.get_stats()
        print("Data Cache Stats:")
        for stat, value in stats["data_cache"].items():
            print(f"  {stat}: {value}")

