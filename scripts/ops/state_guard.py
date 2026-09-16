#!/usr/bin/env python3
"""AstroLove operasyon durumunu doğrula ve çelişkide kapalı kal.

Kanonik kaynak: config/operational_state.json
Bu kontrol geçmeden batch raporu üretilmez.
"""
import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "config" / "operational_state.json"
COMPLETION_LEDGER = ROOT / "config" / "completed_operations.json"
STATUS_DOC = ROOT / "docs" / "OPERATIONS_STATUS.md"
ALLOWED = {"completed", "pending_approval", "pending_input", "blocked"}

# Bu dizeler aktif belgelerde yeniden görünürse tamamlanan iş yanlışlıkla açılmıştır.
STALE_ASSERTIONS = {
    ROOT / "scripts" / "night2" / "batch4.py": [
        "| 3 | GPSR panel girisi |",
        "| 5 | Workflow hardening merge |",
    ],
    ROOT / "docs" / "night2" / "RUNBOOKS.md": [
        "## R1 - GPSR panel girisi (78 POD ilani)",
        "**Gerekli onay:** Serdar'in yazili onayi. API'de GPSR alani YOK; islem tamamen elle.",
    ],
    ROOT / "docs" / "POD_LISTING_TEMPLATE.md": [
        "GPSR uretici/sorumlu kisi alanlari: Prodigi cevabi sonrasi (simdilik bos).",
    ],
    ROOT / "docs" / "batch4" / "workflow_final_test.md": [
        "main'e merge EDILMEDI",
        "Merge onayi: branch main'e alinmadi.",
    ],
}


def load_state(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("desteklenmeyen schema_version")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks bos veya gecersiz")
    ids = [x.get("id") for x in tasks]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("task id bos veya tekrarli")
    for task in tasks:
        if task.get("status") not in ALLOWED:
            raise ValueError(f"gecersiz durum: {task.get('id')}={task.get('status')}")
        if task["status"] == "completed" and not task.get("evidence"):
            raise ValueError(f"tamamlanan iste kanit yok: {task['id']}")
    return data


def render(data):
    labels = {
        "completed": "TAMAMLANDI",
        "pending_approval": "ONAY BEKLIYOR",
        "pending_input": "GIRDI BEKLIYOR",
        "blocked": "BLOKE",
    }
    lines = [
        "# AstroLove Operasyon Durumu",
        "",
        f"Guncelleme: **{data['as_of']}**",
        "",
        "> Bu belge `config/operational_state.json` dosyasindan uretilir. Tamamlanan işler",
        "> `config/completed_operations.json` defteriyle tek yönlü kilitlenir. Eski batch raporlari durum kaynagi degildir.",
        "",
        "| oncelik | is | durum | kapsam | kanit / hazir dosya |",
        "|---:|---|---|---|---|",
    ]
    for task in sorted(data["tasks"], key=lambda x: (x.get("priority", 999), x["id"])):
        if task["status"] == "completed":
            proof = "; ".join(x["path"] for x in task["evidence"])
        else:
            proof = task.get("ready_file", "-")
        lines.append(
            f"| {task.get('priority', 999)} | {task['name']} | **{labels[task['status']]}** | "
            f"{task.get('scope', '-')} | `{proof}` |"
        )
    lines += [
        "",
        "## Zorunlu karar kurali",
        "",
        "1. Bir isin durumu yalnizca kanonik JSON kaydindan okunur.",
        "2. Tamamlanma defterindeki bir is yeniden bekleyenler listesine eklenemez.",
        "3. Kanit eksikse veya belgeler celisiyorsa kontrol FAIL olur; sonraki is onerilmez.",
        "4. Canli islem, durum `pending_approval` olsa bile Serdar'in o isleme ozel acik onayi olmadan baslamaz.",
        "",
    ]
    return "\n".join(lines)


def load_ledger(path=COMPLETION_LEDGER):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("records"), list):
        raise ValueError("tamamlanma defteri gecersiz")
    ids = [x.get("task_id") for x in data["records"]]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("tamamlanma defterinde task_id bos veya tekrarli")
    return data


def validate(data, ledger):
    errors = []
    tasks_by_id = {x["id"]: x for x in data["tasks"]}
    # Tamamlanma defteri tek yonlu kilittir: kayda giren is yeniden pending olamaz.
    for record in ledger["records"]:
        task = tasks_by_id.get(record["task_id"])
        if not task:
            errors.append(f"tamamlanan is durum kaydinda yok: {record['task_id']}")
            continue
        if task["status"] != "completed":
            errors.append(f"tamamlanan is yeniden acilmis: {record['task_id']}={task['status']}")
        ev = record["evidence"]
        path = ROOT / ev["path"]
        if not path.exists() or ev["contains"] not in path.read_text(encoding="utf-8"):
            errors.append(f"tamamlanma defteri kaniti gecersiz: {record['task_id']}")
    for task in data["tasks"]:
        if task["status"] != "completed":
            continue
        for ev in task["evidence"]:
            path = ROOT / ev["path"]
            if not path.exists():
                errors.append(f"kanit dosyasi yok: {task['id']} -> {ev['path']}")
                continue
            text = path.read_text(encoding="utf-8")
            if ev["contains"] not in text:
                errors.append(f"kanit metni yok: {task['id']} -> {ev['path']}")
    for path, needles in STALE_ASSERTIONS.items():
        if not path.exists():
            errors.append(f"kontrollu belge yok: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                errors.append(f"eski durum iddiasi: {path.relative_to(ROOT)} -> {needle}")
    expected = render(data)
    if not STATUS_DOC.exists() or STATUS_DOC.read_text(encoding="utf-8") != expected:
        errors.append("docs/OPERATIONS_STATUS.md kanonik kayitla ayni degil")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE)
    ap.add_argument("--write", action="store_true", help="durum belgesini yeniden uret")
    ap.add_argument("--next", action="store_true", help="siradaki dogrulanmis isi yaz")
    args = ap.parse_args()
    try:
        data = load_state(args.state)
        ledger = load_ledger()
        if args.write:
            STATUS_DOC.write_text(render(data), encoding="utf-8")
        errors = validate(data, ledger)
    except Exception as exc:  # fail-closed
        print(f"FAIL: operasyon durumu okunamadi: {exc}", file=sys.stderr)
        return 2
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    if args.next:
        pending = [x for x in data["tasks"] if x["status"] != "completed"]
        pending.sort(key=lambda x: (x.get("priority", 999), x["id"]))
        if pending:
            task = pending[0]
            print(f"{task['id']} | {task['name']} | {task['status']} | {task.get('scope', '-')}")
        else:
            print("bekleyen is yok")
    else:
        print(f"PASS: {len(data['tasks'])} operasyon kaydi dogrulandi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
