from config import Config
from trace_parser import TraceParser
from mem_hierarchy import *

def main():
    mem_sim_config = Config.from_config_file("trace copy.config")
    #print(mem_sim_config)

    # trace_parser = TraceParser("trace.dat")
    # for operation, address in trace_parser:
    #     print(f"Operation: {operation}, Address: {address}")

    simulator = MemoryHierarchySimulator(mem_sim_config)
    simulator.simulate("trace_copy.dat")


if __name__ == '__main__':
    main()