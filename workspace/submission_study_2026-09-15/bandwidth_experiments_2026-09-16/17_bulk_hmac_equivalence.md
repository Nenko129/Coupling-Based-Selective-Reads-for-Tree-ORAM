# 批量HMAC执行的等价关系

2026-09-16。本优化只用于待执行的B4规模切片。核心、消融、调优、缓存与小型扩展仍按各自原执行身份运行。没有改写任何正在运行的执行闭包。

原stream的第j块是 `HMAC-SHA512(key, prefix || uint64be(j))`，其中prefix包括STREAM、context、对象、AAD、nonce及uint64长度字段。j=0单独执行。

对1≤j<2^32，令salt=`prefix || uint32be(0)`。PBKDF2-HMAC-SHA512在iteration=1时，第j块是 `HMAC(key, salt || uint32be(j))`，与上述原stream第j块逐字节相同。这里调用密码库的批量HMAC实现，不改变协议、密码算法或随机带，也不是将ORAM密钥改成密码派生。[RFC 8018 §5.2](https://www.rfc-editor.org/rfc/rfc8018.html#section-5.2)、[Python hashlib](https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac)

短输入、接近公开PRF预算上限以及库长度边界退回已检查的前缀复用实现；保留原本部分执行后抛错的调用计数、nonce分配和认证次序。

新证据 `results/bulk_prf_checks.json` 和 `results/bulk_runner_checks.json` 覆盖120组随机stream、原语边界、12个完整ORAM/缓存配置、两个实际递归进程、5个调用预算边界及6个主动失败前缀。检查完整密文字节、最终状态与计数，未把只比长度当作逐字节等价。

原scale派发进程在尚无子任务时停止，新派发器等待同一个调优批次成功完成后启动。切换记录为 `results/scale_bulk_switch.json`，新入口是 `dispatch_bulk_scale.py`，状态为 `results/extended_scale_queue_bulk_state.json`。不能同时重启旧scale队列。

原语微基准仅用于决定调度；不进入论文的ORAM性能结论。本任务不报告运行器变化产生的加速比。
