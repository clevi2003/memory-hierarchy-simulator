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
    def __init__(self, tag, index, address, dirty):
        self.tag = tag
        self.index = index
        self.address = address
        self.dirty = dirty

class AccessLine:
    def __init__(self, address):
        # format address as int regardless of if its an int or string
        if isinstance(address, str):
            self.address = int(address, 2)
        else:
            self.address = int(address) & 0xFFFFFFFF
        self.vpn = None
        self.page_offset = None
        self.dtlb_tag = None
        self.dtlb_index = None
        self.dtlb_result = None
        self.page_table_result = None
        self.ppn = None
        self.dc_tag = None
        self.dc_index = None
        self.dc_result = None
        self.l2_tag = None
        self.l2_index = None
        self.l2_result = None

    @staticmethod
    def _format_numeric(value, width, zero_pad=False):
        if value is None:
            return " " * width
        if zero_pad:
            return f"{value:0{width}x}"
        return f"{value:>{width}x}"

    @staticmethod
    def _format_hit_miss(value, width):
        return (" " * width) if value is None else f"{'hit' if value else 'miss':>{width}s}"

    def __str__(self):
        # Address is always printed as 8-hex, zero-padded
        addr = self._format_numeric(self.address, 8, zero_pad=True)

        # VM side (right-aligned hex, no zero-pad)
        # print(self.dc_tag, type(self.dc_tag))
        # print(self.vpn, type(self.vpn))
        vpn = self._format_numeric(self.vpn, 6)
        page_off = self._format_numeric(self.page_offset, 4)
        dtlb_tag = self._format_numeric(self.dtlb_tag, 6)
        dtlb_idx = self._format_numeric(self.dtlb_index, 3)
        dtlb_res = self._format_hit_miss(self.dtlb_result, 4)
        pt_res = self._format_hit_miss(self.page_table_result, 4)
        ppn = self._format_numeric(self.ppn, 4)

        # DC
        dc_tag = self._format_numeric(self.dc_tag, 6)
        dc_idx = self._format_numeric(self.dc_index, 3)
        dc_res = self._format_hit_miss(self.dc_result, 4)

        # L2
        l2_tag = self._format_numeric(self.l2_tag, 6)
        l2_idx = self._format_numeric(self.l2_index, 3)
        l2_res = self._format_hit_miss(self.l2_result, 4)

        return " ".join([
            addr, vpn, page_off,
            dtlb_tag, dtlb_idx, dtlb_res, pt_res, ppn,
            dc_tag, dc_idx, dc_res,
            l2_tag, l2_idx, l2_res
        ])

class EvictedPageTableEntry:
    def __init__(self, ppn, vpn, page_offset_bits=0):
        self.ppn = ppn
        self.vpn = vpn
        self.page_offset_bits = page_offset_bits

class TranslationResult:
    def __init__(self, hit, vpn, ppn, physical_address, offset, evicted_entry=None):
        self.hit = hit
        self.vpn = vpn
        self.ppn = ppn
        self.physical_address = physical_address
        self.evicted_entry = evicted_entry
        self.offset = offset

