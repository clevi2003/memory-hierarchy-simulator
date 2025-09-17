
def hex_to_binary(hex_string, num_bits):
    return bin(int(hex_string, 16))[2:].zfill(num_bits)

class TraceParser:
    """
    Parses a trace file and yields operation and address pairs
    """
    def __init__(self, trace_file, addr_bits=32):
        self.addr_bits = addr_bits
        self.trace_file = trace_file
        with open(trace_file, 'r') as f:
            self.lines = f.readlines()

    def __iter__(self):
        # iterate over each line and yield relevant info
        for line in self.lines:
            parts = line.split(":")
            if len(parts) < 2:
                continue
            operation = parts[0]
            address = hex_to_binary(parts[1].strip(), self.addr_bits)
            yield operation, address, parts[1].strip()