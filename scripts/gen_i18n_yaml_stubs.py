"""Generate 13 YAML stub i18n catalogs for v0.4.x.

Each stub contains:
- A `_meta` block with native-script locale name + draft=true
- A handful of the most-visible top-level strings translated
- The remaining ~200 keys fall through to English at lookup time

This is a best-effort draft to demonstrate the i18n machinery scales
to 16 locales. Native-speaker review is required before promoting
any of these to draft=false.
"""

import json
from pathlib import Path
from typing import Any

I18N_DIR = Path(r"D:\LoopOS\loopos\i18n")

# Source: English catalog (canonical).
with (I18N_DIR / "en.json").open(encoding="utf-8") as f:
    EN = json.load(f)

# Each entry: (id, native_name, english_name, rtl, sample_translations)
# sample_translations: dict[en_key, native_string] -- if missing, falls
# back to English. Keep it small: just the most-visible top-level
# keys, so native reviewers have a starting point.
LOCALES = [
    (
        "de",
        "Deutsch",
        "German",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Projekt-Trainings-Laufzeit",
            "panel.run.title": "Schleife ausführen",
            "panel.run.run_label": "Lauf",
            "panel.run.status_label": "Status",
            "panel.deliver.title": "Bereitstellung",
            "panel.status.title": "Schleifenstatus",
            "panel.review.title": "Prüfung",
            "panel.repair.title": "Reparaturplan",
            "panel.optimize.title": "Optimierer",
            "commands.loop.help": "Projekttrainings-Schleife ausführen/prüfen/reparieren",
            "commands.locale.help": "CLI-Sprache anzeigen oder festlegen",
            "status.ready_to_deliver": "bereit_zur_Bereitstellung",
            "status.blocked": "blockiert",
            "status.failed": "fehlgeschlagen",
            "status.continue": "weitermachen",
            "status.deliver": "bereitstellen",
            "status.iteration_budget_exhausted": "Iterationsbudget_erschöpft",
            "severity.info": "Info",
            "severity.low": "niedrig",
            "severity.medium": "mittel",
            "severity.high": "hoch",
            "severity.critical": "kritisch",
        },
    ),
    (
        "es",
        "Español",
        "Spanish",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Tiempo de ejecución de entrenamiento del proyecto",
            "panel.run.title": "ejecutar bucle",
            "panel.run.run_label": "Ejecución",
            "panel.run.status_label": "Estado",
            "panel.deliver.title": "Entrega",
            "panel.status.title": "Estado del bucle",
            "panel.review.title": "Revisión",
            "panel.repair.title": "Plan de reparación",
            "panel.optimize.title": "Optimizador",
            "commands.loop.help": "Ejecutar/revisar/reparar el bucle de entrenamiento del proyecto",
            "commands.locale.help": "Ver o establecer el idioma de la CLI",
            "status.ready_to_deliver": "listo_para_entregar",
            "status.blocked": "bloqueado",
            "status.failed": "fallido",
            "status.continue": "continuar",
            "status.deliver": "entregar",
            "status.iteration_budget_exhausted": "presupuesto_de_iteración_agotado",
            "severity.info": "Info",
            "severity.low": "bajo",
            "severity.medium": "medio",
            "severity.high": "alto",
            "severity.critical": "crítico",
        },
    ),
    (
        "fr",
        "Français",
        "French",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Exécution d'entraînement de projet",
            "panel.run.title": "exécution de boucle",
            "panel.run.run_label": "Exécution",
            "panel.run.status_label": "Statut",
            "panel.deliver.title": "Livraison",
            "panel.status.title": "Statut de boucle",
            "panel.review.title": "Revue",
            "panel.repair.title": "Plan de réparation",
            "panel.optimize.title": "Optimiseur",
            "commands.loop.help": "Exécuter/vérifier/réparer la boucle d'entraînement du projet",
            "commands.locale.help": "Voir ou définir la langue de la CLI",
            "status.ready_to_deliver": "prêt_à_livrer",
            "status.blocked": "bloqué",
            "status.failed": "échoué",
            "status.continue": "continuer",
            "status.deliver": "livrer",
            "status.iteration_budget_exhausted": "budget_itérations_épuisé",
            "severity.info": "Info",
            "severity.low": "faible",
            "severity.medium": "moyen",
            "severity.high": "élevé",
            "severity.critical": "critique",
        },
    ),
    (
        "it",
        "Italiano",
        "Italian",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Runtime di addestramento del progetto",
            "panel.run.title": "esecuzione del ciclo",
            "panel.run.run_label": "Esecuzione",
            "panel.run.status_label": "Stato",
            "panel.deliver.title": "Consegna",
            "panel.status.title": "Stato del ciclo",
            "panel.review.title": "Revisione",
            "panel.repair.title": "Piano di riparazione",
            "panel.optimize.title": "Ottimizzatore",
            "commands.loop.help": "Esegui/controlla/ripara il ciclo di addestramento del progetto",
            "commands.locale.help": "Visualizza o imposta la lingua della CLI",
            "status.ready_to_deliver": "pronto_per_la_consegna",
            "status.blocked": "bloccato",
            "status.failed": "fallito",
            "status.continue": "continua",
            "status.deliver": "consegnare",
            "status.iteration_budget_exhausted": "budget_iterazioni_esaurito",
            "severity.info": "Info",
            "severity.low": "basso",
            "severity.medium": "medio",
            "severity.high": "alto",
            "severity.critical": "critico",
        },
    ),
    (
        "pt",
        "Português",
        "Portuguese",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Tempo de execução de treinamento do projeto",
            "panel.run.title": "execução do loop",
            "panel.run.run_label": "Execução",
            "panel.run.status_label": "Estado",
            "panel.deliver.title": "Entrega",
            "panel.status.title": "Estado do loop",
            "panel.review.title": "Revisão",
            "panel.repair.title": "Plano de reparo",
            "panel.optimize.title": "Otimizador",
            "commands.loop.help": "Executar/verificar/reparar o loop de treinamento do projeto",
            "commands.locale.help": "Ver ou definir o idioma da CLI",
            "status.ready_to_deliver": "pronto_para_entregar",
            "status.blocked": "bloqueado",
            "status.failed": "falhou",
            "status.continue": "continuar",
            "status.deliver": "entregar",
            "status.iteration_budget_exhausted": "orçamento_iteração_esgotado",
            "severity.info": "Info",
            "severity.low": "baixo",
            "severity.medium": "médio",
            "severity.high": "alto",
            "severity.critical": "crítico",
        },
    ),
    (
        "ja",
        "日本語",
        "Japanese",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "プロジェクト訓練ランタイム",
            "panel.run.title": "ループ実行",
            "panel.run.run_label": "実行",
            "panel.run.status_label": "状態",
            "panel.deliver.title": "配信",
            "panel.status.title": "ループ状態",
            "panel.review.title": "レビュー",
            "panel.repair.title": "修復計画",
            "panel.optimize.title": "オプティマイザ",
            "commands.loop.help": "プロジェクト訓練ループを実行/確認/修復",
            "commands.locale.help": "CLI言語を表示または設定",
            "status.ready_to_deliver": "配信準備完了",
            "status.blocked": "ブロック中",
            "status.failed": "失敗",
            "status.continue": "続行",
            "status.deliver": "配信",
            "status.iteration_budget_exhausted": "反復予算枯渇",
            "severity.info": "情報",
            "severity.low": "低",
            "severity.medium": "中",
            "severity.high": "高",
            "severity.critical": "重大",
        },
    ),
    (
        "ko",
        "한국어",
        "Korean",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "프로젝트 훈련 런타임",
            "panel.run.title": "루프 실행",
            "panel.run.run_label": "실행",
            "panel.run.status_label": "상태",
            "panel.deliver.title": "전달",
            "panel.status.title": "루프 상태",
            "panel.review.title": "검토",
            "panel.repair.title": "수리 계획",
            "panel.optimize.title": "최적화기",
            "commands.loop.help": "프로젝트 훈련 루프 실행/확인/수리",
            "commands.locale.help": "CLI 언어 표시 또는 설정",
            "status.ready_to_deliver": "전달_준비_완료",
            "status.blocked": "차단됨",
            "status.failed": "실패",
            "status.continue": "계속",
            "status.deliver": "전달",
            "status.iteration_budget_exhausted": "반복_예산_소진",
            "severity.info": "정보",
            "severity.low": "낮음",
            "severity.medium": "중간",
            "severity.high": "높음",
            "severity.critical": "심각",
        },
    ),
    (
        "tr",
        "Türkçe",
        "Turkish",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Proje eğitim çalışma zamanı",
            "panel.run.title": "döngü çalıştır",
            "panel.run.run_label": "Çalıştır",
            "panel.run.status_label": "Durum",
            "panel.deliver.title": "Teslim",
            "panel.status.title": "Döngü durumu",
            "panel.review.title": "İnceleme",
            "panel.repair.title": "Onarım planı",
            "panel.optimize.title": "Optimize edici",
            "commands.loop.help": "Proje eğitim döngüsünü çalıştır/denetle/onar",
            "commands.locale.help": "CLI dilini görüntüle veya ayarla",
            "status.ready_to_deliver": "teslime_hazır",
            "status.blocked": "engellendi",
            "status.failed": "başarısız",
            "status.continue": "devam",
            "status.deliver": "teslim",
            "status.iteration_budget_exhausted": "iterasyon_bütçesi_tükendi",
            "severity.info": "Bilgi",
            "severity.low": "düşük",
            "severity.medium": "orta",
            "severity.high": "yüksek",
            "severity.critical": "kritik",
        },
    ),
    (
        "uk",
        "Українська",
        "Ukrainian",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Середовище виконання тренування проєкту",
            "panel.run.title": "запуск циклу",
            "panel.run.run_label": "Запуск",
            "panel.run.status_label": "Стан",
            "panel.deliver.title": "Доставка",
            "panel.status.title": "Стан циклу",
            "panel.review.title": "Перегляд",
            "panel.repair.title": "План ремонту",
            "panel.optimize.title": "Оптимізатор",
            "commands.loop.help": "Запуск/перевірка/ремонт циклу тренування проєкту",
            "commands.locale.help": "Переглянути або встановити мову CLI",
            "status.ready_to_deliver": "готово_до_доставки",
            "status.blocked": "заблоковано",
            "status.failed": "невдача",
            "status.continue": "продовжити",
            "status.deliver": "доставити",
            "status.iteration_budget_exhausted": "бюджет_ітерацій_вичерпано",
            "severity.info": "Інфо",
            "severity.low": "низький",
            "severity.medium": "середній",
            "severity.high": "високий",
            "severity.critical": "критичний",
        },
    ),
    (
        "hu",
        "Magyar",
        "Hungarian",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Projekt tréning futtatókörnyezet",
            "panel.run.title": "ciklus futtatás",
            "panel.run.run_label": "Futtatás",
            "panel.run.status_label": "Állapot",
            "panel.deliver.title": "Szállítás",
            "panel.status.title": "Ciklus állapota",
            "panel.review.title": "Áttekintés",
            "panel.repair.title": "Javítási terv",
            "panel.optimize.title": "Optimalizáló",
            "commands.loop.help": "Projekt tréning ciklus futtatása/ellenőrzése/javítása",
            "commands.locale.help": "CLI nyelv megtekintése vagy beállítása",
            "status.ready_to_deliver": "szállításra_kész",
            "status.blocked": "blokkolva",
            "status.failed": "sikertelen",
            "status.continue": "folytatás",
            "status.deliver": "szállítás",
            "status.iteration_budget_exhausted": "iterációs_költségvetés_kimerült",
            "severity.info": "Infó",
            "severity.low": "alacsony",
            "severity.medium": "közepes",
            "severity.high": "magas",
            "severity.critical": "kritikus",
        },
    ),
    (
        "ga",
        "Gaeilge",
        "Irish",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Am rith traenála tionscadail",
            "panel.run.title": "rith an lúb",
            "panel.run.run_label": "Rith",
            "panel.run.status_label": "Stádas",
            "panel.deliver.title": "Seachadadh",
            "panel.status.title": "Stádas an lúb",
            "panel.review.title": "Athbhreithniú",
            "panel.repair.title": "Plean deisiúcháin",
            "panel.optimize.title": "Optamaitheoir",
            "commands.loop.help": "Rith/seiceáil/deisigh lúb traenála an tionscadail",
            "commands.locale.help": "Féach ar nó socraigh teanga an CLI",
            "status.ready_to_deliver": "réidh_le_seachadadh",
            "status.blocked": "bacáilte",
            "status.failed": "theip",
            "status.continue": "leanúint",
            "status.deliver": "seachadadh",
            "status.iteration_budget_exhausted": "buiséad_athchleachta_imithe",
            "severity.info": "Eolas",
            "severity.low": "íseal",
            "severity.medium": "meánach",
            "severity.high": "ard",
            "severity.critical": "criticiúil",
        },
    ),
    (
        "af",
        "Afrikaans",
        "Afrikaans",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "Projek-opleiding looptyd",
            "panel.run.title": "lus-uitvoering",
            "panel.run.run_label": "Uitvoering",
            "panel.run.status_label": "Status",
            "panel.deliver.title": "Aflewering",
            "panel.status.title": "Lusstatus",
            "panel.review.title": "Resensie",
            "panel.repair.title": "Herstelplan",
            "panel.optimize.title": "Optimeerder",
            "commands.loop.help": "Voer uit/kyk/herstel die projek-opleidinglus",
            "commands.locale.help": "Vertoon of stel die CLI-taal",
            "status.ready_to_deliver": "gereed_om_lewer",
            "status.blocked": "geblokkeer",
            "status.failed": "misluk",
            "status.continue": "gaan_voort",
            "status.deliver": "lewer",
            "status.iteration_budget_exhausted": "iterasie_begroting_opgeput",
            "severity.info": "Info",
            "severity.low": "laag",
            "severity.medium": "medium",
            "severity.high": "hoog",
            "severity.critical": "kritiek",
        },
    ),
    (
        "zh-hant",
        "繁體中文",
        "Traditional Chinese",
        False,
        {
            "app.name": "LoopOS",
            "app.tagline": "專案訓練執行環境",
            "panel.run.title": "執行迴圈",
            "panel.run.run_label": "執行",
            "panel.run.status_label": "狀態",
            "panel.deliver.title": "交付",
            "panel.status.title": "迴圈狀態",
            "panel.review.title": "審查",
            "panel.repair.title": "修復計畫",
            "panel.optimize.title": "優化器",
            "commands.loop.help": "執行/檢查/修復專案訓練迴圈",
            "commands.locale.help": "檢視或設定 CLI 語言",
            "status.ready_to_deliver": "可交付",
            "status.blocked": "已封鎖",
            "status.failed": "失敗",
            "status.continue": "繼續",
            "status.deliver": "交付",
            "status.iteration_budget_exhausted": "反覆運算預算用盡",
            "severity.info": "資訊",
            "severity.low": "低",
            "severity.medium": "中",
            "severity.high": "高",
            "severity.critical": "嚴重",
        },
    ),
]


def _format_yaml_value(v: Any) -> str:
    """Format a Python value for YAML output."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        # Always quote strings with non-ASCII to be safe, and any
        # string that contains YAML metacharacters.
        if any(c in v for c in ":#{}[]&*?|>!%@`'\""):
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        if not v:
            return '""'
        return v
    return str(v)


def _emit_yaml(catalog: dict, indent: int = 0) -> str:
    """Render a (potentially nested) dict as YAML.

    Recurses for arbitrarily-deep nested dicts. Lists are
    rendered as ``- item`` blocks. Strings are quoted only when
    necessary.
    """
    pad = "  " * indent
    lines: list[str] = []
    for k, v in catalog.items():
        if isinstance(v, dict):
            if v:
                lines.append(f"{pad}{k}:")
                lines.append(_emit_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {{}}")
        elif isinstance(v, list):
            if v:
                lines.append(f"{pad}{k}:")
                for item in v:
                    lines.append(f"{pad}  - {_format_yaml_value(item)}")
            else:
                lines.append(f"{pad}{k}: []")
        else:
            lines.append(f"{pad}{k}: {_format_yaml_value(v)}")
    return "\n".join(lines) + "\n"


for loc_id, native_name, english_name, rtl, sample in LOCALES:
    out: dict = {
        "_meta": {
            "locale": loc_id,
            "name": native_name,
            "english_name": english_name,
            "rtl": rtl,
            "version": "0.4.0",
            "draft": True,
            "note": (
                f"Best-effort {english_name} draft generated by "
                "scripts/gen_i18n_yaml_stubs.py. Most keys fall through "
                "to English. Native-speaker review required before "
                "promoting to draft=false."
            ),
        },
        "app": {
            "name": "LoopOS",
            "tagline": sample.get("app.tagline", EN["app"]["tagline"]),
        },
        "panel": {},
        "status": {},
        "severity": {},
    }
    # Distribute the sample translations into the right sections.
    for k, v in sample.items():
        if k.startswith("app."):
            out["app"][k.split(".", 1)[1]] = v
        elif k.startswith("panel."):
            # panel.run.title, panel.deliver.title, etc.
            parts = k.split(".")
            section = out["panel"]
            for p in parts[1:-1]:
                section = section.setdefault(p, {})
            section[parts[-1]] = v
        elif k.startswith("status."):
            out["status"][k.split(".", 1)[1]] = v
        elif k.startswith("severity."):
            out["severity"][k.split(".", 1)[1]] = v
        else:
            out[k] = v

    out_path = I18N_DIR / f"{loc_id}.yaml"
    out_path.write_text(_emit_yaml(out), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")

print("done.")