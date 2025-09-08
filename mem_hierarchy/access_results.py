class AccessResult:
    def __init__(self, level, operation, address, hit, tag, index, offset, allocated=False, evicted_entry=None,
        wrote_back=False, needs_lower_read=False, needs_lower_write=False):
        self.level = level
        self.op = operation
        self.addr = address
        self.hit = hit
        self.tag = tag
        self.index = index
        self.offset = offset
        self.allocated = allocated
        self.evicted_entry = evicted_entry
        self.wrote_back = wrote_back
        self.needs_lower_read = needs_lower_read
        self.needs_lower_write = needs_lower_write


class EvictedCacheEntry:
    def __init__(self, tag, index, dirty):
        self.tag = tag
        self.idx = index
        self.dirty = dirty