from .level_core import MemoryLevel
from ...protocols import WriteBackWriteAllocate
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class DataCacheLevel(MemoryLevel):
    def __init__(self, name, cache, write_policy, inclusion_policy, lower_level=None, invalidation_bus=None):
        super().__init__(name, lower_level)
        self.cache = cache
        self.write_policy = write_policy
        self.inclusion_policy = inclusion_policy
        self.runtime_writebacks = 0
        if invalidation_bus:
            invalidation_bus.register_listener(self)
        self.inclusions = 0

    @staticmethod
    def update_line(access_result, line):
        if access_result.level == "DC":
            line.dc_tag = int(access_result.tag)
            line.dc_index = int(access_result.index)
            line.dc_result = access_result.hit
        elif access_result.level in ["L2", "l2"]:
            line.l2_tag = int(access_result.tag)
            line.l2_index = int(access_result.index)
            line.l2_result = access_result.hit

    def lower_eviction_inclusion(self, lower_read, line):
        if lower_read.evicted_entry and hasattr(self.lower_level, "cache"):
            hit, was_dirty = self.inclusion_policy.on_lower_eviction(
                self.cache, lower_read.evicted_entry.address
            )
            if hit and was_dirty:
                # push dirty data downward
                self.lower_level.access("W", lower_read.evicted_entry.address, line,
                                        origin=self.name + " read miss lower eviction enforce inclusion (writeback)",
                                        is_writeback=True)
                self.runtime_writebacks += 1

    def manage_backfill(self, address, line):
        back_filled = self.cache.back_fill("R", address)

        # if backfill evicted a dirty line, write it down to lower level
        if back_filled.evicted_entry and back_filled.evicted_entry.dirty and self.lower_level:
            self.lower_level.access("W", back_filled.evicted_entry.address, line,
                                    origin=self.name + " read miss backfill dirty eviction so writeback",
                                    is_writeback=True)
            self.runtime_writebacks += 1
        return back_filled

    def read_access(self, address, line, update_line):
        first_read = self.cache.probe("R", address, update_mru=True)
        self.cache.reads += 1
        if update_line:
            self.update_line(first_read, line)

        if first_read.hit:
            self.cache.read_hits += 1
            if self.lower_level and hasattr(self.lower_level, "cache"):
                self.lower_level.cache.probe("R", address, update_mru=True)
            return first_read

        # miss
        self.cache.read_misses += 1
        self.cache.l2_read_miss_calls += 1

        if self.lower_level:
            lower_read = self.lower_level.access("R", address, line,
                                                 origin=self.name + " read miss so lower read")
            # inclusion on lower eviction
            self.lower_eviction_inclusion(lower_read, line)

        return self.manage_backfill(address, line)

    def _write_back(self, address, line, update_line, **kwargs):
        pre = self.cache.probe("W", address, update_mru=True)
        if pre.hit:
            self.cache.write_hits += 1
            self.cache.mark_dirty(address)
            if line and update_line:
                self.update_line(pre, line)
            return pre
        if self.lower_level:
            self.lower_level.access("W", address, line,
                                    origin=(kwargs.get("origin") or (self.name + " pass-through writeback")),
                                    is_writeback=True)
        base = self.cache._block_base(address)
        tag, index, offset = self.cache.parse_address(base)
        return AccessResult(self.cache.name, "W", base, True, tag, index, offset)

    def _rfo(self, address, line, is_wb_wa, pre):
        if self.lower_level and is_wb_wa and not pre.hit:
            lower_read = self.lower_level.access(
                "R", address, line, update_line=True,
                origin=self.name + " write miss RFO"
            )
            if hasattr(self.lower_level, "cache") and lower_read.evicted_entry:
                hit, was_dirty = self.inclusion_policy.on_lower_eviction(
                    self.cache, lower_read.evicted_entry.address
                )
                if hit and was_dirty:
                    self.lower_level.access(
                        "W", lower_read.evicted_entry.address, line,
                        origin=self.name + " inclusion dirty writeback",
                        is_writeback=True
                    )
                    self.runtime_writebacks += 1

    def write_access(self, address, line, update_line, **kwargs):
        is_wb = kwargs.get("is_writeback", False)
        if is_wb:
            return self._write_back(address, line, update_line, **kwargs)

        is_wb_wa = isinstance(self.write_policy, WriteBackWriteAllocate)
        pre = self.cache.probe("W", address, update_mru=False)

        # Miss RFO first
        self._rfo(address, line, is_wb_wa, pre)

        # Write according to policy
        first_write = self.write_policy.on_write(self.cache, address, is_writeback=False)

        # If the policy needs a lower write (WT/NWA), propagate it down
        if first_write.needs_lower_write and self.lower_level:
            self.lower_level.access("W", address, line,
                                    origin=self.name + " write needs lower write")

        # If this level evicted a dirty victim, write it back
        if first_write.evicted_entry and first_write.evicted_entry.dirty and self.lower_level:
            self.lower_level.access(
                "W", first_write.evicted_entry.address, line,
                origin=self.name + " write back dirty eviction",
                is_writeback=True
            )

        if line and update_line:
            self.update_line(first_write, line)
        return first_write

    def access(self, operation, address, line, update_line=True, origin=None, **kwargs):
        if operation == "R":
            return self.read_access(address, line, update_line)
        elif operation == "W":
            return self.write_access(address, line, update_line, **kwargs)
        else:
            raise ValueError(f"Unknown op: {operation}")

    def on_page_evicted(self, evicted_entry):
        entries_in_page = self.cache.entries_in_page(evicted_entry)

        # for each dirty entry, write back to lower (L2) as a WRITEBACK
        for entry in entries_in_page:
            if entry.dirty and self.lower_level:
                self.lower_level.access(
                    "W", entry.address, line=None,
                    origin=self.name + " page eviction writeback",
                    is_writeback=True
                )
                self.runtime_writebacks += 1
        self.cache.invalidate_page(evicted_entry)

    def get_stats(self):
        return self.cache.get_stats()