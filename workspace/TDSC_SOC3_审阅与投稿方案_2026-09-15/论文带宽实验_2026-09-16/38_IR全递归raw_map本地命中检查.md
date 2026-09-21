# IR-Stash：全部raw位置表层的本地命中

本阶段在35号文档的数据块接口上继续接入各层raw位置表。它是新增的独立实现，不修改正在执行的旧IR/AB批次，也没有把功能夹具作为论文带宽样本。

后续39号转录检查已复现底层跳过规则的安全反例。本文件仍可作为功能证据，不能作为安全或性能准入。目标规模新实验须先解决该反例，不能只增加样本或R来绕过。

## 所有权规则

新增 `src/ir_stash_raw_maps.py`。PLB命中仍直接使用其唯一canonical map；F/S命中则保留map在后端的canonical位置，仅返回临时句柄。这个句柄保存地址、已知叶标签和创建时的Transfer时钟，不复制payload到另一个持久缓存。

句柄读写通过已经验证的本地加密接口；不remap该map，不更新它在父map中的叶项。只有确实需要远端获取某个map时，才生成其parked leaf、更新父项并通过Transfer把唯一所有权移入PLB；同次Transfer可接纳被驱逐的PLB map。

dedicated-top对照与indexed模式仍采用相同区别：F命中无需父查询；indexed的S命中也无需父查询；dedicated的S命中先递归取得当前叶。递归加载后再探测，避免忽略加载期间的放置变化。

## 原子提交与取消边界

远端map加载之前，父项更新与该Transfer之间没有yield。若父项在本地桶，先完成它的认证重写，随后远端访问使用更新后的可信根。若父项在PLB，选择待驱逐项时将父项pin住。Transfer通过后才安装新的PLB条目。

每次对外step只产生一个已提交Transfer事件，或一个零Transfer的数据完成事件；控制器仍填满公共时隙。暂停点前已完成的map操作不回滚。LocalMap句柄不能放入PLB，也不能在任何后续Transfer后再次使用；时钟检查在I/O和解密之前拒绝过期句柄。该限制保证代码不会把旧放置位置当成当前canonical位置。

在初始唯一所有权和raw位置表指向正确的前提下，本地map读写保持map的uid/leaf和owner；远端map操作将owner从后端变为PLB，并把其父项改为相同parked leaf；PLB驱逐则用该parked leaf重新接纳。逐项组合可保持全部层的叶指向和唯一所有权。异常由公开step入口统一停止前端和后端，不能带着部分更新继续请求。

## 实际检查

`src/check_ir_stash_raw_maps.py` 已完成：

| 检查项 | 覆盖 |
|---|---|
| 组合矩阵 | 2种递归几何 × dedicated/indexed × Path/Deferred/SDE × DWB开关，共24组 |
| 较浅递归 | N64、X16、3层记录类型、缓存6层；每组48请求/384公共时隙 |
| 较深递归 | N96、X2、8层记录类型、缓存3层；每组48请求/576公共时隙 |
| 完成态 | 解密oracle核对全部地址唯一owner、每层父map中的叶、PLB parked leaf、LLC dirty/clean数据与应用返回值 |
| 本地map更新 | 24组均实际取得并读写了本地map句柄；indexed探测无需父查询、Transfer或叶随机数消耗 |
| 调度 | 每个公共时隙恰好一个Transfer；前台、DWB、dummy分项与总时钟守恒 |
| 过期句柄 | 已发生后续Transfer后拒绝使用，不产生新I/O或解密 |
| 主动失败 | 3后端 × OPEN/WRITE，共6个远端map回复篡改，公开入口永久停止，后续请求不再通信 |

结果为 `results/ir_stash_raw_maps_checks.json`，绑定本阶段代码、checker、已有数据接口检查和独立oracle来源。所有24组均实际触发本地map访问。测试使用Z1/R400以覆盖状态分支，不提供新溢出概率或目标规模性能结论。

## 仍未完成的内容

此阶段支持raw位置表。压缩计数器的group reset会跨多个公共时隙保存parent状态；临时LocalMap句柄不能直接作为其持久parent。接入时必须提供跨时隙的唯一owner与父项更新规则，并在每个恢复点重新确认当前位置，或通过明确的所有权转移把parent固定到PLB；不能删除过期句柄检查来通过测试。

本地命中不remap以及hash组冲突仍改变版本寿命和放置过程。原固定历史Poisson证书尚未覆盖，完整transcript模拟也未补齐。本阶段不改变35号文档中的安全边界，不声称完整原生IR已经闭合。目标规模实测还需独立配置、收据和比较计划，不能把原批次数字改名为本实现结果。
