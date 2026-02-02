from .config import DataConfig
from .data_process import load_data
from .solver import ALNSSolver
from .visualization import visualize_solution, print_cost_breakdown
import os
from .visualization import print_routes


def main():
    # 1. 加载数据
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    vrp_data = load_data("C101network_charge_test.txt")
    
    # 2. 配置参数
    config = DataConfig()
    config.vehicle_num = 14
    
    # 3. 求解
    solver = ALNSSolver(vrp_data, config)
    best_routes = solver.solve()
    
    # 4. 输出结果
    print_cost_breakdown(solver, best_routes)
    print_routes(solver, best_routes)
    visualize_solution(vrp_data, best_routes)

if __name__ == "__main__":
    main()