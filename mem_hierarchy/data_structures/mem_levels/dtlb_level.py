from .level_core import MemoryLevel

class DTLBLevel(MemoryLevel):
    def __init__(self, dtlb_cache, lower_level=None, invalidation_bus=None):
        super().__init__("DTLB", lower_level)
        self.dtlb_cache = dtlb_cache
        if invalidation_bus:
            invalidation_bus.register_listener(self)

    # def invalidate_page(self, evicted_entry):
    #     self.dtlb_cache.invalidate(evicted_entry)

    def on_page_evicted(self, evicted_entry):
        vpn = getattr(evicted_entry, "vpn", None)
        if vpn is None:
            # Fallback: derive from PPN only if you maintain a reverse map; otherwise bail quietly.
            return
        self.dtlb_cache.invalidate_vpn(vpn)

    @staticmethod
    def update_line(access_result, line):
        line.dtlb_tag = access_result.tag
        line.dtlb_index = access_result.index
        line.dtlb_result = access_result.hit

    def access(self, operation, address, line):
        if operation == "R":
            return self.read_access(address, line)
        elif operation == "W":
            return self.write_access(address, line)
        else:
            raise ValueError(f"Unknown op: {operation}")

    def read_access(self, address, line):
        result = self.dtlb_cache.probe("R", int(address))
        self.dtlb_cache.reads += 1
        self.update_line(result, line)
        if result.hit:
            self.dtlb_cache.read_hits += 1
        else:
            self.dtlb_cache.read_misses += 1
        return result

    def write_access(self, address, translation_info):
        self.dtlb_cache.writes += 1
        backfill_result = self.dtlb_cache.backfill(address, translation_info.physical_address)
        if backfill_result.evicted_entry:
            self.dtlb_cache.evictions += 1

    def get_stats(self):
        return self.dtlb_cache.get_stats()




# class DTLBLevel(MemoryLevel):
#     def __init__(self, dtlb_cache, lower_level=None, invalidation_bus=None):
#         super().__init__("DTLB", lower_level)
#         self.dtlb_cache = dtlb_cache
#         if invalidation_bus:
#             invalidation_bus.register_listener(self)
#
#     @staticmethod
#     def update_line(access_result, line):
#         line.dtlb_tag = int(access_result.tag)
#         line.dtlb_index = int(access_result.index)
#         line.dtlb_result = access_result.hit
#
#     def access(self, operation, address, line):
#         if operation == "R":
#             return self.read_access(address, line)
#         elif operation == "W":
#             return self.write_access(address, line)
#         else:
#             raise ValueError(f"Unknown op: {operation}")
#
#     def read_access(self, address, line):
#         first_read = self.dtlb_cache.probe("R", address)
#         self.dtlb_cache.reads += 1
#         self.update_line(first_read, line)
#         # read hit
#         if first_read.hit:
#             self.dtlb_cache.read_hits += 1
#         else:
#             # read miss page table handles this
#             self.dtlb_cache.read_misses += 1
#         return first_read
#
#     def write_access(self, address, translation_info):
#         self.dtlb_cache.writes += 1
#         #print("translated p address:", translation_info.physical_address)
#         # print("from v address:", address)
#         back_filled = self.dtlb_cache.back_fill(address, translation_info.physical_address)
#         if back_filled.evicted_entry:
#             self.dtlb_cache.evictions += 1
#
#     def get_stats(self):
#         return self.dtlb_cache.get_stats()