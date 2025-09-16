from .level_core import MemoryLevel

class DTLBLevel(MemoryLevel):
    def __init__(self, dtlb_cache, lower_level=None, invalidation_bus=None):
        super().__init__("DTLB", lower_level)
        self.dtlb_cache = dtlb_cache
        if invalidation_bus:
            invalidation_bus.register_listener(self)

    @staticmethod
    def update_line(access_result, line):
        line.dtlb_tag = int(access_result.tag)
        line.dtlb_index = int(access_result.index)
        line.dtlb_result = access_result.hit

    def access(self, operation, address, line):
        if operation == "R":
            return self.read_access(address, line)
        elif operation == "W":
            return self.write_access(address, line)
        else:
            raise ValueError(f"Unknown op: {operation}")

    def read_access(self, address, line):
        first_read = self.dtlb_cache.probe("R", address)
        self.dtlb_cache.reads += 1
        self.update_line(first_read, line)
        # read hit
        if first_read.hit:
            self.dtlb_cache.read_hits += 1
        else:
            # read miss page table handles this
            self.dtlb_cache.read_misses += 1
        return first_read

    def write_access(self, address, translation_info):
        self.dtlb_cache.writes += 1

        back_filled = self.dtlb_cache.back_fill(address, translation_info.ppn)
        if back_filled.evicted_entry:
            self.dtlb_cache.evictions += 1

    def get_stats(self):
        return self.dtlb_cache.get_stats()