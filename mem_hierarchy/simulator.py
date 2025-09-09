from .cache import DataCache, L2Cache
from .levels import MainMemoryLevel, CacheLevel
from trace_parser import TraceParser
from .policies import WriteThroughNoWriteAllocate, InclusivePolicy, WriteBackWriteAllocate
from pprint import pprint
from .access_results import AccessLine

class MemoryHierarchySimulator:
    def __init__(self, config):
        self.config = config
        self.bits = self.config.bits
        self.memory = MainMemoryLevel()
        lower_for_next_level = self.memory
        # setup for L2 cache if applicable
        if self.config.l2_enabled:
            if config.l2.policy:
                l2_write_policy = WriteThroughNoWriteAllocate()
            else:
                l2_write_policy = WriteBackWriteAllocate()
            self.l2 = CacheLevel("l2", L2Cache(config), l2_write_policy, InclusivePolicy(), lower_level=lower_for_next_level)
            lower_for_next_level = self.l2
        else:
            lower_for_next_level = self.memory
            self.l2 = None
        #setup for data cache
        if config.dc.policy:
            dc_write_policy = WriteThroughNoWriteAllocate()
        else:
            dc_write_policy = WriteBackWriteAllocate()
        self.dc = CacheLevel("dc", DataCache(config), dc_write_policy, InclusivePolicy(), lower_level=lower_for_next_level)

    def simulate(self, trace):
        print("Virtual  Virt.  Page TLB    TLB TLB  PT   Phys        DC  DC          L2  L2")
        print("Address  Page # Off  Tag    Ind Res. Res. Pg # DC Tag Ind Res. L2 Tag Ind Res.")
        print("-------- ------ ---- ------ --- ---- ---- ---- ------ --- ---- ------ --- ----")
        for operation, address in TraceParser(trace):
            line = AccessLine(address)
            self.dc.access(operation, address, line)
            #print("-------- ------ ---- ------ --- ---- ---- ---- ------ --- ---- ------ --- ----")
            print(line)
            #line.pprint()
        print("Simulation statistics")
        self.pprint_stats()

    def get_stats(self):
        stats = {"data_cache": self.dc.get_stats(),
                 "main_memory": self.memory.get_stats()}
        if self.l2:
            stats["l2"] = self.l2.get_stats()
        return stats

    def pprint_stats(self):
        stats = self.get_stats()
        pprint(stats)

