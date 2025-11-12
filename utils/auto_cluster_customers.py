import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# === 1. 读取数据 ===
df = pd.read_csv('C:\Users\12448\OneDrive - MasterWai\Code\ALNS2\data\C101network_charge_test.txt')

# === 2. 去除充电站点 ===
df_customers = df[df['TYPE'] != 'charging_station'].copy()
df_customers = df_customers.fillna('')
X = df_customers[['XCOORD', 'YCOORD']].values

# === 3. 自动确定最佳聚类数 ===
sse = []  # 总平方误差
silhouette_scores = []
K_range = range(2, 11)  # 测试簇数 2~10，可自行调整

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=0, n_init='auto')
    labels = kmeans.fit_predict(X)
    sse.append(kmeans.inertia_)
    sil_score = silhouette_score(X, labels)
    silhouette_scores.append(sil_score)

# === 4. 根据轮廓系数选最优簇数 ===
best_k = K_range[np.argmax(silhouette_scores)]
print(f"最优聚类数（基于轮廓系数）为：{best_k}")

# === 5. 最终聚类 ===
final_kmeans = KMeans(n_clusters=best_k, random_state=0, n_init='auto')
df_customers['Cluster'] = final_kmeans.fit_predict(X)
centers = final_kmeans.cluster_centers_

# === 6. 输出结果 ===
print("\n=== 聚类中心点坐标 ===")
for i, (x, y) in enumerate(centers):
    members = df_customers[df_customers['Cluster'] == i]['CUST NO'].tolist()
    print(f"簇 {i+1}: 中心=({x:.2f}, {y:.2f})，客户数量={len(members)}，客户={members}")

# === 7. 可视化评估曲线 ===
plt.figure(figsize=(12,5))
plt.subplot(1,2,1)
plt.plot(K_range, sse, 'o-', label='SSE（肘部法）')
plt.xlabel('簇数 K')
plt.ylabel('SSE')
plt.title('肘部法判断聚类数')
plt.grid(True)

plt.subplot(1,2,2)
plt.plot(K_range, silhouette_scores, 'o-', color='orange', label='轮廓系数')
plt.xlabel('簇数 K')
plt.ylabel('Silhouette Score')
plt.title('轮廓系数判断聚类数')
plt.grid(True)
plt.tight_layout()
plt.show()

# === 8. 聚类可视化 ===
plt.figure(figsize=(8,6))
plt.scatter(df_customers['XCOORD'], df_customers['YCOORD'], c=df_customers['Cluster'], cmap='tab10', s=50)
plt.scatter(centers[:,0], centers[:,1], c='red', marker='x', s=150, label='中心点')
plt.title(f'客户聚类结果（K={best_k}）')
plt.xlabel('X 坐标')
plt.ylabel('Y 坐标')
plt.legend()
plt.grid(True)
plt.show()
