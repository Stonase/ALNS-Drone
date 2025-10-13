import matplotlib.pyplot as plt
import random
from .data_structure import VRPData
from .solver import ALNSSolver
from .utils.helpers import solution_cost
 
def visualize_solution(data: VRPData, solution: list[list[int]], save_path: str = None):
    """整合路径绘制的可视化函数"""
    import matplotlib.pyplot as plt
    import random

    plt.figure(figsize=(10, 7))
    plt.xlabel("X Coordinate", fontfamily='serif')
    plt.ylabel("Y Coordinate", fontfamily='serif')
    plt.title(f"{len(data.customer_ids)} Customers, {sum(1 for r in solution if len(r)>2)} Vehicles Used",
             fontfamily='serif', fontsize=14)

    # ===== 基础节点绘制 =====
    # 车场节点
    depot_x, depot_y = data.coords[0]
    plt.scatter(depot_x, depot_y, 
                c='blue', alpha=1, marker=',', s=30,
                linewidths=2, label='Depot', zorder=5)

    # 客户节点
    customers = [i for i in data.customer_ids if i != 0]
    cust_x = [data.coords[i][0] for i in customers]
    cust_y = [data.coords[i][1] for i in customers]
    plt.scatter(cust_x, cust_y,
                c='black', alpha=1, marker='o', s=30,
                linewidths=1, label='Customer', zorder=5)

    # 充电站节点
    if data.charge_ids:
        charge_x = [data.coords[i][0] for i in data.charge_ids]
        charge_y = [data.coords[i][1] for i in data.charge_ids]
        plt.scatter(charge_x, charge_y,
                    c='red', alpha=1, marker='s', s=50,
                    linewidths=1, label='Charging Station', zorder=5)

    # ===== 节点标注 =====
    for node_id in [0] + data.customer_ids + data.charge_ids:
        x, y = data.coords[node_id]
        plt.text(x, y, str(node_id),
                family='serif', style='italic', fontsize=10,
                verticalalignment="bottom", 
                horizontalalignment='left',
                color='k')

    # ===== 路径绘制 =====
    for route in solution:
        if len(route) <= 2:  # 跳过空路径
            continue
        
        # 生成随机颜色
        red = random.randint(50, 200)
        green = random.randint(50, 200)
        blue = random.randint(50, 200)
        
        # 绘制路径线段
        for i in range(len(route)-1):
            start = route[i]
            end = route[i+1]
            plt.plot([data.coords[start][0], data.coords[end][0]],
                    [data.coords[start][1], data.coords[end][1]],
                    color=(red/255, green/255, blue/255),
                    linewidth=1.5,
                    alpha=0.7,
                    zorder=3)

    # ===== 样式调整 =====
    plt.grid(False)
    plt.legend(loc='best', prop={'family':'serif', 'size':12})
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
    else:
        plt.show()

# 输出解决方案的详细成本构成
def print_cost_breakdown(solver: ALNSSolver, solution: list[list[int]]):
    used_vehicles = sum(1 for r in solution if len(r) > 2)
    total_distance = sum(solver.data.dist_matrix[i][j] for route in solution for i,j in zip(route[:-1], route[1:]))
    charging_count = sum(1 for r in solution for n in r if n in solver.data.charge_ids)
    
    print(f"[成本分析]")
    print(f"车辆使用数: {used_vehicles} × {solver.cfg.vehicle_fixed_cost} = {used_vehicles * solver.cfg.vehicle_fixed_cost}元")
    print(f"行驶距离: {total_distance:.1f}km × {solver.cfg.distance_cost} = {total_distance * solver.cfg.distance_cost:.1f}元")
    print(f"充电次数: {charging_count} × {solver.cfg.charging_cost} = {charging_count * solver.cfg.charging_cost}元")
    print(f"总运营成本: {solution_cost(solver.data, solver.cfg, solution):.1f}元")
