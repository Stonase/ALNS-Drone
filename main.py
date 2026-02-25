from .config import DataConfig
from .data_process import load_data
from .solver import ALNSSolver
from .ga_solver import GASolver
from .visualization import visualize_solution, print_cost_breakdown, plot_convergence
import os
from .visualization import print_routes


def main():
    # 1. 加载数据
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    vrp_data = load_data("C101_Strategy1_Centers.txt")
    
    # 2. 配置参数
    config = DataConfig()
    config.vehicle_num = 15
    config.max_iter = 200   # 统一迭代次数以方便对比
    
    # 3. 求解
    solver = ALNSSolver(vrp_data, config)
    best_routes = solver.solve()
    
    # # ==========================
    # # 4. 对比组 B：GA 求解
    # # ==========================
    # print("\n" + "="*40)
    # print("正在运行：GA (遗传算法)")
    # print("="*40)
    # ga_solver = GASolver(vrp_data, config)
    # ga_best_routes = ga_solver.solve()
    # print_cost_breakdown(ga_solver, ga_best_routes)


    # 4. 输出结果
    print("\n" + "="*40)
    print("ALNS结果")
    print("="*40)
    print_cost_breakdown(solver, best_routes)
    print_routes(solver, best_routes)
    plot_convergence(solver.history, save_path="convergence_log.png")
    visualize_solution(vrp_data, best_routes, save_path="route_visualization.png")

if __name__ == "__main__":
    main()