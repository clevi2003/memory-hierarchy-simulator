from mem_hierarchy.mem_levels.data_structures.caches.cache import DataCache, L2Cache
from mem_hierarchy.mem_levels.levels import MainMemoryLevel, CacheLevel, PageTableLevel
from trace_parser import TraceParser
from mem_hierarchy.protocols.policies import WriteThroughNoWriteAllocate, InclusivePolicy, WriteBackWriteAllocate
from pprint import pprint
from mem_hierarchy.mem_levels.data_structures.access_results import AccessLine
from mem_hierarchy.mem_levels.data_structures.page_table import PageTable
from mem_hierarchy.protocols.invalidation_bus import InvalidationBus

class MemoryHierarchySimulator:
    def __init__(self, config):
        self.config = config
        self.bits = self.config.bits
        self.memory = MainMemoryLevel()
        self.top_level = self.memory
        invalidation_bus = InvalidationBus()
        lower_for_next_level = self.top_level
        # setup for L2 cache if applicable
        if self.config.l2_enabled:
            if config.l2.policy:
                l2_write_policy = WriteThroughNoWriteAllocate()
            else:
                l2_write_policy = WriteBackWriteAllocate()
            self.l2 = CacheLevel("l2", L2Cache(config), l2_write_policy, InclusivePolicy(),
                                 invalidation_bus=invalidation_bus, lower_level=lower_for_next_level)
            lower_for_next_level = self.l2
            self.top_level = self.l2
        else:
            self.l2 = None
        # setup for data cache
        if config.dc.policy:
            dc_write_policy = WriteThroughNoWriteAllocate()
        else:
            dc_write_policy = WriteBackWriteAllocate()
        self.dc = CacheLevel("dc", DataCache(config), dc_write_policy, InclusivePolicy(),
                                 invalidation_bus=invalidation_bus, lower_level=lower_for_next_level)
        lower_for_next_level = self.dc
        self.top_level = self.dc
        # setup for page table if applicable
        if config.virtual_addresses:
            self.pt = PageTableLevel(PageTable(config), invalidation_bus, lower_level=lower_for_next_level)
            self.top_level = self.pt
            lower_for_next_level = self.pt

    def simulate(self, trace):
        print("Virtual  Virt.  Page TLB    TLB TLB  PT   Phys        DC  DC          L2  L2")
        print("Address  Page # Off  Tag    Ind Res. Res. Pg # DC Tag Ind Res. L2 Tag Ind Res.")
        print("-------- ------ ---- ------ --- ---- ---- ---- ------ --- ---- ------ --- ----")
        for operation, address in TraceParser(trace, addr_bits=self.config.address_bits):
            line = AccessLine(address)
            self.top_level.access(operation, address, line)
            #print("-------- ------ ---- ------ --- ---- ---- ---- ------ --- ---- ------ --- ----")
            print(line)
        print("Simulation statistics")
        #self.pprint_stats()

    def get_stats(self):
        stats = {"data_cache": self.dc.get_stats(),
                 "main_memory": self.memory.get_stats()}
        if self.l2:
            stats["l2"] = self.l2.get_stats()
        return stats

    def pprint_stats(self):
        stats = self.get_stats()
        pprint(stats)

