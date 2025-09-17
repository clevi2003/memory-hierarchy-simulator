
class AccessResult:
    """
    Flexible class to encapsulate the result of accessing a memory hierarchy level
    """
    def __init__(self, level, operation, address, hit, tag, index, offset, page_offset=None, ppn=None, vpn=None, allocated=False, evicted_entry=None,
        wrote_back=False, needs_lower_read=False, needs_lower_write=False):
        # lots of parameters, but this is a flexible data class to hold whatever info is needed
        self.level = level
        self.op = operation
        self.addr = address
        self.hit = hit
        self.tag = tag
        self.index = index
        self.offset = offset
        self.page_offset = page_offset
        self.ppn = ppn
        self.vpn = vpn
        self.allocated = allocated
        self.evicted_entry = evicted_entry
        self.wrote_back = wrote_back
        self.needs_lower_read = needs_lower_read
        self.needs_lower_write = needs_lower_write

class AccessLine:
    """
    Class to encapsulate all the info about a single memory access for logging purposes
    """
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
        """
        Helper to format numeric values as hex strings, with options for width and zero-padding
        :param value: int or None
        :param width: int
        :param zero_pad: bool
        :return: formatted string
        """
        if value is None:
            return " " * width
        if zero_pad:
            return f"{value:0{width}x}"
        return f"{value:>{width}x}"

    @staticmethod
    def _format_hit_miss(value, width):
        """
        Helper to format hit/miss values as 'hit' or 'miss', or spaces if None
        :param value: bool or None
        :param width: int
        :return: formatted string
        """
        return (" " * width) if value is None else f"{'hit' if value else 'miss':>{width}s}"

    def __str__(self):
        # address is always printed as 8-hex, zero-padded
        addr = self._format_numeric(self.address, 8, zero_pad=True)

        # VM side (right-aligned hex, no zero-pad)
        vpn = self._format_numeric(self.vpn, 6)
        page_off = self._format_numeric(self.page_offset, 4)
        dtlb_tag = self._format_numeric(self.dtlb_tag, 6)
        dtlb_idx = self._format_numeric(self.dtlb_index, 3)
        dtlb_res = self._format_hit_miss(self.dtlb_result, 4)
        pt_res = self._format_hit_miss(self.page_table_result, 4)
        # print("PPN:", self.ppn)
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
