from .level_core import MemoryLevel
from ..result_structures import AccessResult
from collections import defaultdict

class MainMemoryLevel(MemoryLevel):
    def __init__(self):
        super().__init__("Main Memory")
        self.reads = 0
        self.writes = 0
        self.by_origin = defaultdict(lambda x: 0)

    def access(self, operation, address, line, update_line=False, origin="unknown"):
        self.by_origin[origin] = self.by_origin.get(origin, 0) + 1
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