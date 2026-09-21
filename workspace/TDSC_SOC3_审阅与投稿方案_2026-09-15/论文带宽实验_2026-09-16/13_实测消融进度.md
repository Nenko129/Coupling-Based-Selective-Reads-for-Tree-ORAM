# 实测消融进度

每个效应仅使用四格均完成的同种子组；n<5不生成置信区间。负收益和交互项照常保留。

| 参数族 | 效应 | n | 均值 | 95%区间 |
|---|---|---:|---:|---|
| 43 | fusion_without_compact_pct | 5 | 0.9632% | [0.6299, 1.2965] |
| 43 | fusion_with_compact_pct | 5 | 0.8407% | [0.5670, 1.1143] |
| 43 | compact_without_fusion_pct | 5 | 2.0520% | [1.6668, 2.4371] |
| 43 | compact_with_fusion_pct | 5 | 1.9310% | [1.7203, 2.1416] |
| 43 | interaction_bytes | 5 | 442.5559 bytes/op | [-1018.6797, 1903.7914] |
| 76 | fusion_without_compact_pct | 5 | 0.3554% | [0.1651, 0.5456] |
| 76 | fusion_with_compact_pct | 5 | 0.4021% | [0.0469, 0.7574] |
| 76 | compact_without_fusion_pct | 5 | 2.8130% | [2.6413, 2.9847] |
| 76 | compact_with_fusion_pct | 5 | 2.8586% | [2.5467, 3.1705] |
| 76 | interaction_bytes | 5 | -94.1172 bytes/op | [-1251.7421, 1063.5077] |

| 顺序步骤 | n | 条件通信节省 |
|---|---:|---:|
| 43_large_map_cf00 → 43_cf00 | 5 | 15.4049% |
| 43_cf00 → 43_cf10 | 5 | 2.0520% |
| 43_cf10 → 43_cf11 | 5 | 0.8407% |
| 43_cf11 → 76_cf11 | 5 | 16.2031% |

顺序百分比不能直接相加。更换参数族同时改变Z/A/S、树高和递归布局；小map、compact、fusion分别记录。
