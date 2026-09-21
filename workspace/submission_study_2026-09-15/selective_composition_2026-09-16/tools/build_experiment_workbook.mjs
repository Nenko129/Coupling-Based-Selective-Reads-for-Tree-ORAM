import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "论文实验章节完整证据_2026-09-16");
const data = JSON.parse(await fs.readFile(path.join(outDir, "workbook_data.json"), "utf8"));
const outputPath = path.join(outDir, "TDSC论文实验数据总表.xlsx");
const previewDir = path.join(outDir, "workbook_previews");
await fs.mkdir(previewDir, { recursive: true });

const wb = Workbook.create();
const FONT = "Aptos";
const NAVY = "#17324D";
const TEAL = "#0F8B8D";
const GOLD = "#D89B2B";
const PALE = "#EAF2F8";
const PALE_TEAL = "#E8F5F4";
const LIGHT = "#F4F6F8";
const RED = "#B42318";
const GREEN = "#217A4D";

const sheets = {};
for (const name of ["总览", "主比较", "规模矩阵", "最小组合", "消融", "稳健性", "补充证据", "资源审计", "原始运行", "证据索引"]) {
  sheets[name] = wb.worksheets.add(name);
  sheets[name].showGridLines = false;
}

function colLetter(n) {
  let s = "";
  while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); }
  return s;
}

function fmtValue(v) {
  if (v === undefined || v === null) return null;
  if (typeof v === "object") return JSON.stringify(v);
  return v;
}

function baseSheet(sheet, title, subtitle, endCol = "L") {
  sheet.getRange(`A2:${endCol}2`).format.borders = { bottom: { style: "thin", color: NAVY } };
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format.font = { name: FONT, size: 15, bold: true, color: NAVY };
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange(`A3:${endCol}3`).format.font = { name: FONT, size: 9, italic: true, color: "#5B6573" };
}

function writeTable(sheet, startRow, headers, rows, keys, tableName, options = {}) {
  const startCol = options.startCol || 1;
  const matrix = [headers, ...rows.map(r => keys.map(k => fmtValue(r[k])))];
  const start = `${colLetter(startCol)}${startRow}`;
  const end = `${colLetter(startCol + keys.length - 1)}${startRow + rows.length}`;
  sheet.getRange(`${start}:${end}`).values = matrix;
  const header = sheet.getRange(`${colLetter(startCol)}${startRow}:${colLetter(startCol + keys.length - 1)}${startRow}`);
  header.format.fill = NAVY;
  header.format.font = { name: FONT, size: 10, bold: true, color: "#FFFFFF" };
  header.format.horizontalAlignment = "center";
  header.format.verticalAlignment = "center";
  header.format.wrapText = true;
  header.format.rowHeight = 38;
  const body = sheet.getRange(`${colLetter(startCol)}${startRow + 1}:${end}`);
  body.format.font = { name: FONT, size: 10, color: "#1F2937" };
  body.format.verticalAlignment = "center";
  if (rows.length) {
    const table = sheet.tables.add(`${start}:${end}`, true, tableName);
    table.style = "TableStyleMedium2";
  }
  return { start, end, startRow, endRow: startRow + rows.length, startCol, endCol: startCol + keys.length - 1 };
}

function applyFormats(sheet, table, keys) {
  const first = table.startRow + 1, last = table.endRow;
  if (last < first) return;
  keys.forEach((k, i) => {
    const letter = colLetter(table.startCol + i);
    const range = sheet.getRange(`${letter}${first}:${letter}${last}`);
    if (/pct|ci95|saving|gap_pp|rpc_saving/.test(k)) range.setNumberFormat("0.000\"%\"");
    else if (/bytes_per_request|baseline_bytes|variant_bytes|storage_bytes|payload_bytes|map_bytes|request_bytes|response_bytes/.test(k)) range.setNumberFormat("#,##0.00");
    else if (/seconds/.test(k)) range.setNumberFormat("#,##0.00");
    else if (/^N$|^B$|^n$|seed|requests|observed|required/.test(k)) range.setNumberFormat("#,##0");
    else if (/measured|eligible|included|needs_more/.test(k)) range.format.horizontalAlignment = "center";
  });
}

function setWidths(sheet, widths) {
  Object.entries(widths).forEach(([col, width]) => { sheet.getRange(`${col}:${col}`).format.columnWidth = width; });
}

function styleChart(chart, title, yTitle, type = "bar") {
  chart.title = title;
  chart.titleTextStyle.fontSize = 12;
  chart.titleTextStyle.typeface = FONT;
  chart.legend = { position: "top", textStyle: { typeface: FONT, fontSize: 9 } };
  chart.xAxis = { axisType: "textAxis", textStyle: { typeface: FONT, fontSize: 9 } };
  chart.yAxis = { minimumScale: 0, numberFormatCode: "0.0\"%\"", numberFormatSourceLinked: false, textStyle: { typeface: FONT, fontSize: 9 } };
  chart.yAxis.title.text = yTitle;
  if (type === "line") for (const [i, s] of chart.series.items.entries()) s.line = { fill: [NAVY, TEAL, GOLD][i % 3], style: "solid", width: 2 };
  else for (const [i, s] of chart.series.items.entries()) s.fill = [NAVY, TEAL, GOLD][i % 3];
}

// Summary sheet.
{
  const s = sheets["总览"];
  baseSheet(s, "TDSC 实验数据总览", `冻结矩阵：120 条最小组合 + 125 条规模实验；生成于 ${data.generated}`, "N");
  s.getRange("A5:D5").values = [["核心指标", "数值", "口径", "状态"]];
  s.getRange("A5:D5").format.fill = NAVY;
  s.getRange("A5:D5").format.font = { name: FONT, size: 10, bold: true, color: "#FFFFFF" };
  s.getRange("A6:A12").values = [["SDE / tuned Path"], ["SDE / tuned Deferred"], ["R0 / tuned Ring"], ["四宿主最小组合下界"], ["四宿主最小组合上界"], ["正式收据"], ["关键证据缺口"]];
  s.getRange("B6").formulas = [["='主比较'!H5"]];
  s.getRange("B7").formulas = [["='主比较'!H6"]];
  s.getRange("B8").formulas = [["='主比较'!H7"]];
  s.getRange("B9").formulas = [["=MIN('最小组合'!I5:I14)"]];
  s.getRange("B10").formulas = [["=MAX('最小组合'!I5:I14)"]];
  s.getRange("B11").formulas = [["=COUNTA('原始运行'!A5:A124)+COUNTA('原始运行'!Y5:Y129)"]];
  s.getRange("B12").values = [["峰值内存、真实网络延迟"]];
  s.getRange("C6:C12").values = [["uniform；同调优"], ["uniform；同调优"], ["uniform；同调优"], ["仅 selective read"], ["仅 selective read"], ["120+125"], ["未测量，不作实测声明"]];
  s.getRange("D6:D11").values = [["headline"], ["headline"], ["headline"], ["composability"], ["composability"], ["complete"]];
  s.getRange("D12").values = [["open"]];
  s.getRange("A6:D12").format.font = { name: FONT, size: 10, color: "#1F2937" };
  s.getRange("B6:B10").setNumberFormat("0.000\"%\"");
  s.getRange("B11").setNumberFormat("0");
  s.getRange("D6:D11").format.font = { name: FONT, size: 10, bold: true, color: GREEN };
  s.getRange("D12").format.font = { name: FONT, size: 10, bold: true, color: RED };
  s.getRange("A5:D12").format.borders = { preset: "outside", style: "thin", color: "#C9D2DC" };
  s.getRange("A15:C15").values = [["最小组合", "通信下降 (%)", "95% CI 半宽"]];
  const helper = data.minimal_primary.map(r => [`${r.family}/${r.layout}, B=${r.B}`, r.bytes_saving_pct, (r.ci95_high_pct-r.ci95_low_pct)/2]);
  s.getRange(`A16:C${15+helper.length}`).values = helper;
  s.getRange("A15:C15").format.fill = PALE;
  s.getRange("A15:C15").format.font = { name: FONT, size: 10, bold: true, color: NAVY };
  s.getRange(`B16:C${15+helper.length}`).setNumberFormat("0.000\"%\"");
  const chart = s.charts.add("bar", [s.getRange(`A15:A${15+helper.length}`), s.getRange(`B15:B${15+helper.length}`)]);
  chart.setPosition("F5", "N21"); styleChart(chart, "Minimal-composition savings", "Communication saving (%)");
  s.getRange("A29:D29").values = [["声明边界", "是否闭合", "主文写法", "禁止写法"]];
  s.getRange("A30:D33").values = [
    ["通信", true, "paired bytes/op with 95% CI", "无条件全局最优"],
    ["RPC", true, "与通信并列报告", "将 RPC 增加隐藏"],
    ["可信内存峰值", false, "持久对象口径", "peak RSS"],
    ["网络延迟", false, "仅模型讨论", "measured latency improvement"],
  ];
  s.getRange("A29:D29").format.fill = NAVY; s.getRange("A29:D29").format.font = { name: FONT, size: 10, bold: true, color: "#FFFFFF" };
  setWidths(s, {A:28, B:17, C:30, D:31, E:3, F:14, G:14, H:14, I:14, J:14, K:14, L:14, M:14, N:14});
}

// Tuned main comparisons.
{
  const s=sheets["主比较"];
  baseSheet(s,"同调优主比较","N=16,384，B=4,096；seed 级 paired mean 与 Student-t 95% CI。", "V");
  const keys=["comparison","workload","baseline","variant","n","baseline_bytes_per_request","variant_bytes_per_request","bytes_saving_pct","ci95_low_pct","ci95_high_pct","rpc_saving_pct","scope"];
  const headers=["比较","负载","对照","方案","n","对照 B/op","方案 B/op","通信下降 (%)","CI 下界","CI 上界","RPC 下降 (%)","口径"];
  const t=writeTable(s,4,headers,data.tuned,keys,"TunedMain"); applyFormats(s,t,keys);
  s.freezePanes.freezeRows(4);
  const chart=s.charts.add("bar",[s.getRange("A4:A10"),s.getRange("H4:H10")]);
  chart.setPosition("N4","V20"); styleChart(chart,"Tuned communication savings","Saving (%)");
  setWidths(s,{A:18,B:12,C:12,D:12,E:8,F:15,G:15,H:15,I:12,J:12,K:14,L:38,M:3,N:12,O:12,P:12,Q:12,R:12,S:12,T:12,U:12,V:12});
}

// Scale matrix.
{
  const s=sheets["规模矩阵"];
  baseSheet(s,"规模与块大小矩阵","25 个系统格、每格 5 个种子；下表为 15 个成对效应。", "X");
  const keys=["comparison","N","B","baseline","variant","n","baseline_bytes_per_request","variant_bytes_per_request","bytes_saving_pct","ci95_low_pct","ci95_high_pct","rpc_saving_pct"];
  const headers=["比较","N","B","对照","方案","n","对照 B/op","方案 B/op","通信下降 (%)","CI 下界","CI 上界","RPC 下降 (%)"];
  const t=writeTable(s,4,headers,data.scale,keys,"ScaleEffects"); applyFormats(s,t,keys); s.freezePanes.freezeRows(4);
  const comps=["SDE/Path","SDE/Deferred","R0/Ring"];
  s.getRange("N24:Q24").values=[["B (N=16384)",...comps]];
  const Bs=[64,256,1024];
  s.getRange("N25:Q27").values=Bs.map(B=>[B,...comps.map(c=>data.scale.find(r=>r.N===16384&&r.B===B&&r.comparison===c).bytes_saving_pct)]);
  s.getRange("N30:Q30").values=[["N (B=4096)",...comps]];
  const Ns=[4096,65536];
  s.getRange("N31:Q32").values=Ns.map(N=>[N,...comps.map(c=>data.scale.find(r=>r.N===N&&r.B===4096&&r.comparison===c).bytes_saving_pct)]);
  const c1=s.charts.add("line",s.getRange("N24:Q27")); c1.setPosition("N4","X18"); styleChart(c1,"Block-size robustness (N=16,384)","Saving (%)","line");
  const c2=s.charts.add("line",s.getRange("N30:Q32")); c2.setPosition("N35","X49"); styleChart(c2,"Scale robustness (B=4,096)","Saving (%)","line");
  setWidths(s,{A:18,B:12,C:12,D:12,E:12,F:8,G:15,H:15,I:15,J:12,K:12,L:14,M:3,N:18,O:14,P:14,Q:14,R:12,S:12,T:12,U:12,V:12,W:12,X:12});
}

// Minimal composition.
{
  const s=sheets["最小组合"];
  baseSheet(s,"Selective read 最小组合","compact/fusion/root removal/small-map/retuning 全部关闭；只改变逻辑读集合。", "X");
  const keys=["family","layout","B","baseline","variant","n","baseline_bytes_per_request","variant_bytes_per_request","bytes_saving_pct","ci95_low_pct","ci95_high_pct","theory_saving_pct","theory_gap_pp","rpc_saving_pct"];
  const headers=["宿主","布局","B","对照","方案","n","对照 B/op","Selective B/op","通信下降 (%)","CI 下界","CI 上界","理论 (%)","实测-理论 (pp)","RPC 下降 (%)"];
  const t=writeTable(s,4,headers,data.minimal_primary,keys,"MinimalMain"); applyFormats(s,t,keys);
  s.getRange("A17:J17").values=[["归因控制","布局","B","对照","方案","n","对照 B/op","Selective B/op","通信下降 (%)","95% CI"]];
  const ctr=data.minimal_controls.map(r=>[r.family,r.layout,r.B,r.baseline,r.variant,r.n,r.baseline_bytes_per_request,r.variant_bytes_per_request,r.bytes_saving_pct,`[${r.ci95_low_pct.toFixed(3)}, ${r.ci95_high_pct.toFixed(3)}]`]);
  s.getRange(`A18:J${17+ctr.length}`).values=ctr;
  s.getRange("A17:J17").format.fill=TEAL; s.getRange("A17:J17").format.font={name:FONT,size:10,bold:true,color:"#FFFFFF"};
  s.getRange(`G18:I${17+ctr.length}`).setNumberFormat("#,##0.000");
  s.freezePanes.freezeRows(4);
  s.getRange("P24:Q24").values=[["配置","通信下降 (%)"]];
  s.getRange(`P25:Q${24+data.minimal_primary.length}`).values=data.minimal_primary.map(r=>[`${r.family}/${r.layout},B=${r.B}`,r.bytes_saving_pct]);
  const chart=s.charts.add("bar",s.getRange(`P24:Q${24+data.minimal_primary.length}`)); chart.setPosition("P4","X20"); styleChart(chart,"Minimal-composition generality","Saving (%)");
  setWidths(s,{A:17,B:12,C:10,D:13,E:13,F:8,G:15,H:17,I:15,J:12,K:12,L:13,M:17,N:14,O:3,P:24,Q:14,R:12,S:12,T:12,U:12,V:12,W:12,X:12});
}

// Ablation.
{
  const s=sheets["消融"];
  baseSheet(s,"五步消融","small map → compact header → fusion → retuning；joint result 相对共同起点，不能与边际项直接相加。", "T");
  const keys=["step","before","after","n","bytes_saving_pct","ci95_low_pct","ci95_high_pct","rpc_saving_pct","note"];
  const headers=["步骤","之前","之后","n","通信下降 (%)","CI 下界","CI 上界","RPC 下降 (%)","解释"];
  const t=writeTable(s,4,headers,data.ablation,keys,"Ablation"); applyFormats(s,t,keys);
  const chart=s.charts.add("bar",[s.getRange("A4:A9"),s.getRange("E4:E9")]); chart.setPosition("K4","T20"); styleChart(chart,"Separated ablation ladder","Saving (%)");
  setWidths(s,{A:24,B:22,C:22,D:8,E:15,F:12,G:12,H:14,I:24,J:3,K:12,L:12,M:12,N:12,O:12,P:12,Q:12,R:12,S:12,T:12});
}

// Robustness and sensitivity.
{
  const s=sheets["稳健性"];
  baseSheet(s,"公开负载与参数敏感性","公开负载进入正文候选；完整 Freecursive/rho 参数扫描用于附录。", "X");
  const pkeys=["family","workload","baseline","variant","n","bytes_saving_pct","ci95_low_pct","ci95_high_pct","range_low_pct","range_high_pct"];
  const ph=["族","负载","对照","方案","n","通信下降 (%)","CI 下界","CI 上界","窗口最小","窗口最大"];
  const p=writeTable(s,4,ph,data.public,pkeys,"PublicWorkloads"); applyFormats(s,p,pkeys);
  const skeys=["family","axis","name","bytes_saving_pct","ci95_low_pct","ci95_high_pct","rpc_saving_pct","baseline_bytes","variant_bytes","n","needs_more_repeats"];
  const sh=["族","轴","名称","通信下降 (%)","CI 下界","CI 上界","RPC 下降 (%)","对照 B/op","方案 B/op","n","需加重复"];
  const sr=writeTable(s,16,sh,data.sensitivity,skeys,"Sensitivity"); applyFormats(s,sr,skeys); s.freezePanes.freezeRows(4);
  s.getRange("M24:N24").values=[["公开负载比较","通信下降 (%)"]];
  s.getRange(`M25:N${24+data.public.length}`).values=data.public.map(r=>[`${r.family}/${r.workload}/${r.baseline}→${r.variant}`,r.bytes_saving_pct]);
  const chart=s.charts.add("bar",s.getRange(`M24:N${24+data.public.length}`)); chart.setPosition("M4","X20"); styleChart(chart,"Public-workload robustness","Saving (%)");
  setWidths(s,{A:20,B:13,C:24,D:16,E:12,F:15,G:12,H:12,I:13,J:13,K:14,L:3,M:13,N:13,O:13,P:13,Q:13,R:13,S:13,T:13,U:13,V:13,W:13,X:13});
}

// Supplements.
{
  const s=sheets["补充证据"];
  baseSheet(s,"IR 与 AB 补充证据","guarded IR 和条件式 AB+CB 均保留范围标签，不进入原生系统复现主结论。", "N");
  const ikeys=Object.keys(data.ir_supplement[0]);
  const it=writeTable(s,4,ikeys,data.ir_supplement,ikeys,"IRSupplement"); applyFormats(s,it,ikeys);
  const akeys=Object.keys(data.ab_supplement[0]);
  const at=writeTable(s,it.endRow+3,akeys,data.ab_supplement,akeys,"ABSupplement"); applyFormats(s,at,akeys); s.freezePanes.freezeRows(4);
  const ckeys=Object.keys(data.core_existing[0]);
  const ct=writeTable(s,at.endRow+3,ckeys,data.core_existing,ckeys,"CoreExisting"); applyFormats(s,ct,ckeys);
  const pkeys=Object.keys(data.classical[0]);
  const pt=writeTable(s,ct.endRow+3,pkeys,data.classical,pkeys,"ClassicalPath"); applyFormats(s,pt,pkeys);
  setWidths(s,{A:16,B:13,C:13,D:13,E:13,F:9,G:15,H:12,I:12,J:15,K:58,L:18,M:18,N:18});
}

// Resources and audit checks.
{
  const s=sheets["资源审计"];
  baseSheet(s,"资源口径与审计门槛","存储表不是 peak RSS；审计门槛用于约束论文声明。", "P");
  const rkeys=Object.keys(data.resources[0]);
  const rt=writeTable(s,4,rkeys,data.resources,rkeys,"Resources"); applyFormats(s,rt,rkeys);
  const akeys=Object.keys(data.audits[0]);
  const at=writeTable(s,rt.endRow+3,akeys,data.audits,akeys,"AuditChecks"); applyFormats(s,at,akeys);
  const ekeys=Object.keys(data.environment[0]);
  const et=writeTable(s,at.endRow+3,ekeys,data.environment,ekeys,"Environment"); applyFormats(s,et,ekeys);
  const statusCol=colLetter(at.startCol+akeys.indexOf("status"));
  s.getRange(`${statusCol}${at.startRow+1}:${statusCol}${at.endRow}`).conditionalFormats.add("containsText",{text:"not measured",format:{fill:"#FDECEC",font:{color:RED,bold:true}}});
  s.freezePanes.freezeRows(4);
  setWidths(s,{A:24,B:16,C:13,D:13,E:16,F:20,G:20,H:21,I:17,J:16,K:22,L:56,M:16,N:16,O:16,P:16});
}

// Raw runs: two adjacent intact observation tables.
{
  const s=sheets["原始运行"];
  baseSheet(s,"正式运行原始索引","每行一个 seed 级观察；左侧 120 条最小组合，右侧 125 条规模实验。", "AL");
  const mkeys=Object.keys(data.minimal_runs[0]);
  const skeys=Object.keys(data.scale_runs[0]);
  const mt=writeTable(s,4,mkeys,data.minimal_runs,mkeys,"MinimalRaw"); applyFormats(s,mt,mkeys);
  const startCol=mkeys.length+3;
  const st=writeTable(s,4,skeys,data.scale_runs,skeys,"ScaleRaw",{startCol}); applyFormats(s,st,skeys);
  s.freezePanes.freezeRows(4); s.freezePanes.freezeColumns(2);
  for(let i=1;i<=mkeys.length;i++) s.getRange(`${colLetter(i)}:${colLetter(i)}`).format.columnWidth = /sha256|receipt/.test(mkeys[i-1])?28:14;
  for(let i=1;i<=skeys.length;i++) s.getRange(`${colLetter(startCol+i-1)}:${colLetter(startCol+i-1)}`).format.columnWidth = /sha256|receipt/.test(skeys[i-1])?28:14;
}

// Evidence index.
{
  const s=sheets["证据索引"];
  baseSheet(s,"证据文件与 SHA-256","所有来源副本和生成件的可追溯索引。", "J");
  const rows=data.evidence_index;
  const keys=["type","source","copy","sha256"];
  const t=writeTable(s,4,["类型","原始路径","包内路径","SHA-256"],rows,keys,"EvidenceIndex");
  s.freezePanes.freezeRows(4);
  setWidths(s,{A:20,B:62,C:62,D:68,E:12,F:12,G:12,H:12,I:12,J:12});
}

// Workbook-wide calculated presentation and validation.
for (const s of Object.values(sheets)) {
  const used=s.getUsedRange();
  if (used) used.format.verticalAlignment="center";
}
await wb.recalculate();

const inspections = {};
inspections.sheets = (await wb.inspect({ kind:"sheet", include:"id,name", maxChars:5000 })).ndjson;
inspections.summary = (await wb.inspect({ kind:"region", sheetId:"总览", range:"A1:N35", maxChars:7000 })).ndjson;
inspections.formulas = (await wb.inspect({ kind:"formula", sheetId:"总览", range:"A1:N35", maxChars:5000, options:{maxResults:50} })).ndjson;
inspections.drawings = (await wb.inspect({ kind:"drawing", maxChars:7000 })).ndjson;
for (const token of ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"]) {
  if ((inspections.summary || "").includes(token)) throw new Error(`formula error ${token}`);
}

const previewRanges = {
  "总览":"A1:N35",
  "主比较":"A1:V20",
  "规模矩阵":"A1:X49",
  "最小组合":"A1:X35",
  "消融":"A1:T20",
  "稳健性":"A1:X55",
  "补充证据":"A1:N55",
  "资源审计":"A1:P45",
  "原始运行":"A1:AL25",
  "证据索引":"A1:J25",
};
for (const [name, s] of Object.entries(sheets)) {
  const preview=await wb.render({ sheetName:name, range:previewRanges[name], autoCrop:"all", scale:0.85, format:"png" });
  await fs.writeFile(path.join(previewDir,`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}

const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(outputPath);

// Re-import the exported workbook to catch serialization failures.
const imported=await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
inspections.reimport = (await imported.inspect({ kind:"workbook,sheet,table,drawing", maxChars:10000, tableMaxRows:3, tableMaxCols:6 })).ndjson;
await fs.writeFile(path.join(outDir,"workbook_qa.json"),JSON.stringify(inspections,null,2),"utf8");

console.log(JSON.stringify({status:"complete",output:outputPath,sheets:Object.keys(sheets).length,previews:Object.keys(sheets).length}));
