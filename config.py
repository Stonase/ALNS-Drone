class DataConfig:
    """算法参数配置容器"""
    def __init__(self):
        self.vehicle_num = 5      # 可用车辆数
        self.car_capacity = 200   # 车辆容量
        self.battery_cap = 800    # 电池容量
        self.base_energy = 0.3    # 基础能耗系数α
        self.load_energy = 0.07    # 负载能耗系数β
        self.max_iter = 200      # 最大迭代次数
        # self.tabu_length = 50     # 禁忌表长度


        # 新增运营成本参数
        self.vehicle_fixed_cost = 800    # 元/车次（车辆使用固定成本）
        self.distance_cost = 1.2         # 元/公里（单位距离成本）
        self.charging_cost = 300         # 元/次（充电服务费）