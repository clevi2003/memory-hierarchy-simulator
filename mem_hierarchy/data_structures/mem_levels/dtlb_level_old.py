from ..caches import DTLB
from .level_core import MemoryLevel

class DTLBLevel(MemoryLevel):
    def __init__(self, dtlb_cache, fallback, lower_level=None, invalidation_bus=None):
        super().__init__("DTLB", lower_level)
        self.dtlb_cache = dtlb_cache
        if invalidation_bus:
            invalidation_bus.register_listener(self)
        self.fallback = fallback

    @staticmethod
    def update_line(access_result, line):
        line.dtlb_tag = int(access_result.tag)
        line.dtlb_index = int(access_result.index)
        line.dtlb_result = access_result.hit


    def access(self, operation, address, line):
        first_read = self.dtlb_cache.probe("R", address)
        self.dtlb_cache.reads += 1
        self.update_line(first_read, line)
        # read hit
        if first_read.hit:
            self.dtlb_cache.read_hits += 1
            self.fallback.fallback_access(address, line, physical_address=first_read.addr)
            physical_address = first_read.addr
            #page_offset = physical_address[self.dtlb_cache.ppn:]
            return self.lower_level.access(operation, address, line, physical_address=physical_address)
        else:
            # read miss get physical address from fallback page table
            self.dtlb_cache.read_misses += 1
            translation_info = self.fallback.fallback_access(address, line)
            physical_address = translation_info.physical_address
            # put data into this level's cache
            back_filled = self.dtlb_cache.back_fill(address, physical_address)
            if back_filled.evicted_entry:
                self.dtlb_cache.evictions += 1
            return self.lower_level.access(operation, address, line)

    def get_stats(self):
        return self.dtlb_cache.get_stats()