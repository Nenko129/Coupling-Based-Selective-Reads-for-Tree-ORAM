"""Finalize and independently verify the consolidated paper evidence bundle."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


HOME = Path(__file__).resolve().parents[1]
OUT = HOME / "论文实验章节完整证据_2026-09-16"
ZIP = HOME / "TDSC论文实验阶段证据总包_2026-09-16.zip"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def load(path):return json.loads(path.read_text(encoding="utf-8"))
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    assert OUT.resolve().parent == HOME.resolve()
    manifest_path=OUT/"evidence_manifest.json"; manifest=load(manifest_path)
    workbook=OUT/"TDSC论文实验数据总表.xlsx"
    qa=OUT/"workbook_qa.json"
    assert workbook.exists() and workbook.stat().st_size>50_000
    assert qa.exists() and len(list((OUT/"workbook_previews").glob("*.png")))==10
    extra=[workbook,qa,OUT/"README.md"]+sorted((OUT/"workbook_previews").glob("*.png"))
    known={r["copy"] for r in manifest["files"]}
    for p in extra:
        rel=str(p.relative_to(OUT))
        if rel not in known:
            manifest["files"].append({"type":"workbook_or_qa","source":None,"copy":rel,"sha256":sha(p)})
    manifest["workbook"]={"path":workbook.name,"sha256":sha(workbook),"sheets":10,"previews":10}
    save(manifest_path,manifest)

    min_receipts=list((OUT/"source_evidence"/"receipts_minimal_120").glob("*.json"))
    scale_receipts=list((OUT/"source_evidence"/"receipts_scale_125").glob("*.json"))
    tables=list((OUT/"tables").glob("*")); figures=list((OUT/"figures").glob("*"))
    assert len(min_receipts)==120 and len(scale_receipts)==125
    assert len([p for p in figures if p.suffix==".png"])==7
    assert len([p for p in figures if p.suffix==".svg"])==7
    assert len([p for p in figures if p.suffix==".pdf"])==7
    for row in manifest["files"]:
        p=OUT/row["copy"]
        assert p.exists(),row["copy"]
        assert sha(p)==row["sha256"],row["copy"]
    validation={
        "status":"passed","minimal_receipts":len(min_receipts),"scale_receipts":len(scale_receipts),
        "tables":len(tables),"figure_files":len(figures),"workbook_bytes":workbook.stat().st_size,
        "workbook_sha256":sha(workbook),"manifest_entries":len(manifest["files"]),
        "limits":{"true_trusted_peak":False,"real_network_latency":False,"native_four_host_reproduction":False},
    }
    save(OUT/"bundle_validation.json",validation)

    if ZIP.exists():ZIP.unlink()
    with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():z.write(p,p.relative_to(HOME))
    with zipfile.ZipFile(ZIP) as z:
        bad=z.testzip();assert bad is None
        names=z.namelist();assert len(names)==len(set(names))
    validation["zip"]={"path":str(ZIP),"bytes":ZIP.stat().st_size,"sha256":sha(ZIP)}
    save(OUT/"bundle_validation.json",validation)
    print(json.dumps(validation,ensure_ascii=False))


if __name__=="__main__":main()
