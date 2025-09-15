from config import Config
from mem_hierarchy import *

def main():
    mem_sim_config = Config.from_config_file("trace copy.config")
    print(mem_sim_config)


    simulator = MemoryHierarchySimulator(mem_sim_config)
    # simulator.simulate("trace_copy.dat")
    simulator.simulate("trace.dat")


if __name__ == '__main__':
    main()