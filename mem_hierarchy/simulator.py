from trace_parser import TraceParser  # if you move it under package
from mem_hierarchy.data_structures.caches.data_cache import DCCache, L2Cache
from mem_hierarchy.data_structures.caches.translation_cache import DTLB
from mem_hierarchy.data_structures.mem_levels.dtlb_level import DTLBLevel
from mem_hierarchy.data_structures.mem_levels.data_cache_level import DataCacheLevel
from mem_hierarchy.data_structures.mem_levels.main_mem_level import MainMemoryLevel
from mem_hierarchy.data_structures.mem_levels.virtual_memory_level import VirtualMemoryLevel
from mem_hierarchy.data_structures.virtual_mem.page_table import PageTable
from mem_hierarchy.data_structures.result_structures.access_results import AccessLine
from mem_hierarchy.protocols.policies import WriteBackWriteAllocate, WriteThroughNoWriteAllocate, InclusivePolicy
from mem_hierarchy.protocols.invalidation_bus import InvalidationBus

class MemoryHierarchySimulator:
    """Simulates a memory hierarchy based on the provided configuration."""
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
            self.l2 = DataCacheLevel("l2", L2Cache(config), l2_write_policy, InclusivePolicy(),
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
        self.dc = DataCacheLevel("dc", DCCache(config), dc_write_policy, InclusivePolicy(),
                                 invalidation_bus=invalidation_bus, lower_level=lower_for_next_level)
        lower_for_next_level = self.dc
        self.top_level = self.dc
        # setup for page table if applicable
        if config.virtual_addresses:
            # setup for DTLB if applicable
            self.dtlb = None
            if config.dtlb_enabled:
                self.dtlb = DTLBLevel(DTLB(config), lower_level=None, invalidation_bus=invalidation_bus)
            self.pt = VirtualMemoryLevel(PageTable(config), invalidation_bus, dtlb_level=self.dtlb, lower_level=lower_for_next_level)
            self.top_level = self.pt

        self.reads = 0
        self.writes = 0

    def simulate(self, trace):
        """
        Core simulator functionality, simulates the memory hierarchy using the provided trace file.
        :param trace: trace file path
        :return: None
        """
        print("Virtual  Virt.  Page TLB    TLB TLB  PT   Phys        DC  DC          L2  L2")
        print("Address  Page # Off  Tag    Ind Res. Res. Pg # DC Tag Ind Res. L2 Tag Ind Res.")
        print("-------- ------ ---- ------ --- ---- ---- ---- ------ --- ---- ------ --- ----")
        for operation, int_address, hex_address in TraceParser(trace, addr_bits=self.config.address_bits):
            address = bin(int_address)[2:].zfill(self.config.address_bits)
            if len(address) > self.config.address_bits:
                print(f"Address {hex_address} exceeds the configured address bits {self.config.address_bits}")
                continue
                # raise ValueError(f"Address {hex_address} exceeds the configured address bits {self.config.address_bits}")
            if operation == "R":
                self.reads += 1
            elif operation == "W":
                self.writes += 1
            else:
                raise ValueError(f"Unknown op: {operation}")
            # have line get passed through the hierarchy to collect info
            line = AccessLine(address)
            self.top_level.access(operation, int_address, line)
            print(line)
        print("\nSimulation statistics\n")
        self.pprint_stats()

    def get_stats(self):
        """
        Gathers and returns stats from all levels of the memory hierarchy.
        :return: dict of stats
        """
        stats = dict()
        if self.dtlb:
            stats['dtlb'] = self.dtlb.get_stats()
        if self.pt:
            stats['page table'] = self.pt.get_stats()
        stats["dc"] = self.dc.get_stats()
        if self.l2:
            stats["l2"] = self.l2.get_stats()
        stats["reads"] = self.reads
        stats["writes"] = self.writes
        stats["read ratio"] = self.reads / (self.reads + self.writes) if (self.reads + self.writes) > 0 else 0
        stats["main memory"] = self.memory.get_stats()

        return stats

    def pprint_stats(self):
        """
        Pretty prints the stats from all levels of the memory hierarchy.
        :return: None
        """
        stats = self.get_stats()
        stat_str = ""
        dtlb_stats = stats.get('dtlb', None)
        if dtlb_stats:
            stat_str += "dtlb hits        : " + str(dtlb_stats['hits']) + "\n"
            stat_str += "dtlb misses      : " + str(dtlb_stats['misses']) + "\n"
            stat_str += "dtlb hit rate    : " + f"{dtlb_stats['hit rate']:.6f}" + "\n\n"
        pt_stats = stats.get('page table', None)
        if pt_stats:
            stat_str += "pt hits          : " + str(pt_stats['hits']) + "\n"
            stat_str += "pt misses        : " + str(pt_stats['misses']) + "\n"
            stat_str += "pt hit rate      : " + f"{pt_stats['hit rate']:.6f}" + "\n\n"
        dc_stats = stats.get('dc', None)
        stat_str += "dc hits          : " + str(dc_stats['hits']) + "\n"
        stat_str += "dc misses        : " + str(dc_stats['misses']) + "\n"
        stat_str += "dc hit rate      : " + f"{dc_stats['hit rate']:.6f}" + "\n\n"
        l2_stats = stats.get('l2', None)
        if l2_stats:
            stat_str += "L2 hits         : " + str(l2_stats['hits']) + "\n"
            stat_str += "L2 misses       : " + str(l2_stats['misses']) + "\n"
            stat_str += "L2 hit rate     : " + f"{l2_stats['hit rate']:.6f}" + "\n\n"
        stat_str += "Total reads      : " + str(stats['reads']) + "\n"
        stat_str += "Total writes     : " + str(stats['writes']) + "\n"
        stat_str += "Ratio of reads   : " + f"{stats['read ratio']:.6f}" + "\n\n"
        stat_str += "main memory refs : " + str(stats['main memory']['mem_accesses']) + "\n"
        stat_str += "page table refs  : " + str(stats['page table']['accesses']) + "\n" if pt_stats else ""
        stat_str += "disk refs        : " + str(stats['page table']['disk refs']) + "\n" if pt_stats else ""
        print(stat_str)

