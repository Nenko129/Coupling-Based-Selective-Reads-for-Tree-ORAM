# 扩展实验的配对统计与模型校准

指标为实际序列化双向字节/应用请求。模型列为完整周期期望，不能与有限前缀测量混称。
公开trace的5组相邻窗口只报配对均值与范围，不报告代表整个工作负载总体的独立样本置信区间。

| 批次 | 已核查/计划观察数 |
|---|---:|
| calibration | 40/40 |
| public | 80/80 |
| sensitivity | 220/220 |
| slices | 126/150 |
| tuned | 50/50 |

## 配对收益

n<5仅为过程数据；只用两侧均完成的同种子运行。

| 批次/条件 | 前端/负载 | N/B | 基线→selective | n | 基线 bytes/op | selective bytes/op | 节省 | 95%区间或窗口范围 |
|---|---|---|---|---:|---:|---:|---:|---|
| public/default | free_compressed/Financial1_startkey | 16384/64 | deferred → sde | 5 | 54,677.11 | 42,617.23 | 22.06% | 窗口范围 [22.01%, 22.12%] |
| public/default | free_compressed/Financial1_startkey | 16384/64 | ring → r0 | 5 | 81,083.12 | 61,560.80 | 24.08% | 窗口范围 [24.06%, 24.10%] |
| public/default | rho/Financial1_startkey | 16384/64 | deferred → sde | 5 | 28,094.29 | 25,538.65 | 9.10% | 窗口范围 [9.08%, 9.10%] |
| public/default | rho/Financial1_startkey | 16384/64 | ring → r0 | 5 | 33,663.71 | 29,538.34 | 12.25% | 窗口范围 [12.20%, 12.28%] |
| public/default | free_compressed/WebSearch1_startkey | 16384/64 | deferred → sde | 5 | 56,468.30 | 44,019.92 | 22.04% | 窗口范围 [22.02%, 22.08%] |
| public/default | free_compressed/WebSearch1_startkey | 16384/64 | ring → r0 | 5 | 83,750.60 | 63,615.07 | 24.04% | 窗口范围 [23.97%, 24.12%] |
| public/default | rho/WebSearch1_startkey | 16384/64 | deferred → sde | 5 | 48,764.40 | 44,323.17 | 9.11% | 窗口范围 [9.08%, 9.12%] |
| public/default | rho/WebSearch1_startkey | 16384/64 | ring → r0 | 5 | 58,434.55 | 51,269.19 | 12.26% | 窗口范围 [12.22%, 12.33%] |
| sensitivity/plb4 | free_compressed/hot90 | 4096/64 | deferred → sde | 5 | 47,346.72 | 37,023.13 | 21.80% | [21.78%, 21.83%] |
| sensitivity/plb4 | free_compressed/hot90 | 4096/64 | ring → r0 | 5 | 70,237.50 | 53,062.67 | 24.45% | [24.40%, 24.50%] |
| sensitivity/plb32 | free_compressed/hot90 | 4096/64 | deferred → sde | 5 | 23,737.82 | 18,550.18 | 21.85% | [21.80%, 21.90%] |
| sensitivity/plb32 | free_compressed/hot90 | 4096/64 | ring → r0 | 5 | 35,199.55 | 26,581.19 | 24.48% | [24.44%, 24.53%] |
| sensitivity/beta4 | free_compressed/hot90 | 4096/64 | deferred → sde | 5 | 74,667.71 | 58,369.40 | 21.83% | [21.77%, 21.88%] |
| sensitivity/beta4 | free_compressed/hot90 | 4096/64 | ring → r0 | 5 | 110,764.10 | 83,674.50 | 24.46% | [24.38%, 24.53%] |
| sensitivity/B4096 | free_raw/uniform | 4096/4096 | deferred → sde | 5 | 366,897.89 | 278,537.22 | 24.08% | [23.95%, 24.22%] |
| sensitivity/B4096 | free_raw/uniform | 4096/4096 | ring → r0 | 5 | 318,762.38 | 248,348.41 | 22.09% | [21.94%, 22.24%] |
| sensitivity/B4096 | free_compressed/uniform | 4096/4096 | deferred → sde | 5 | 366,897.89 | 278,708.41 | 24.04% | [23.93%, 24.14%] |
| sensitivity/B4096 | free_compressed/uniform | 4096/4096 | ring → r0 | 5 | 318,766.20 | 248,464.83 | 22.05% | [21.97%, 22.14%] |
| sensitivity/llc8 | rho/hot90 | 4096/64 | deferred → sde | 5 | 14,571.26 | 13,358.54 | 8.32% | [8.30%, 8.34%] |
| sensitivity/llc8 | rho/hot90 | 4096/64 | ring → r0 | 5 | 17,212.80 | 15,207.90 | 11.65% | [11.62%, 11.67%] |
| sensitivity/llc128 | rho/hot90 | 4096/64 | deferred → sde | 5 | 4,488.84 | 4,118.23 | 8.26% | [8.18%, 8.33%] |
| sensitivity/llc128 | rho/hot90 | 4096/64 | ring → r0 | 5 | 5,304.60 | 4,689.74 | 11.59% | [11.50%, 11.68%] |
| sensitivity/rho32 | rho/zipf09 | 4096/64 | deferred → sde | 5 | 30,195.93 | 27,375.04 | 9.34% | [9.31%, 9.37%] |
| sensitivity/rho32 | rho/zipf09 | 4096/64 | ring → r0 | 5 | 36,393.93 | 31,724.57 | 12.83% | [12.78%, 12.88%] |
| sensitivity/rho512 | rho/zipf09 | 4096/64 | deferred → sde | 5 | 24,280.98 | 22,469.80 | 7.46% | [7.41%, 7.51%] |
| sensitivity/rho512 | rho/zipf09 | 4096/64 | ring → r0 | 5 | 28,265.44 | 25,256.81 | 10.64% | [10.60%, 10.69%] |
| sensitivity/ratio1 | rho/uniform | 4096/64 | deferred → sde | 5 | 26,818.70 | 23,031.46 | 14.12% | [14.07%, 14.17%] |
| sensitivity/ratio1 | rho/uniform | 4096/64 | ring → r0 | 5 | 35,189.13 | 28,903.33 | 17.86% | [17.81%, 17.92%] |
| sensitivity/ratio5 | rho/uniform | 4096/64 | deferred → sde | 5 | 62,593.02 | 58,922.52 | 5.86% | [5.84%, 5.89%] |
| sensitivity/ratio5 | rho/uniform | 4096/64 | ring → r0 | 5 | 70,693.79 | 64,593.53 | 8.63% | [8.61%, 8.65%] |
| slices/default | core/uniform | 4096/4096 | path → sde | 5 | 435,568.00 | 278,471.38 | 36.07% | [35.98%, 36.16%] |
| slices/default | core/uniform | 4096/4096 | deferred → sde | 5 | 366,897.89 | 278,471.38 | 24.10% | [23.99%, 24.21%] |
| slices/default | core/uniform | 4096/4096 | ring → r0 | 5 | 331,068.99 | 242,930.54 | 26.62% | [26.45%, 26.79%] |
| slices/default | core/uniform | 16384/64 | path → sde | 5 | 57,432.00 | 42,591.27 | 25.84% | [25.69%, 25.99%] |
| slices/default | core/uniform | 16384/64 | deferred → sde | 5 | 54,884.78 | 42,591.27 | 22.40% | [22.24%, 22.56%] |
| slices/default | core/uniform | 16384/64 | ring → r0 | 5 | 67,093.58 | 48,579.62 | 27.59% | [27.46%, 27.73%] |
| slices/default | core/uniform | 16384/256 | path → sde | 5 | 80,472.00 | 57,099.00 | 29.04% | [28.93%, 29.15%] |
| slices/default | core/uniform | 16384/256 | deferred → sde | 5 | 74,082.90 | 57,099.00 | 22.93% | [22.81%, 23.05%] |
| slices/default | core/uniform | 16384/256 | ring → r0 | 5 | 83,775.55 | 60,907.85 | 27.30% | [27.19%, 27.41%] |
| slices/default | core/uniform | 16384/1024 | path → sde | 5 | 172,632.00 | 115,128.94 | 33.31% | [33.22%, 33.40%] |
| slices/default | core/uniform | 16384/1024 | deferred → sde | 5 | 150,875.40 | 115,128.94 | 23.69% | [23.59%, 23.80%] |
| slices/default | core/uniform | 16384/1024 | ring → r0 | 5 | 150,715.77 | 110,173.40 | 26.90% | [26.78%, 27.02%] |
| slices/default | core/uniform | 16384/4096 | path → sde | 5 | 541,272.00 | 347,515.59 | 35.80% | [35.77%, 35.82%] |
| slices/default | core/uniform | 16384/4096 | deferred → sde | 5 | 458,045.40 | 347,515.59 | 24.13% | [24.10%, 24.16%] |
| slices/default | core/uniform | 16384/4096 | ring → r0 | 5 | 418,371.80 | 307,356.26 | 26.54% | [26.41%, 26.66%] |
| tuned/default | core/uniform | 16384/4096 | path → sde | 5 | 527,664.00 | 338,932.57 | 35.77% | [35.66%, 35.88%] |
| tuned/default | core/uniform | 16384/4096 | deferred → sde | 5 | 446,997.06 | 338,932.57 | 24.18% | [24.05%, 24.30%] |
| tuned/default | core/uniform | 16384/4096 | ring → r0 | 5 | 339,710.71 | 253,539.89 | 25.37% | [25.19%, 25.55%] |
| tuned/default | core/hot90 | 16384/4096 | path → sde | 5 | 527,664.00 | 338,824.32 | 35.79% | [35.68%, 35.89%] |
| tuned/default | core/hot90 | 16384/4096 | deferred → sde | 5 | 446,997.06 | 338,824.32 | 24.20% | [24.08%, 24.32%] |
| tuned/default | core/hot90 | 16384/4096 | ring → r0 | 5 | 339,520.46 | 253,302.41 | 25.39% | [25.16%, 25.63%] |

## 完整周期校准

Path每次访问一条随机路径并读写；其窗口长度与其他方案对齐，但不是bit-reversal维护周期。其余方案核对测量起点整周期对齐。有限个周期仍不自动等于稳态。

| 协议/参数 | n | 周期期望 bytes/op | 实际均值 bytes/op | 相对模型偏差 |
|---|---:|---:|---:|---:|
| path/[4, 3, 3] | 5 | 11,280.00 | 11,280.00 | 0.000% |
| deferred/[4, 3, 3] | 5 | 12,160.00 | 12,160.00 | 0.000% |
| sde/[4, 3, 3] | 5 | 9,589.25 | 9,602.76 | 0.141% |
| ring/[4, 3, 3] | 5 | 18,206.23 | 18,206.00 | -0.001% |
| gc_ring/[4, 3, 3] | 5 | 14,435.08 | 14,433.15 | -0.013% |
| r0/[4, 3, 3] | 5 | 13,119.83 | 13,099.30 | -0.156% |
| ring/[7, 6, 6] | 5 | 17,297.17 | 17,291.08 | -0.035% |
| r0/[7, 6, 6] | 5 | 11,674.78 | 11,688.50 | 0.117% |

随机neutral频次会产生有限样本偏差。单个均值或置信区间与模型不同不能直接判定协议或模型错误，应先检查暖机、周期相位与分项账单。所有偏差保留。
sensitivity中的B4096点同时按编码容量改变X（raw=1024、compressed=2048），它是块大小与相应打包方式的配置切片，不能称固定X的单因素实验。
