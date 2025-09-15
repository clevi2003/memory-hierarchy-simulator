from mem_hierarchy.mem_levels.data_structures.access_results import AccessResult
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


class MainMemoryLevel(MemoryLevel):
    def __init__(self):
        super().__init__("Main Memory")
        self.reads = 0
        self.writes = 0

    def access(self, operation, address, line):
        if operation == "R":
            self.reads += 1
        elif operation == "W":
            self.writes += 1
        else:
            raise ValueError(f"Unknown op: {operation}")
        return AccessResult(self.name, operation, address, True, 0, 0, 0)

    def get_stats(self):
        total = self.reads + self.writes
        return {
            "mem_accesses": total,
            "mem_reads": self.reads,
            "mem_writes": self.writes,
        }

class CacheLevel(MemoryLevel):
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

    def read_access(self, address, line):
        first_read = self.cache.probe("R", address)
        self.cache.reads += 1
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

    def write_access(self, address, line):
        self.cache.writes += 1
        # if write allocate write back, must ensure data is in lower level to enforce inclusion
        if self.lower_level and not self.cache.policy:
            lower_read = self.lower_level.access("R", address, line)
            if lower_read.evicted_entry:
                self.inclusion_policy.on_lower_eviction(self.cache, lower_read.evicted_entry.address)
        first_write = self.write_policy.on_write(self.cache, address)
        if first_write.hit:
            self.cache.write_hits += 1
        else:
            self.cache.write_misses += 1
        # write through or no write allocate miss, write to lower level
        if first_write.needs_lower_write and self.lower_level:
            self.lower_level.access("W", address, line)
        # if write caused dirty eviction, must write that to the lower level
        if first_write.evicted_entry and first_write.evicted_entry.dirty and self.lower_level:
            self.lower_level.access("W", first_write.evicted_entry.address, line)
        return first_write

    def access(self, operation, address, line):
        if operation == "R":
            return self.read_access(address, line)
        elif operation == "W":
            return self.write_access(address, line)
        else:
            raise ValueError(f"Unknown op: {operation}")

    def on_page_evicted(self, evicted_entry):
        self.cache.invalidate_page(evicted_entry)

    def get_stats(self):
        return self.cache.get_stats()

class PageTableLevel(MemoryLevel):
    def __init__(self, page_table, invalidation_bus, lower_level=None):
        super().__init__("Page Table", lower_level)
        self.page_table = page_table
        self.invalidation_bus = invalidation_bus
        self.lower_level = lower_level

    @staticmethod
    def update_line(translation_result, line):
        line.vpn = int(translation_result.vpn, 2)
        line.page_offset = int(translation_result.offset, 2)
        line.ppn = int(translation_result.ppn, 2)
        line.page_table_result = translation_result.hit

    def access(self, operation, address, line):
        translation_info = self.page_table.translate(address)
        self.update_line(translation_info, line)
        if translation_info.evicted_entry:
            self.invalidation_bus.publish_page_evicted(translation_info.evicted_entry)
        physical_address = translation_info.physical_address
        if self.lower_level:
            return self.lower_level.access(operation, physical_address, line)
        result = AccessResult(self.name, operation, address, translation_info.hit, translation_info.vpn, 0,
                              translation_info.offset, evicted_entry=translation_info.evicted_entry)
        return result

    def get_stats(self):
        return self.page_table.get_stats()



