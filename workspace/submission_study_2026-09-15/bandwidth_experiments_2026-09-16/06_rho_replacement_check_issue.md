# ρ扩大实验中的Path前树检查修复

## 发现与影响

原N256原型测试未触发一个Path Transfer分支的检查错误。N4096的热点与Zipf输入使前树目标更容易停留在stash；在一次合法“删除旧版本并接纳同址新版本”的时隙中，代码已经从临时`pool`删除旧记录，却仍对尚未更新的`self.stash`检查地址是否存在，因而误报重复插入并fail-stop。

失败发生在不同完整后端使用的同一Path前树，不能解释为selective优化失败或忽略不利trace。原始失败栈、配置和日志保存在results/failures及results/logs。旧组合调度器已停止继续发派；当时已经启动的子进程允许完成，停止时PID记录在results/composition_v1_dispatch_stop.json。其余Freecursive以完全相同代码与配置继续，ρ全部80个正式观察在修复后统一重跑，避免混合实现版本。

## 可独立复现的最小可达反例

L1、Z1、A2、N2。先对路径0接纳地址0、fresh leaf1；再对路径0接纳地址1、fresh leaf1，此时地址1留在stash。第三个时隙沿旧leaf1删除地址1，并以fresh leaf0接纳地址1的新版本。原实现从pool完成删除后仍看到旧stash中的地址1，错误拒绝；正确检查应以删除后的pool为准。

修复只将旧stash检查限定到非Path分支；Path本来已经有“pool中不得存在同址current”的检查，继续保留。真实重复接纳仍被拒绝。未改变payload、uid优先级、nonce分配、路径选择、维护时钟或认证格式，也未编辑冻结的旧组合包。

`results/transfer_fix_regression.json`记录：原反例确实失败，修复后能返回旧值并随后读回新值，真实重复接纳仍fail-stop，五类先前成功的执行保留全部frame与完成态。独立差分文件是`transfer_stash_replacement_fix.diff`。

## 结果采用规则

- Freecursive：继续使用原正式源版本，原有成功收据可复用。
- ρ：仅采用`formal_rho_fixed`目录的修复版结果；原`formal_composition`中的ρ结果全部留作版本历史。
- 不修改旧包的manifest，不把局部回归称为完整原生ρ审计。
- 该问题不涉及SOC3核心Path类的普通access分支，而在上一轮新增Transfer wrapper中；基础B1和新静态树顶缓存实验使用普通access，不受影响。
