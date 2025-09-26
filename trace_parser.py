
def hex_to_binary(hex_string, num_bits):
    return bin(int(hex_string, 16))[2:].zfill(num_bits)

def hex_to_int(hex_string):
    return int(hex_string, 16)

class TraceParser:
    """
    Parses a trace file and yields operation and address pairs
    """
    def __init__(self, trace_file, addr_bits=32, emit_str=False):
        self.addr_bits = addr_bits
        self.trace_file = trace_file
        with open(trace_file, 'r') as f:
            self.lines = f.readlines()
        self._mask = (1 << self.addr_bits) - 1
        self.emit_str = emit_str

    def __iter__(self):
        # iterate over each line and yield relevant info
        for line in self.lines:
            parts = line.split(":")
            if len(parts) < 2:
                continue
            operation = parts[0].strip()
            hex_string = parts[1].strip()
            addr_int = hex_to_int(hex_string) & self._mask
            if self.emit_str:
                address = format(addr_int, f"0{self.addr_bits}b")
            else:
                address = addr_int
            yield operation, address, hex_string