import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'outputs','01a09f23-0c2e-75e3-9ce5-d8ef0a277d5e');
const preview=path.join(output,'preview');
await fs.mkdir(preview,{recursive:true});
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const audit=await read('results/frontend_batch_audit.json');
const raw=[];const byKey=new Map();const bindings=[];
const components=['data_download','data_upload','headers_download','headers_upload','authentication_download','authentication_upload','framing_and_control'];
for(const report of audit.reports){
  const folder=report.family_group==='free'?'formal_composition':'formal_rho_fixed';
  for(const entry of report.rows){
    const rel=`results/${folder}/${entry.id}.json`;
    const bytes=await fs.readFile(path.join(root,rel));assert.equal(hash(bytes),entry.sha256);
    const r=JSON.parse(bytes),s=r.spec,m=r.phases.measurement;
    assert.equal(r.status,'passed');assert.equal(s.N,4096);assert.equal(s.B,64);
    assert.equal(s.requests,4096);assert.equal(m.requests,s.requests);
    const sum=k=>m.bills.reduce((a,b)=>a+b[k],0);
    const c=components.map(k=>m.bills.reduce((a,b)=>a+(b.components[k]??0),0));
    assert.equal(sum('total_bytes'),m.total_bytes);assert.equal(sum('request_bytes')+sum('response_bytes'),m.total_bytes);
    assert.equal(c.reduce((a,b)=>a+b,0),m.total_bytes);
    const row=[s.id,s.family,s.workload,s.kind,s.trace_seed,s.N,s.B,s.requests,m.total_bytes,sum('response_bytes'),sum('request_bytes'),m.rpc,...c,s.profile.join('/'),rel,entry.sha256];
    raw.push(row);byKey.set([s.family,s.workload,s.kind,s.trace_seed].join('/'),r);bindings.push({file:rel,sha256:entry.sha256});
  }
}
assert.equal(raw.length,240);assert.equal(byKey.size,240);
raw.sort((a,b)=>a[0].localeCompare(b[0]));
const stats=await read('results/paired_statistics.json');
const groups=[];
for(const family of ['free_raw','free_compressed','rho'])for(const w of ['uniform','hot90','zipf09','scan'])for(const [base,newKind] of [['deferred','sde'],['ring','r0']]){
  const reference=stats.rows.filter(r=>r.family===family&&r.workload===w&&r.N===4096&&r.B===64&&r.baseline===base&&r.selective===newKind);
  assert.equal(reference.length,1);assert.equal(reference[0].n,5);
  groups.push({family,w,base,newKind,key:`${family} / ${w} / ${newKind} vs ${base}`,reference:reference[0]});
}
const wb=Workbook.create();
const summary=wb.worksheets.add('结果');
const pairs=wb.worksheets.add('配对计算');
const source=wb.worksheets.add('原始运行');
const dark='#243B53',light='#EDF2F7',ink='#243746';
function baseStyle(sheet,range){sheet.showGridLines=false;sheet.getRange(range).format.font={name:'Arial',size:10,color:ink};sheet.getRange(range).format.rowHeight=22;sheet.getRange(range).format.verticalAlignment='center';}
function header(sheet,range){sheet.getRange(range).format={fill:dark,font:{name:'Arial',size:10,color:'#FFFFFF',bold:true},rowHeight:28,horizontalAlignment:'center',verticalAlignment:'center'};}
function title(sheet,cell,value){sheet.getRange(cell).values=[[value]];sheet.getRange(cell).format.font={name:'Arial',size:15,bold:true,color:dark};}
baseStyle(source,'A1:V242');
source.getRange('A1:V1').values=[['运行ID','前端','工作负载','后端','种子','N（块）','B（字节）','请求数','总字节','下行字节','上行字节','RPC','数据下行字节','数据上行字节','头部下行字节','头部上行字节','认证下行字节','认证上行字节','帧及控制字节','参数Z/A/S','原始证据相对路径','SHA-256']];
source.getRange('A2:V241').values=raw;
source.getRange('A1:A241').format.columnWidth=65;source.getRange('B1:B241').format.columnWidth=21;
source.getRange('C1:D241').format.columnWidth=15;source.getRange('E1:H241').format.columnWidth=12;
source.getRange('I1:S241').format.columnWidth=19;source.getRange('U1:U241').format.columnWidth=100;source.getRange('V1:V241').format.columnWidth=68;
source.getRange('T1:T241').format.columnWidth=14;
source.getRange('E2:S241').setNumberFormat('#,##0');header(source,'A1:V1');
source.tables.add('A1:V241',true,'RawRuns');source.freezePanes.freezeRows(1);source.freezePanes.freezeColumns(1);

baseStyle(pairs,'A1:H128');title(pairs,'A2','逐种子配对计算');
pairs.getRange('A3').values=[['节省率 = 1 − selective 字节/请求 ÷ 基线字节/请求。原始数据通过运行ID精确匹配。']];
pairs.getRange('A5:H5').values=[['比较组','种子','基线运行ID','selective运行ID','基线字节/请求','selective字节/请求','节省率','节省率平方']];
const pairRows=[];
for(const g of groups)for(let seed=101;seed<=105;seed++){
  const a=byKey.get([g.family,g.w,g.base,seed].join('/')),b=byKey.get([g.family,g.w,g.newKind,seed].join('/'));
  assert.deepEqual(a.trace,b.trace);assert.deepEqual(a.phases.measurement.schedules,b.phases.measurement.schedules);
  pairRows.push([g.key,seed,a.spec.id,b.spec.id]);
}
pairs.getRange('A6:D125').values=pairRows;
pairs.getRange('E6:H6').formulas=[[
  "=INDEX('原始运行'!$I$2:$I$241,MATCH(C6,'原始运行'!$A$2:$A$241,0))/INDEX('原始运行'!$H$2:$H$241,MATCH(C6,'原始运行'!$A$2:$A$241,0))",
  "=INDEX('原始运行'!$I$2:$I$241,MATCH(D6,'原始运行'!$A$2:$A$241,0))/INDEX('原始运行'!$H$2:$H$241,MATCH(D6,'原始运行'!$A$2:$A$241,0))",
  '=1-F6/E6','=G6^2'
]];pairs.getRange('E6:H125').fillDown();
pairs.getRange('A1:A128').format.columnWidth=62;pairs.getRange('B1:B128').format.columnWidth=9;
pairs.getRange('C1:D128').format.columnWidth=65;pairs.getRange('E1:F128').format.columnWidth=23;pairs.getRange('G1:H128').format.columnWidth=18;
pairs.getRange('E6:F125').setNumberFormat('#,##0.00');pairs.getRange('G6:G125').setNumberFormat('0.00%');pairs.getRange('H6:H125').setNumberFormat('0.000000');header(pairs,'A5:H5');
pairs.tables.add('A5:H125',true,'PairedRuns');pairs.freezePanes.freezeRows(5);pairs.freezePanes.freezeColumns(2);

baseStyle(summary,'A1:H37');title(summary,'A2','Freecursive 与 ρ 通信量实验');
summary.getRange('A3').values=[['N=4,096，B=64字节。每组5次独立运行，预热2,048次，测量4,096次。']];
summary.getRange('A4').values=[['双向协议通信含密文、头部、认证和帧开销。范围为已实现组件。']];
summary.getRange('A5').values=[['t 临界值（双侧95%，自由度4）']];summary.getRange('B5').values=[[2.7764451051977987]];summary.getRange('B5').setNumberFormat('0.000000');
summary.getRange('A7:H7').values=[['比较组','重复数','基线字节/请求','selective字节/请求','平均节省','样本标准差','95%下限','95%上限']];
summary.getRange('A8:A31').values=groups.map(g=>[g.key]);
summary.getRange('B8:H8').formulas=[[
  "=COUNTIFS('配对计算'!$A$6:$A$125,$A8)",
  "=AVERAGEIFS('配对计算'!$E$6:$E$125,'配对计算'!$A$6:$A$125,$A8)",
  "=AVERAGEIFS('配对计算'!$F$6:$F$125,'配对计算'!$A$6:$A$125,$A8)",
  "=AVERAGEIFS('配对计算'!$G$6:$G$125,'配对计算'!$A$6:$A$125,$A8)",
  "=SQRT(MAX(0,(SUMIFS('配对计算'!$H$6:$H$125,'配对计算'!$A$6:$A$125,$A8)-B8*E8^2)/(B8-1)))",
  '=E8-$B$5*F8/SQRT(B8)','=E8+$B$5*F8/SQRT(B8)'
]];summary.getRange('B8:H31').fillDown();
summary.getRange('A33').values=[['平均节省为逐运行节省率的均值。区间以独立运行作为统计单位。']];
summary.getRange('A34').values=[['free_raw 为原始位置表，free_compressed 为压缩位置表。两者均只比较同一前端中的后端替换。']];
summary.getRange('A35').values=[['ρ 的数据为前树与后树的合计。未把后端自身节省当成整体节省。']];
summary.getRange('A36').values=[['本表未纳入IR、AB的未完成重复，也未纳入后续敏感性和公开负载批次。']];
summary.getRange('A1:A37').format.columnWidth=62;summary.getRange('B1:B37').format.columnWidth=12;
summary.getRange('C1:D37').format.columnWidth=23;summary.getRange('E1:H37').format.columnWidth=17;
summary.getRange('C8:D31').setNumberFormat('#,##0.00');summary.getRange('E8:H31').setNumberFormat('0.00%');header(summary,'A7:H7');
for(let i=0;i<3;i++)if(i%2===0)summary.getRange(`A${8+i*8}:H${15+i*8}`).format.fill=light;
summary.getRange('E8:E31').format.font.bold=true;summary.tabColor=dark;
wb.recalculate();
// Independent reference checks cover every displayed mean and CI, not just selected examples.
const calculated=summary.getRange('B8:H31').values;
for(let i=0;i<groups.length;i++){
  const a=calculated[i],r=groups[i].reference;assert.equal(a[0],5);
  for(const [actual,expected] of [[a[1],r.baseline_mean_bytes],[a[2],r.selective_mean_bytes],[a[3],r.paired_mean_saving_pct/100],[a[5],r.ci95[0]/100],[a[6],r.ci95[1]/100]])assert.ok(Math.abs(actual-expected)<1e-8,`${groups[i].key}: ${actual} != ${expected}`);
}
// Input perturbation and restoration proves that lookups, paired values, and summaries recalculate.
const old=source.getRange('I2').values[0][0];const before=summary.getRange('E8:E31').values.flat();
source.getRange('I2').values=[[old*1.01]];wb.recalculate();const changed=summary.getRange('E8:E31').values.flat();
assert.equal(changed.filter((v,i)=>Math.abs(v-before[i])>1e-10).length,1);
source.getRange('I2').values=[[old]];wb.recalculate();
assert.deepEqual(summary.getRange('E8:E31').values.flat(),before);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'});
await fs.writeFile(path.join(preview,'formula_scan.json'),errors.ndjson);
for(const [sheetName,range,name] of [['结果','A1:H37','summary'],['配对计算','A1:H12','pairs'],['原始运行','A1:L8','raw_main'],['原始运行','M1:V8','raw_details']]){
  const img=await wb.render({sheetName,range,scale:1.3,format:'png'});await fs.writeFile(path.join(preview,`${name}.png`),new Uint8Array(await img.arrayBuffer()));
}
const filename=path.join(output,'Freecursive_rho_基础实验.xlsx');await(await SpreadsheetFile.exportXlsx(wb)).save(filename);
await fs.writeFile(path.join(output,'workbook_receipt.json'),JSON.stringify({file:filename,sha256:hash(await fs.readFile(filename)),runs:240,paired_runs:120,comparison_groups:24,all_means_and_ci_checked:true,input_change_and_restore_checked:true,bindings,engine:'artifact-tool; native Excel not executed'},null,2));
console.log(JSON.stringify({file:filename,runs:240,pairs:120,groups:24,verified:true}));
