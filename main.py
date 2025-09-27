from config import Config
from mem_hierarchy import MemoryHierarchySimulator

def main():
    mem_sim_config = Config.from_config_file("tests/trace.config")
    print(mem_sim_config)

# ppn is wrong when dtlb hit


    simulator = MemoryHierarchySimulator(mem_sim_config)
    # simulator.simulate("trace_copy.dat")
    simulator.simulate("tests/long_trace.dat")


if __name__ == '__main__':
    main()