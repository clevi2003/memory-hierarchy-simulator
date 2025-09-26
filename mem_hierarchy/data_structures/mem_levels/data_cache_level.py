from .level_core import MemoryLevel

class DataCacheLevel(MemoryLevel):
    def __init__(self, name, cache, write_policy, inclusion_policy, lower_level=None, invalidation_bus=None):
        super().__init__(name, lower_level)
        self.cache = cache
        self.write_policy = write_policy
        self.inclusion_policy = inclusion_policy
        if invalidation_bus:
            invalidation_bus.register_listener(self)

    @staticmethod
    def update_line(access_result, line):
        if access_result.level == "DC":
            line.dc_tag = int(access_result.tag)
            line.dc_index = int(access_result.index)
            line.dc_result = access_result.hit
        elif access_result.level == "L2":
            line.l2_tag = int(access_result.tag)
            line.l2_index = int(access_result.index)
            line.l2_result = access_result.hit

    def read_access(self, address, line, update_line):
        first_read = self.cache.probe("R", address)
        self.cache.reads += 1
        if update_line:
            self.update_line(first_read, line)
        # read hit
        if first_read.hit:
            self.cache.read_hits += 1
            return first_read
        # read miss, access lower level
        self.cache.read_misses += 1
        if self.lower_level:
            lower_read = self.lower_level.access("R", address, line)
            # if lower level evicted something, enforce inclusion
            if lower_read.evicted_entry:
                #self.inclusion_policy.on_lower_eviction(self.cache, lower_read.evicted_entry)
                self.inclusion_policy.on_lower_eviction(self.cache, lower_read.evicted_entry.address)
        # now put data into this level's cache
        back_filled = self.cache.back_fill("R", address)
        # if backfill evicted something dirty, write it back to lower level
        if back_filled.evicted_entry and back_filled.evicted_entry.dirty and self.lower_level:
            self.lower_level.access("W", back_filled.evicted_entry.address, line)
        return back_filled

    def write_access(self, address, line, update_line):
        self.cache.writes += 1
        first_write = self.write_policy.on_write(self.cache, address)
        # if write allocate write back, must ensure data is in lower level to enforce inclusion
        if self.lower_level and not self.cache.policy:
            update_line_lower = not first_write.hit
            lower_read = self.lower_level.access("R", address, line, update_line=update_line_lower)
            if lower_read.evicted_entry:
                self.inclusion_policy.on_lower_eviction(self.cache, lower_read.evicted_entry.address)
        # write through or no write allocate miss, write to lower level
        if first_write.needs_lower_write and self.lower_level:
            self.lower_level.access("W", address, line)
        # if write caused dirty eviction, must write that to the lower level
        if first_write.evicted_entry and first_write.evicted_entry.dirty and self.lower_level:
            self.lower_level.access("W", first_write.evicted_entry.address, line)
        if update_line:
            self.update_line(first_write, line)
        return first_write

    def access(self, operation, address, line, update_line=True):
        if operation == "R":
            return self.read_access(address, line, update_line)
        elif operation == "W":
            return self.write_access(address, line, update_line)
        else:
            raise ValueError(f"Unknown op: {operation}")

    def on_page_evicted(self, evicted_entry):
        self.cache.invalidate_page(evicted_entry)

    def get_stats(self):
        return self.cache.get_stats()