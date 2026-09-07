# -*- coding: utf-8 -*-
"""gen-translations.py - builds the eleven ApocryphaLockInteractionOverhaul_<language>.txt files.

The English key list is extracted from the PATCHED source/UI.cpp, so it can never drift from the
code. Two shapes are read:

  * strings::TR("KEY", "English text") - the ordinary call;
  * a parallel `kFooKeys[] / kFooLabels[]` array pair - the Combo option lists and the lock-tier
    names, whose entries are looked up by index at draw time rather than by a literal TR call.

The other ten languages are this project's own translations of that list, held below as one dict
per key. Writes REPO/dist/Interface/Translations/ApocryphaLockInteractionOverhaul_<language>.txt
for english + the owner's ten languages: UTF-16LE with a BOM, one "$key<TAB>text" record per
line, a literal "\\n" for an embedded line break, CRLF records - the SKSE/SkyUI shape the
Apocrypha Menu Framework's Strings.cpp reads.

Untranslated on purpose, in every language: the mod's own spell name (Manipulate Lock - the ESL
record is English, so the page must match the spell book), file names (Lock Overhaul.esp,
RememberLockpickAngle.dll, ApocryphaLockInteractionOverhaul.esl / .log), the log path, INI keys
(sPerkPlugin, uPerkFormID), the game setting fSkillUsageLockPick, and the page name Unlock Spell
(page names are the framework's registry identity and stay English).

Run: `python tools/gen-translations.py`.
"""
import io
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM = "ApocryphaLockInteractionOverhaul"
LANGS = ["english", "japanese", "korean", "chinese", "russian",
         "german", "french", "spanish", "italian", "polish", "czech"]
OTHERS = LANGS[1:]

TR_RE = re.compile(r'strings::TR\(\s*"((?:[^"\\]|\\.)+)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')
KEYS_RE = re.compile(r'constexpr const char\* k(\w+)Keys\[\]\s*=\s*\{([^}]*)\};')
LABELS_RE = re.compile(r'constexpr const char\* k(\w+)Labels\[\]\s*=\s*\{([^}]*)\};')
LIT_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def unescape(s):
    return s.encode("latin-1", "backslashreplace").decode("unicode_escape") if "\\" in s else s


def read_keys():
    src = io.open(os.path.join(REPO, "source", "UI.cpp"), encoding="utf-8", newline="").read()
    order, texts = [], {}

    def add(key, text):
        if key in texts:
            if texts[key] != text:
                raise RuntimeError("key {!r} has two English texts: {!r} vs {!r}".format(key, texts[key], text))
            return
        order.append(key)
        texts[key] = text

    for m in TR_RE.finditer(src):
        add(unescape(m.group(1)), unescape(m.group(2)))

    labels = {m.group(1): m.group(2) for m in LABELS_RE.finditer(src)}
    for m in KEYS_RE.finditer(src):
        name = m.group(1)
        if name not in labels:
            raise RuntimeError("k{}Keys has no matching k{}Labels array".format(name, name))
        ks = [unescape(x) for x in LIT_RE.findall(m.group(2))]
        vs = [unescape(x) for x in LIT_RE.findall(labels[name])]
        if len(ks) != len(vs):
            raise RuntimeError("k{}Keys ({}) and k{}Labels ({}) length mismatch".format(name, len(ks), name, len(vs)))
        for k, v in zip(ks, vs):
            add(k, v)

    return order, texts


# ------------------------------------------------------------------------------------------------
# The project's own translations, one dict per key, in the order the page draws them.
# ------------------------------------------------------------------------------------------------
def T(ja, ko, zh, ru, de, fr, es, it, pl, cs):
    return {"japanese": ja, "korean": ko, "chinese": zh, "russian": ru, "german": de,
            "french": fr, "spanish": es, "italian": it, "polish": pl, "czech": cs}


TRANSLATIONS = {}
# --- shared words and the crosshair readout ---------------------------------------------------
TRANSLATIONS["ALIO_Yes"] = T("はい", "예", "是", "да", "ja", "oui", "sí", "sì", "tak", "ano")
TRANSLATIONS["ALIO_No"] = T("いいえ", "아니오", "否", "нет", "nein", "non", "no", "no", "nie", "ne")
TRANSLATIONS["ALIO_Tier_KeyRequired"] = T(
    "鍵が必要", "열쇠 필요", "需要钥匙", "нужен ключ", "Schlüssel nötig",
    "clé requise", "requiere llave", "richiede chiave", "wymaga klucza", "vyžaduje klíč")
TRANSLATIONS["ALIO_HelpMark"] = T("(?)", "(?)", "(?)", "(?)", "(?)", "(?)", "(?)", "(?)", "(?)", "(?)")
TRANSLATIONS["ALIO_TierHelp"] = T(
    "%s ― %s の錠に必要な値です（0～100）。",
    "%s ― %s 자물쇠에 필요한 수치, 0~100.",
    "%s ― %s 锁所需的数值，0 到 100。",
    "%s — требуется для замка уровня «%s», от 0 до 100.",
    "%s — nötig für ein %s-Schloss, 0 bis 100.",
    "%s — nécessaire pour une serrure %s, de 0 à 100.",
    "%s: necesario para una cerradura %s, de 0 a 100.",
    "%s: necessario per una serratura %s, da 0 a 100.",
    "%s — wymagane dla zamka %s, od 0 do 100.",
    "%s — potřebné pro zámek %s, 0 až 100.")
TRANSLATIONS["ALIO_LookAtNothing"] = T(
    "施錠された宝箱や扉を見ると、このMODがどう判定するかを表示します。",
    "잠긴 상자나 문을 바라보면 이 모드가 어떻게 판정하는지 표시됩니다.",
    "看向一个上锁的箱子或门，即可看到本模组如何判定它。",
    "Посмотрите на запертый сундук или дверь, чтобы увидеть, как этот мод её оценивает.",
    "Blicke auf eine verschlossene Truhe oder Tür, um zu sehen, wie diese Mod sie bewertet.",
    "Regardez un coffre ou une porte verrouillée pour voir comment ce mod l'évalue.",
    "Mira un cofre o una puerta cerrada con llave para ver cómo la evalúa este mod.",
    "Guarda una cassa o una porta chiusa a chiave per vedere come questa mod la valuta.",
    "Spójrz na zamknięty kufer lub drzwi, aby zobaczyć, jak ocenia je ta modyfikacja.",
    "Podívej se na zamčenou truhlu nebo dveře a uvidíš, jak je tento mod vyhodnotí.")
TRANSLATIONS["ALIO_LookNotLocked"] = T(
    "%s: 施錠されていません。", "%s: 잠겨 있지 않습니다.", "%s：未上锁。", "%s: не заперто.",
    "%s: nicht verschlossen.", "%s : non verrouillé.", "%s: no está cerrado.",
    "%s: non è chiuso a chiave.", "%s: nie jest zamknięte.", "%s: není zamčeno.")
TRANSLATIONS["ALIO_LookNeedsKey"] = T(
    "%s: 鍵が必要です ― このMODは手を出しません。",
    "%s: 열쇠가 필요합니다 ― 이 모드는 관여하지 않습니다.",
    "%s：需要钥匙 ― 本模组不会干预。",
    "%s: нужен ключ — этот мод его не трогает.",
    "%s: benötigt einen Schlüssel – diese Mod rührt es nicht an.",
    "%s : nécessite une clé – ce mod n'y touche pas.",
    "%s: necesita una llave; este mod no la toca.",
    "%s: richiede una chiave: questa mod non la tocca.",
    "%s: wymaga klucza – ta modyfikacja go nie rusza.",
    "%s: vyžaduje klíč – tento mod se ho nedotýká.")
TRANSLATIONS["ALIO_LookLock"] = T(
    "%s: %s の錠%s%s", "%s: %s 자물쇠%s%s", "%s：%s 锁%s%s", "%s: %s замок%s%s",
    "%s: %s-Schloss%s%s", "%s : serrure %s%s%s", "%s: cerradura %s%s%s",
    "%s: serratura %s%s%s", "%s: zamek %s%s%s", "%s: %s zámek%s%s")
TRANSLATIONS["ALIO_LookFrozen"] = T(
    "、凍結中", ", 얼어붙음", "，已冻结", ", заморожен", ", vereist",
    ", gelée", ", congelada", ", congelata", ", zamrożony", ", zmrzlý")
TRANSLATIONS["ALIO_LookCrime"] = T(
    "、開けると犯罪", ", 여는 것은 범죄", "，开锁属于犯罪", ", вскрытие — преступление",
    ", das Öffnen ist ein Verbrechen", ", l'ouvrir est un crime", ", abrirla es un delito",
    ", aprirla è un crimine", ", otwarcie to przestępstwo", ", otevřít ho je zločin")
TRANSLATIONS["ALIO_LookPick"] = T(
    "開錠: %s（開錠 %u、必要 %u）",
    "따기: %s (자물쇠 따기 %u, 필요 %u)",
    "撬锁：%s（开锁 %u，需要 %u）",
    "Взлом: %s (Взлом %u, нужно %u)",
    "Knacken: %s (Schlösserknacken %u, nötig %u)",
    "Crochetage : %s (Crochetage %u, requis %u)",
    "Ganzúa: %s (Allanamiento %u, necesita %u)",
    "Scasso: %s (Scasso %u, richiesto %u)",
    "Otwieranie: %s (Otwieranie zamków %u, wymagane %u)",
    "Páčení: %s (Páčení zámků %u, potřeba %u)")
TRANSLATIONS["ALIO_LookSmash"] = T(
    "破壊: 片手 %s（%u / %u）、両手 %s（%u / %u）",
    "부수기: 한손 %s (%u / %u), 양손 %s (%u / %u)",
    "砸锁：单手 %s（%u / %u），双手 %s（%u / %u）",
    "Взлом силой: одноручное %s (%u из %u), двуручное %s (%u из %u)",
    "Aufbrechen: Einhändig %s (%u von %u), Zweihändig %s (%u von %u)",
    "Fracture : une main %s (%u sur %u), deux mains %s (%u sur %u)",
    "Romper: una mano %s (%u de %u), dos manos %s (%u de %u)",
    "Sfondare: una mano %s (%u su %u), due mani %s (%u su %u)",
    "Rozbicie: jednoręczna %s (%u z %u), dwuręczna %s (%u z %u)",
    "Rozbití: jednoruční %s (%u z %u), obouruční %s (%u z %u)")
TRANSLATIONS["ALIO_LookMagic"] = T(
    "魔法: 変化 %s（%u / %u）、破壊 %s（%u / %u）",
    "마법: 변화 %s (%u / %u), 파괴 %s (%u / %u)",
    "魔法：变化系 %s（%u / %u），毁灭系 %s（%u / %u）",
    "Магия: Изменение %s (%u из %u), Разрушение %s (%u из %u)",
    "Magie: Veränderung %s (%u von %u), Zerstörung %s (%u von %u)",
    "Magie : Altération %s (%u sur %u), Destruction %s (%u sur %u)",
    "Magia: Alteración %s (%u de %u), Destrucción %s (%u de %u)",
    "Magia: Alterazione %s (%u su %u), Distruzione %s (%u su %u)",
    "Magia: Zmiana %s (%u z %u), Zniszczenie %s (%u z %u)",
    "Magie: Proměny %s (%u z %u), Ničení %s (%u z %u)")
TRANSLATIONS["ALIO_StandDown"] = T(
    "Lock Overhaul.esp が読み込まれているため、このMODは完全に停止しています。そのMODを外すまで、これらのページの設定は何も機能しません。",
    "Lock Overhaul.esp가 로드되어 있어 이 모드는 완전히 물러납니다. 해당 모드를 제거하기 전까지 이 페이지의 설정은 아무 효과도 없습니다.",
    "已加载 Lock Overhaul.esp，因此本模组完全停用。在移除该模组之前，这些页面上的设置都不会生效。",
    "Загружен Lock Overhaul.esp, поэтому этот мод полностью отключается: ничто на этих страницах не действует, пока тот мод не будет удалён.",
    "Lock Overhaul.esp ist geladen, daher tritt diese Mod vollständig zurück – nichts auf diesen Seiten hat eine Wirkung, solange jene Mod installiert ist.",
    "Lock Overhaul.esp est chargé, ce mod se met donc complètement en retrait : rien sur ces pages n'a d'effet tant que l'autre mod n'est pas retiré.",
    "Lock Overhaul.esp está cargado, así que este mod se aparta por completo: nada de estas páginas hace nada hasta que se retire ese mod.",
    "Lock Overhaul.esp è caricato, quindi questa mod si ritira completamente: nulla in queste pagine ha effetto finché quella mod non viene rimossa.",
    "Wczytano Lock Overhaul.esp, więc ta modyfikacja całkowicie się wycofuje – nic na tych stronach nie działa, dopóki tamta modyfikacja nie zostanie usunięta.",
    "Je načten Lock Overhaul.esp, takže tento mod zcela ustupuje – dokud onen mod neodstraníš, nic na těchto stránkách nic nedělá.")
# --- the Save / Reload / Restore row, shared by every page -------------------------------------
TRANSLATIONS["ALIO_SaveBtn"] = T("保存", "저장", "保存", "Сохранить", "Speichern",
                                 "Enregistrer", "Guardar", "Salva", "Zapisz", "Uložit")
TRANSLATIONS["ALIO_StatusSaving"] = T("保存中...", "저장 중...", "正在保存...", "Сохранение...",
                                      "Speichern...", "Enregistrement...", "Guardando...",
                                      "Salvataggio...", "Zapisywanie...", "Ukládání...")
TRANSLATIONS["ALIO_StatusSaved"] = T(
    "設定を保存しました。", "설정을 저장했습니다.", "设置已保存。", "Настройки сохранены.",
    "Einstellungen gespeichert.", "Paramètres enregistrés.", "Ajustes guardados.",
    "Impostazioni salvate.", "Ustawienia zapisane.", "Nastavení uloženo.")
TRANSLATIONS["ALIO_StatusSaveFail"] = T(
    "INIファイルを書き込めませんでした。理由はログを参照してください。",
    "INI 파일을 쓸 수 없습니다. 이유는 로그를 확인하세요.",
    "无法写入 INI 文件。原因请查看日志。",
    "Не удалось записать INI. Причина — в журнале.",
    "Die INI konnte nicht geschrieben werden. Der Grund steht im Log.",
    "Impossible d'écrire le fichier INI. Voyez le journal pour la raison.",
    "No se pudo escribir el INI. Consulta el registro para saber por qué.",
    "Impossibile scrivere il file INI. Il motivo è nel log.",
    "Nie udało się zapisać pliku INI. Powód znajdziesz w dzienniku.",
    "Soubor INI se nepodařilo zapsat. Důvod najdeš v logu.")
TRANSLATIONS["ALIO_HelpSave"] = T(
    "すべてのセクションの設定をプラグインのINIに書き込み、再起動後も残るようにします。",
    "모든 섹션의 설정을 플러그인 INI에 기록하여 재시작 후에도 유지되게 합니다.",
    "将所有分区的设置写入插件的 INI 文件，使其在重启后依然保留。",
    "Записывает все настройки всех разделов в INI плагина, чтобы они пережили перезапуск.",
    "Schreibt jede Einstellung aller Abschnitte in die INI des Plugins, damit sie einen Neustart übersteht.",
    "Écrit tous les réglages de toutes les sections dans l'INI du plugin, pour qu'ils survivent à un redémarrage.",
    "Escribe todos los ajustes de todas las secciones en el INI del plugin para que sobrevivan a un reinicio.",
    "Scrive tutte le impostazioni di ogni sezione nell'INI del plugin, così sopravvivono a un riavvio.",
    "Zapisuje wszystkie ustawienia ze wszystkich sekcji do pliku INI wtyczki, aby przetrwały ponowne uruchomienie.",
    "Zapíše všechna nastavení ze všech sekcí do INI zásuvného modulu, aby přežila restart.")
TRANSLATIONS["ALIO_ReloadBtn"] = T(
    "INIから再読み込み", "INI에서 다시 불러오기", "从 INI 重新加载", "Перечитать INI",
    "Aus INI neu laden", "Recharger depuis l'INI", "Recargar desde el INI",
    "Ricarica dall'INI", "Wczytaj ponownie z INI", "Načíst znovu z INI")
TRANSLATIONS["ALIO_StatusReloading"] = T(
    "再読み込み中...", "다시 불러오는 중...", "正在重新加载...", "Перезагрузка...",
    "Neu laden...", "Rechargement...", "Recargando...", "Ricaricamento...",
    "Wczytywanie...", "Načítání...")
TRANSLATIONS["ALIO_StatusReloaded"] = T(
    "INIから設定を再読み込みしました。", "INI에서 설정을 다시 불러왔습니다.",
    "已从 INI 重新加载设置。", "Настройки перечитаны из INI.",
    "Einstellungen aus der INI neu geladen.", "Paramètres rechargés depuis l'INI.",
    "Ajustes recargados desde el INI.", "Impostazioni ricaricate dall'INI.",
    "Ustawienia wczytane ponownie z pliku INI.", "Nastavení bylo znovu načteno z INI.")
TRANSLATIONS["ALIO_StatusReloadFail"] = T(
    "INIファイルを読み込めませんでした。理由はログを参照してください。",
    "INI 파일을 읽을 수 없습니다. 이유는 로그를 확인하세요.",
    "无法读取 INI 文件。原因请查看日志。",
    "Не удалось прочитать INI. Причина — в журнале.",
    "Die INI konnte nicht gelesen werden. Der Grund steht im Log.",
    "Impossible de lire le fichier INI. Voyez le journal pour la raison.",
    "No se pudo leer el INI. Consulta el registro para saber por qué.",
    "Impossibile leggere il file INI. Il motivo è nel log.",
    "Nie udało się odczytać pliku INI. Powód znajdziesz w dzienniku.",
    "Soubor INI se nepodařilo přečíst. Důvod najdeš v logu.")
TRANSLATIONS["ALIO_HelpReload"] = T(
    "前回の保存以降にここで行った変更を破棄し、ディスクからINIを読み直します。",
    "마지막 저장 이후 여기서 변경한 내용을 버리고 디스크에서 INI를 다시 읽습니다.",
    "丢弃自上次保存以来在此处所做的更改，并从磁盘重新读取 INI。",
    "Отбрасывает изменения, сделанные здесь после последнего сохранения, и перечитывает INI с диска.",
    "Verwirft alle seit dem letzten Speichern hier gemachten Änderungen und liest die INI erneut von der Festplatte.",
    "Annule toutes les modifications faites ici depuis la dernière sauvegarde et relit l'INI depuis le disque.",
    "Descarta todos los cambios hechos aquí desde el último guardado y vuelve a leer el INI del disco.",
    "Scarta ogni modifica fatta qui dall'ultimo salvataggio e rilegge l'INI dal disco.",
    "Odrzuca wszystkie zmiany wprowadzone tutaj od ostatniego zapisu i ponownie odczytuje plik INI z dysku.",
    "Zahodí všechny změny provedené zde od posledního uložení a znovu načte INI z disku.")
TRANSLATIONS["ALIO_RestoreBtn"] = T(
    "初期設定に戻す", "기본값 복원", "恢复默认值", "Сбросить настройки",
    "Standardwerte wiederherstellen", "Restaurer les valeurs par défaut",
    "Restaurar valores predeterminados", "Ripristina i valori predefiniti",
    "Przywróć domyślne", "Obnovit výchozí")
TRANSLATIONS["ALIO_StatusRestored"] = T(
    "初期設定に戻しました（すべてオフ）。保存を押すと確定します。",
    "기본값으로 복원했습니다(모두 꺼짐). 저장을 눌러야 유지됩니다.",
    "已恢复默认值（全部关闭）。按“保存”以保留。",
    "Настройки сброшены (всё выключено). Нажмите «Сохранить», чтобы оставить их.",
    "Standardwerte wiederhergestellt (alles aus). Zum Behalten auf Speichern drücken.",
    "Valeurs par défaut restaurées (tout est désactivé). Appuyez sur Enregistrer pour les conserver.",
    "Valores predeterminados restaurados (todo desactivado). Pulsa Guardar para conservarlos.",
    "Valori predefiniti ripristinati (tutto disattivato). Premi Salva per mantenerli.",
    "Przywrócono wartości domyślne (wszystko wyłączone). Naciśnij Zapisz, aby je zachować.",
    "Výchozí hodnoty obnoveny (vše vypnuto). Stiskni Uložit, aby zůstaly.")
TRANSLATIONS["ALIO_HelpRestore"] = T(
    "すべての設定を新規インストール時の値（全機能オフ）に戻します。保存を押すまで何も書き込まれません。",
    "모든 설정을 새로 설치했을 때의 값(모든 기능 꺼짐)으로 되돌립니다. 저장을 누르기 전에는 아무것도 기록되지 않습니다.",
    "将所有设置恢复为全新安装时的值 ― 所有功能均关闭。在按下“保存”之前不会写入任何内容。",
    "Возвращает каждую настройку к значению при свежей установке — все возможности выключены. Ничего не записывается, пока вы не нажмёте «Сохранить».",
    "Setzt jede Einstellung auf den Wert einer frischen Installation zurück – alle Funktionen aus. Es wird nichts geschrieben, bis du auf Speichern drückst.",
    "Remet chaque réglage à sa valeur d'installation initiale – toutes les fonctions désactivées. Rien n'est écrit tant que vous n'appuyez pas sur Enregistrer.",
    "Devuelve cada ajuste a su valor de instalación inicial: todas las funciones desactivadas. No se escribe nada hasta que pulses Guardar.",
    "Riporta ogni impostazione al valore di installazione iniziale: tutte le funzioni disattivate. Non viene scritto nulla finché non premi Salva.",
    "Przywraca każde ustawienie do wartości po świeżej instalacji – wszystkie funkcje wyłączone. Nic nie zostanie zapisane, dopóki nie naciśniesz Zapisz.",
    "Vrátí každé nastavení na hodnotu po čerstvé instalaci – všechny funkce vypnuty. Dokud nestiskneš Uložit, nic se nezapíše.")
# --- Requirements page --------------------------------------------------------------------------
TRANSLATIONS["ALIO_ReqIntro"] = T(
    "錠の等級に応じた開錠スキルがないと、開錠画面は開きません。足りない場合は画面がすぐ閉じ、ロックピックも失われません。鍵が必要な錠には一切干渉しません。",
    "자물쇠 등급에 맞는 자물쇠 따기 실력이 있어야 따기 화면이 열립니다. 부족하면 화면이 다시 닫히고 자물쇠 따개도 잃지 않습니다. 열쇠가 필요한 자물쇠는 건드리지 않습니다.",
    "只有开锁技能达到该锁等级的要求，撬锁界面才会打开；不足时界面会立即关闭，也不会损失撬锁器。需要钥匙的锁绝不受影响。",
    "Чтобы открылось окно взлома, навык Взлома должен соответствовать уровню замка; при недостатке окно сразу закрывается и отмычка не теряется. Замки, требующие ключ, не затрагиваются.",
    "Ein Schloss verlangt für seine Stufe ein entsprechendes Schlösserknacken, bevor sich das Knackfenster öffnet; darunter schließt es sich wieder und es geht kein Dietrich verloren. Schlösser, die einen Schlüssel verlangen, werden nie angerührt.",
    "Une serrure exige un niveau de Crochetage correspondant à sa difficulté avant que l'écran de crochetage ne s'ouvre ; en dessous, l'écran se referme et aucun crochet n'est perdu. Les serrures nécessitant une clé ne sont jamais touchées.",
    "Una cerradura exige un nivel de Allanamiento acorde a su dificultad antes de que se abra la pantalla de ganzúa; por debajo, la pantalla se cierra de nuevo y no se pierde ninguna ganzúa. Las cerraduras que requieren llave nunca se tocan.",
    "Una serratura richiede un livello di Scasso adeguato al suo grado prima che si apra la schermata di scasso; sotto quel valore la schermata si richiude e non si perde alcun grimaldello. Le serrature che richiedono una chiave non vengono mai toccate.",
    "Zamek wymaga poziomu Otwierania zamków odpowiedniego dla swojej klasy, zanim otworzy się okno otwierania; poniżej okno zamyka się z powrotem i nie tracisz wytrycha. Zamki wymagające klucza nigdy nie są ruszane.",
    "Zámek vyžaduje pro svou úroveň odpovídající Páčení zámků, než se otevře okno páčení; pod touto hodnotou se okno zase zavře a nepřijdeš o paklíč. Zámků vyžadujících klíč se mod nikdy nedotkne.")
TRANSLATIONS["ALIO_ReqHeader"] = T(
    "錠の要求値", "자물쇠 요구 조건", "锁的要求", "Требования замков", "Schlossanforderungen",
    "Exigences des serrures", "Requisitos de las cerraduras", "Requisiti delle serrature",
    "Wymagania zamków", "Požadavky zámků")
TRANSLATIONS["ALIO_ReqEnabled"] = T(
    "錠の等級ごとに開錠スキルを要求する",
    "자물쇠 등급별로 자물쇠 따기 실력 요구",
    "按锁的等级要求相应的开锁技能",
    "Требовать навык Взлома по уровню замка",
    "Schlösserknacken je nach Schlossstufe verlangen",
    "Exiger un niveau de Crochetage selon la difficulté de la serrure",
    "Exigir Allanamiento según el nivel de la cerradura",
    "Richiedi Scasso in base al grado della serratura",
    "Wymagaj Otwierania zamków zależnie od klasy zamka",
    "Vyžadovat Páčení zámků podle úrovně zámku")
TRANSLATIONS["ALIO_HelpReqEnabled"] = T(
    "オン: 下の表が開錠画面の可否を決めます。オフ: バニラ同様、どの錠でも試せます。",
    "켜기: 아래 표가 따기 화면을 통제합니다. 끄기: 바닐라처럼 어떤 자물쇠든 시도할 수 있습니다.",
    "开启：由下表决定能否打开撬锁界面。关闭：与原版一样，任何锁都可以尝试。",
    "Вкл.: таблица ниже управляет доступом к окну взлома. Выкл.: любой замок можно попробовать, как в оригинале.",
    "An: Die Tabelle unten steuert das Knackfenster. Aus: Jedes Schloss kann versucht werden, wie im Original.",
    "Activé : le tableau ci-dessous conditionne l'écran de crochetage. Désactivé : toute serrure peut être tentée, comme dans le jeu de base.",
    "Activado: la tabla de abajo controla la pantalla de ganzúa. Desactivado: se puede intentar cualquier cerradura, como en el juego base.",
    "Attivo: la tabella qui sotto regola la schermata di scasso. Disattivo: si può tentare qualsiasi serratura, come nel gioco base.",
    "Wł.: poniższa tabela decyduje o oknie otwierania. Wył.: każdy zamek można spróbować otworzyć, jak w podstawowej grze.",
    "Zapnuto: tabulka níže řídí okno páčení. Vypnuto: lze zkusit jakýkoli zámek, jako v základní hře.")
TRANSLATIONS["ALIO_SkillLockpicking"] = T(
    "開錠", "자물쇠 따기", "开锁", "Взлом", "Schlösserknacken",
    "Crochetage", "Allanamiento", "Scasso", "Otwieranie zamków", "Páčení zámků")
TRANSLATIONS["ALIO_AutoPickHeader"] = T(
    "自動開錠", "자동 따기", "自动开锁", "Автовзлом", "Automatisch knacken",
    "Crochetage automatique", "Ganzúa automática", "Scasso automatico",
    "Automatyczne otwieranie", "Automatické páčení")
TRANSLATIONS["ALIO_AutoPick"] = T(
    "ミニゲームなしで錠を開ける", "미니게임 없이 자물쇠 열기", "无需小游戏直接开锁",
    "Открывать замки без мини-игры", "Schlösser ohne Minispiel öffnen",
    "Ouvrir les serrures sans le mini-jeu", "Abrir cerraduras sin el minijuego",
    "Apri le serrature senza il minigioco", "Otwieraj zamki bez minigry",
    "Otevírat zámky bez minihry")
TRANSLATIONS["ALIO_HelpAutoPick"] = T(
    "開錠スキルが上の表を満たしていれば、錠はそのまま開きます。ロックピックを1本消費し（「折れずの技」があれば消費しません）、開錠スキルはゲーム本来の開錠と同じだけ上昇します。所有者のいる錠を開けるのは、「早業」がない限り犯罪です。",
    "자물쇠 따기 실력이 위 표를 충족하면 자물쇠가 그대로 열립니다. 자물쇠 따개를 하나 소모하고(불굴 특전이 있으면 소모하지 않음), 자물쇠 따기 실력은 게임 본래의 따기와 같은 만큼 오릅니다. 주인이 있는 자물쇠를 여는 것은 재빠른 손놀림 특전이 없으면 범죄입니다.",
    "开锁技能达到上表要求时，锁会直接打开：消耗一个撬锁器（拥有“坚不可摧”特技时不消耗），开锁技能按游戏原本撬锁的幅度提升；若无“快手”特技，开启他人所有的锁属于犯罪。",
    "Если навык Взлома соответствует таблице выше, замок просто открывается: тратится одна отмычка (ни одной со способностью «Несгибаемый»), Взлом растёт так же, как при обычном взломе, а вскрытие чужого замка — преступление, если у вас нет способности «Ловкие руки».",
    "Reicht das Schlösserknacken (Tabelle oben), öffnet sich das Schloss einfach: ein Dietrich wird verbraucht (keiner mit dem Vorteil „Unzerbrechlich“), Schlösserknacken steigt so wie beim normalen Knacken, und das Öffnen eines fremden Schlosses ist ein Verbrechen, sofern du nicht „Schnelle Hände“ besitzt.",
    "Si le Crochetage suffit (tableau ci-dessus), la serrure s'ouvre simplement : un crochet est consommé (aucun avec l'atout « Incassable »), le Crochetage progresse comme lors d'un crochetage normal, et ouvrir une serrure appartenant à autrui est un crime à moins de posséder « Mains agiles ».",
    "Con suficiente Allanamiento (la tabla de arriba) la cerradura se abre sin más: se gasta una ganzúa (ninguna con la habilidad «Irrompible»), Allanamiento sube igual que con el forzado normal del juego y abrir una cerradura ajena es un delito salvo que tengas «Manos rápidas».",
    "Con Scasso sufficiente (la tabella qui sopra) la serratura si apre e basta: si consuma un grimaldello (nessuno con il talento «Infrangibile»), lo Scasso sale come con lo scasso normale del gioco e aprire una serratura altrui è un crimine se non possiedi «Mani veloci».",
    "Przy wystarczającym Otwieraniu zamków (tabela powyżej) zamek po prostu się otwiera: zużywa się jeden wytrych (żaden przy atucie „Niezniszczalny”), Otwieranie zamków rośnie tak samo jak przy zwykłym otwieraniu, a otwarcie cudzego zamka jest przestępstwem, chyba że masz „Zwinne dłonie”.",
    "Při dostatečném Páčení zámků (tabulka výše) se zámek prostě otevře: spotřebuje se jeden paklíč (žádný se schopností „Nezlomný“), Páčení zámků roste stejně jako při běžném páčení a otevřít cizí zámek je zločin, pokud nemáš „Rychlé ruce“.")
TRANSLATIONS["ALIO_OpenAfterPick"] = T(
    "開錠後すぐに宝箱や扉を開く", "딴 뒤 곧바로 상자나 문을 열기", "开锁后立即打开箱子或门",
    "Сразу открывать сундук или дверь", "Truhe oder Tür sofort öffnen",
    "Ouvrir aussitôt le coffre ou la porte", "Abrir el cofre o la puerta de inmediato",
    "Apri subito la cassa o la porta", "Otwórz kufer lub drzwi od razu",
    "Truhlu nebo dveře rovnou otevřít")
TRANSLATIONS["ALIO_HelpOpenAfterPick"] = T(
    "自動開錠のあとにオブジェクトを起動し、もう一度押さなくてもすぐ開くようにします。",
    "자동으로 딴 뒤 대상을 곧바로 작동시켜, 한 번 더 누르지 않아도 바로 열립니다.",
    "自动开锁后会立即激活该物体，无需再按一次即可打开。",
    "После автовзлома объект активируется, поэтому открывается сразу, без второго нажатия.",
    "Nach dem automatischen Knacken wird das Objekt aktiviert, sodass es sofort aufgeht und kein zweiter Tastendruck nötig ist.",
    "Après le crochetage automatique, l'objet est activé et s'ouvre aussitôt, sans second appui.",
    "Tras la ganzúa automática, el objeto se activa y se abre al instante, sin necesidad de pulsar otra vez.",
    "Dopo lo scasso automatico l'oggetto viene attivato e si apre subito, senza una seconda pressione.",
    "Po automatycznym otwarciu obiekt zostaje aktywowany, więc otwiera się od razu, bez drugiego naciśnięcia.",
    "Po automatickém vypáčení se objekt aktivuje, takže se otevře hned a není třeba druhé stisknutí.")
TRANSLATIONS["ALIO_ReqReadoutHeader"] = T(
    "現在の判定", "지금 이 상황에서는", "当前的判定结果", "Что это значит прямо сейчас",
    "Was das gerade bedeutet", "Ce que cela donne actuellement",
    "Qué significa esto ahora mismo", "Cosa significa in questo momento",
    "Co to oznacza w tej chwili", "Co to znamená právě teď")
# --- Smash Locks page ----------------------------------------------------------------------------
TRANSLATIONS["ALIO_SmashIntro"] = T(
    "施錠された宝箱や扉を武器で殴ります。錠の等級に見合う武器スキルがあれば壊れて開き、使った武器スキルが上昇します。所有者のいる錠なら通報されます。",
    "잠긴 상자나 문을 무기로 내리칩니다. 자물쇠 등급에 맞는 무기 실력이 있으면 부서져 열리고, 사용한 실력이 오릅니다. 주인이 있는 자물쇠라면 신고당합니다.",
    "用武器击打上锁的箱子或门。若武器技能达到该锁等级的要求，就会被砸开；所用的技能随之提升，而砸开他人的锁会被举报。",
    "Ударьте по запертому сундуку или двери оружием. Если навык владения оружием соответствует уровню замка, он ломается; использованный навык растёт, а за чужой замок на вас донесут.",
    "Schlage mit einer Waffe auf eine verschlossene Truhe oder Tür. Reicht der Waffenskill für die Schlossstufe, bricht es auf; der benutzte Skill steigt, und bei einem fremden Schloss wirst du angezeigt.",
    "Frappez un coffre ou une porte verrouillée avec une arme. Si votre compétence d'arme suffit pour la difficulté de la serrure, elle cède ; la compétence utilisée progresse, et une serrure appartenant à autrui vous fait dénoncer.",
    "Golpea con un arma un cofre o una puerta cerrada. Si tu habilidad de arma basta para el nivel de la cerradura, se rompe; la habilidad usada sube y una cerradura ajena hace que te denuncien.",
    "Colpisci con un'arma una cassa o una porta chiusa a chiave. Se l'abilità dell'arma è sufficiente per il grado della serratura, si sfonda; l'abilità usata sale e una serratura altrui ti fa denunciare.",
    "Uderz w zamknięty kufer lub drzwi bronią. Jeśli umiejętność broni wystarcza dla klasy zamka, zamek pęka; użyta umiejętność rośnie, a cudzy zamek sprawia, że zostajesz zgłoszony.",
    "Udeř do zamčené truhly nebo dveří zbraní. Pokud dovednost se zbraní stačí na úroveň zámku, zámek povolí; použitá dovednost roste a u cizího zámku tě nahlásí.")
TRANSLATIONS["ALIO_SmashEnabled"] = T(
    "武器で錠を破壊する", "무기로 자물쇠 부수기", "用武器砸开锁", "Ломать замки оружием",
    "Schlösser mit einer Waffe aufbrechen", "Fracturer les serrures avec une arme",
    "Romper cerraduras con un arma", "Sfonda le serrature con un'arma",
    "Rozbijaj zamki bronią", "Rozbíjet zámky zbraní")
TRANSLATIONS["ALIO_HelpSmashEnabled"] = T(
    "オン: 施錠されたオブジェクトへの武器攻撃を下の表で判定します。",
    "켜기: 잠긴 대상에 대한 무기 공격을 아래 표로 판정합니다.",
    "开启：对上锁物体的武器攻击将按下表判定。",
    "Вкл.: удар оружием по запертому объекту оценивается по таблице ниже.",
    "An: Ein Waffentreffer auf ein verschlossenes Objekt wird an der Tabelle unten gemessen.",
    "Activé : un coup d'arme sur un objet verrouillé est évalué d'après le tableau ci-dessous.",
    "Activado: un golpe de arma sobre un objeto cerrado se juzga con la tabla de abajo.",
    "Attivo: un colpo d'arma su un oggetto chiuso viene valutato con la tabella qui sotto.",
    "Wł.: uderzenie bronią w zamknięty obiekt jest oceniane według poniższej tabeli.",
    "Zapnuto: zásah zbraní do zamčeného objektu se posuzuje podle tabulky níže.")
TRANSLATIONS["ALIO_AllowedWeapons"] = T(
    "使用できる武器", "허용 무기", "允许的武器", "Допустимое оружие", "Erlaubte Waffen",
    "Armes autorisées", "Armas permitidas", "Armi consentite", "Dozwolone bronie",
    "Povolené zbraně")
TRANSLATIONS["ALIO_HelpAllowedWeapons"] = T(
    "どの武器を対象にするか。両手武器は常に対象で、片手武器やその他はこの設定次第です。弓とクロスボウは弓術、杖は破壊、素手は片手として扱われます。",
    "어떤 무기를 인정할지 정합니다. 양손 무기는 항상 해당되며, 한손 무기와 그 밖의 무기는 이 설정에 따릅니다. 활과 석궁은 궁술, 지팡이는 파괴, 맨주먹은 한손으로 취급합니다.",
    "哪些武器有效。双手武器始终有效；单手武器及其他武器则取决于此设置。弓与弩使用射箭，法杖使用毁灭系，拳头按单手武器计算。",
    "Какое оружие учитывается. Двуручное — всегда; одноручное и всё прочее зависит от этой настройки. Луки и арбалеты используют Стрельбу, посохи — Разрушение, кулаки считаются одноручным оружием.",
    "Welche Waffen zählen. Zweihändige immer; einhändige und alles Übrige hängen von dieser Einstellung ab. Bögen und Armbrüste nutzen Bogenschießen, Stäbe Zerstörung, Fäuste gelten als einhändig.",
    "Quelles armes comptent. Les armes à deux mains toujours ; les armes à une main et le reste dépendent de ce réglage. Arcs et arbalètes utilisent l'Archerie, les bâtons la Destruction, les poings comptent comme une main.",
    "Qué armas cuentan. Las de dos manos siempre; las de una mano y todo lo demás dependen de este ajuste. Arcos y ballestas usan Arquería, los bastones usan Destrucción y los puños cuentan como una mano.",
    "Quali armi contano. Quelle a due mani sempre; quelle a una mano e tutto il resto dipendono da questa impostazione. Archi e balestre usano Tiro con l'arco, i bastoni la Distruzione, i pugni contano come una mano.",
    "Które bronie się liczą. Dwuręczne zawsze; jednoręczne i cała reszta zależą od tego ustawienia. Łuki i kusze korzystają z Łucznictwa, kostury ze Zniszczenia, a pięści liczą się jak broń jednoręczna.",
    "Které zbraně se počítají. Obouruční vždy; jednoruční a vše ostatní záleží na tomto nastavení. Luky a kuše používají Lukostřelbu, hole Ničení, pěsti se počítají jako jednoruční.")
TRANSLATIONS["ALIO_SkillWeapon"] = T(
    "武器スキル（片手または両手）", "무기 실력(한손 또는 양손)", "武器技能（单手或双手）",
    "Навык оружия (одноручное или двуручное)", "Waffenfertigkeit (Einhändig oder Zweihändig)",
    "Compétence d'arme (Une main ou Deux mains)", "Habilidad de arma (Una mano o Dos manos)",
    "Abilità con l'arma (Una mano o Due mani)", "Umiejętność broni (jednoręczna lub dwuręczna)",
    "Dovednost se zbraní (jednoruční nebo obouruční)")
TRANSLATIONS["ALIO_SmashFrostNote"] = T(
    "凍結した錠（Unlock Spell を参照）は、破壊に必要なスキルが %u 下がります。",
    "얼어붙은 자물쇠(Unlock Spell 참조)는 부수는 데 필요한 실력이 %u 낮아집니다.",
    "被冻结的锁（见 Unlock Spell 页）砸开时所需技能降低 %u。",
    "Замёрзшему замку (см. Unlock Spell) для взлома силой нужно на %u меньше навыка.",
    "Ein vereistes Schloss (siehe Unlock Spell) braucht %u weniger Fertigkeit zum Aufbrechen.",
    "Une serrure gelée (voir Unlock Spell) demande %u de compétence en moins pour être fracturée.",
    "Una cerradura congelada (ver Unlock Spell) necesita %u menos de habilidad para romperse.",
    "Una serratura congelata (vedi Unlock Spell) richiede %u di abilità in meno per essere sfondata.",
    "Zamrożony zamek (patrz Unlock Spell) wymaga o %u mniej umiejętności do rozbicia.",
    "Zmrzlý zámek (viz Unlock Spell) vyžaduje k rozbití o %u méně dovednosti.")
TRANSLATIONS["ALIO_Weapons_TwoOnly"] = T(
    "両手武器のみ", "양손 무기만", "仅双手武器", "Только двуручное оружие",
    "Nur zweihändige Waffen", "Armes à deux mains uniquement", "Solo armas a dos manos",
    "Solo armi a due mani", "Tylko broń dwuręczna", "Jen obouruční zbraně")
TRANSLATIONS["ALIO_Weapons_OneAndTwo"] = T(
    "片手・両手武器", "한손 및 양손 무기", "单手与双手武器",
    "Одноручное и двуручное оружие", "Ein- und zweihändige Waffen",
    "Armes à une et deux mains", "Armas a una y dos manos", "Armi a una e due mani",
    "Broń jednoręczna i dwuręczna", "Jednoruční i obouruční zbraně")
TRANSLATIONS["ALIO_Weapons_Any"] = T(
    "あらゆる武器（弓、クロスボウ、杖、素手も含む）",
    "모든 무기(활, 석궁, 지팡이, 맨주먹 포함)",
    "任何武器（包括弓、弩、法杖与拳头）",
    "Любое оружие (луки, арбалеты, посохи и кулаки тоже)",
    "Jede Waffe (auch Bögen, Armbrüste, Stäbe und Fäuste)",
    "Toute arme (arcs, arbalètes, bâtons et poings compris)",
    "Cualquier arma (también arcos, ballestas, bastones y puños)",
    "Qualsiasi arma (anche archi, balestre, bastoni e pugni)",
    "Dowolna broń (także łuki, kusze, kostury i pięści)",
    "Jakákoli zbraň (i luky, kuše, hole a pěsti)")
# --- Unlock Spell page ---------------------------------------------------------------------------
TRANSLATIONS["ALIO_SpellIntro"] = T(
    "Manipulate Lock は、離れた場所から錠の機構を操作する変化の呪文です。錠に向けて唱え、錠の等級に見合う変化があれば開きます。破壊も加わります: フロストは錠を凍らせ（破壊しやすくなり）、ファイアは氷を溶かすか錠そのものを開け、許可されていればショックでも開きます。",
    "Manipulate Lock은 멀리서 자물쇠의 기구를 조작하는 변화 계열 주문입니다. 자물쇠에 시전해 등급에 맞는 변화 실력이 있으면 열립니다. 파괴도 함께 쓸 수 있습니다: 냉기는 자물쇠를 얼리고(부수기 쉬워집니다), 화염은 얼음을 녹이거나 자물쇠를 바로 열며, 허용되면 전격도 자물쇠를 엽니다.",
    "Manipulate Lock 是一种远距离操作锁芯的变化系法术。对锁施放，若变化系达到该锁等级的要求即可打开。毁灭系也能参与：冰霜会冻结锁（更容易砸开），火焰会解冻或直接打开锁，若允许，电击同样能开锁。",
    "Manipulate Lock — заклинание школы Изменение, работающее с механизмом замка на расстоянии. Направьте его на замок: при достаточном Изменении для уровня замка он откроется. Разрушение тоже может участвовать: холод замораживает замок (его легче сломать), огонь растапливает лёд или открывает замок сразу, а электричество тоже открывает, если это разрешено.",
    "Manipulate Lock ist ein Veränderungszauber, der den Mechanismus eines Schlosses aus der Ferne bearbeitet. Wirke ihn auf ein Schloss: Reicht deine Veränderung für die Schlossstufe, öffnet es sich. Zerstörung kann mitwirken: Frost vereist ein Schloss (leichter aufzubrechen), Feuer taut es auf oder öffnet es gleich, und Schock öffnet es ebenfalls, sofern erlaubt.",
    "Manipulate Lock est un sort d'Altération qui manipule le mécanisme d'une serrure à distance. Lancez-le sur une serrure : si votre Altération suffit pour sa difficulté, elle s'ouvre. La Destruction peut s'en mêler : le froid gèle la serrure (plus facile à fracturer), le feu la dégèle ou l'ouvre carrément, et la foudre l'ouvre aussi si cela est autorisé.",
    "Manipulate Lock es un hechizo de Alteración que manipula el mecanismo de una cerradura a distancia. Lánzalo sobre una cerradura: con suficiente Alteración para su nivel, se abre. La Destrucción también puede participar: el hielo congela la cerradura (más fácil de romper), el fuego la descongela o la abre directamente y el rayo también la abre si se permite.",
    "Manipulate Lock è un incantesimo di Alterazione che agisce sul meccanismo di una serratura a distanza. Lancialo su una serratura: con Alterazione sufficiente per il suo grado, si apre. Anche la Distruzione può intervenire: il gelo congela la serratura (più facile da sfondare), il fuoco la scongela o la apre direttamente e il fulmine la apre a sua volta, se consentito.",
    "Manipulate Lock to zaklęcie ze szkoły Zmiany, które obsługuje mechanizm zamka na odległość. Rzuć je na zamek: przy wystarczającej Zmianie dla jego klasy zamek się otworzy. Zniszczenie też może pomóc: mróz zamraża zamek (łatwiej go rozbić), ogień go rozmraża lub otwiera od razu, a błyskawica również go otwiera, jeśli na to pozwolisz.",
    "Manipulate Lock je kouzlo školy Proměny, které ovládá mechanismus zámku na dálku. Sešli ho na zámek: při dostatečných Proměnách pro jeho úroveň se zámek otevře. Zapojit se může i Ničení: mráz zámek zmrazí (snáze se rozbije), oheň ho rozmrazí nebo rovnou otevře a blesk ho otevře také, je-li to povoleno.")
TRANSLATIONS["ALIO_SpellEnabled"] = T(
    "呪文 Manipulate Lock を習得する", "Manipulate Lock 주문 익히기", "学会法术 Manipulate Lock",
    "Знать заклинание Manipulate Lock", "Den Zauber Manipulate Lock beherrschen",
    "Connaître le sort Manipulate Lock", "Conocer el hechizo Manipulate Lock",
    "Conosci l'incantesimo Manipulate Lock", "Znaj zaklęcie Manipulate Lock",
    "Znát kouzlo Manipulate Lock")
TRANSLATIONS["ALIO_HelpSpellEnabled"] = T(
    "オン: 呪文が魔法書に追加されます（変化、消費30）。オフ: 再び取り除かれます。",
    "켜기: 주문이 마법서에 추가됩니다(변화, 소모 30). 끄기: 다시 제거됩니다.",
    "开启：将该法术加入你的法术书（变化系，消耗 30）。关闭：再次移除。",
    "Вкл.: заклинание добавляется в книгу заклинаний (Изменение, стоимость 30). Выкл.: оно снова убирается.",
    "An: Der Zauber wird deinem Zauberbuch hinzugefügt (Veränderung, Kosten 30). Aus: Er wird wieder entfernt.",
    "Activé : le sort est ajouté à votre grimoire (Altération, coût 30). Désactivé : il est retiré.",
    "Activado: el hechizo se añade a tu libro de hechizos (Alteración, coste 30). Desactivado: se vuelve a retirar.",
    "Attivo: l'incantesimo viene aggiunto al tuo libro degli incantesimi (Alterazione, costo 30). Disattivo: viene rimosso.",
    "Wł.: zaklęcie zostaje dodane do księgi zaklęć (Zmiana, koszt 30). Wył.: zostaje ponownie usunięte.",
    "Zapnuto: kouzlo se přidá do tvé knihy kouzel (Proměny, cena 30). Vypnuto: opět se odebere.")
TRANSLATIONS["ALIO_EslMissing"] = T(
    "ApocryphaLockInteractionOverhaul.esl が読み込まれていません ― MOD管理ソフトで有効にしてください。有効でないと呪文は存在できません。",
    "ApocryphaLockInteractionOverhaul.esl이 로드되지 않았습니다 ― 모드 관리자에서 활성화하세요. 그렇지 않으면 주문이 존재할 수 없습니다.",
    "未加载 ApocryphaLockInteractionOverhaul.esl ― 请在模组管理器中启用，否则该法术无法存在。",
    "ApocryphaLockInteractionOverhaul.esl не загружен — включите его в менеджере модов, иначе заклинание не может существовать.",
    "ApocryphaLockInteractionOverhaul.esl ist nicht geladen – aktiviere es in deinem Mod-Manager, sonst kann der Zauber nicht existieren.",
    "ApocryphaLockInteractionOverhaul.esl n'est pas chargé – activez-le dans votre gestionnaire de mods, sinon le sort ne peut pas exister.",
    "ApocryphaLockInteractionOverhaul.esl no está cargado: actívalo en tu gestor de mods o el hechizo no puede existir.",
    "ApocryphaLockInteractionOverhaul.esl non è caricato: attivalo nel tuo gestore di mod, altrimenti l'incantesimo non può esistere.",
    "ApocryphaLockInteractionOverhaul.esl nie jest wczytany – włącz go w menedżerze modyfikacji, inaczej zaklęcie nie może istnieć.",
    "ApocryphaLockInteractionOverhaul.esl není načten – zapni ho ve správci modů, jinak kouzlo nemůže existovat.")
TRANSLATIONS["ALIO_SpellKnown"] = T(
    "Manipulate Lock を習得しています。", "Manipulate Lock을 알고 있습니다.",
    "你已掌握 Manipulate Lock。", "Вы знаете Manipulate Lock.",
    "Du beherrschst Manipulate Lock.", "Vous connaissez Manipulate Lock.",
    "Conoces Manipulate Lock.", "Conosci Manipulate Lock.",
    "Znasz Manipulate Lock.", "Znáš Manipulate Lock.")
TRANSLATIONS["ALIO_SpellNotKnown"] = T(
    "現在 Manipulate Lock を習得していません。", "지금은 Manipulate Lock을 알지 못합니다.",
    "你目前尚未掌握 Manipulate Lock。", "Сейчас вы не знаете Manipulate Lock.",
    "Du beherrschst Manipulate Lock derzeit nicht.",
    "Vous ne connaissez pas Manipulate Lock pour le moment.",
    "Ahora mismo no conoces Manipulate Lock.", "Al momento non conosci Manipulate Lock.",
    "W tej chwili nie znasz Manipulate Lock.", "Manipulate Lock právě neznáš.")
TRANSLATIONS["ALIO_AllowedSpells"] = T(
    "錠に効く呪文", "자물쇠에 통하는 주문", "对锁生效的法术",
    "Заклинания, действующие на замки", "Zauber, die auf Schlösser wirken",
    "Sorts agissant sur les serrures", "Hechizos que afectan a las cerraduras",
    "Incantesimi efficaci sulle serrature", "Zaklęcia działające na zamki",
    "Kouzla působící na zámky")
TRANSLATIONS["ALIO_HelpAllowedSpells"] = T(
    "Manipulate Lock は変化を、ファイアとショックは破壊を、それぞれ同じ表に照らして判定します。",
    "Manipulate Lock은 변화를, 화염과 전격은 파괴를 같은 표에 대조해 판정합니다.",
    "Manipulate Lock 使用你的变化系；火焰与电击使用毁灭系，对照同一张表判定。",
    "Manipulate Lock использует ваше Изменение; огонь и электричество используют Разрушение по той же таблице.",
    "Manipulate Lock nutzt deine Veränderung; Feuer und Schock nutzen deine Zerstörung an derselben Tabelle.",
    "Manipulate Lock utilise votre Altération ; le feu et la foudre utilisent votre Destruction avec le même tableau.",
    "Manipulate Lock usa tu Alteración; el fuego y el rayo usan tu Destrucción contra la misma tabla.",
    "Manipulate Lock usa la tua Alterazione; fuoco e fulmine usano la tua Distruzione sulla stessa tabella.",
    "Manipulate Lock korzysta ze Zmiany; ogień i błyskawica korzystają ze Zniszczenia według tej samej tabeli.",
    "Manipulate Lock používá tvé Proměny; oheň a blesk používají tvé Ničení podle téže tabulky.")
TRANSLATIONS["ALIO_SkillMagic"] = T(
    "魔法スキル（呪文は変化、ファイアとショックは破壊）",
    "마법 실력(주문은 변화, 화염과 전격은 파괴)",
    "魔法技能（法术用变化系，火焰与电击用毁灭系）",
    "Магический навык (Изменение для заклинания, Разрушение для огня и электричества)",
    "Magiefertigkeit (Veränderung für den Zauber, Zerstörung für Feuer und Schock)",
    "Compétence magique (Altération pour le sort, Destruction pour le feu et la foudre)",
    "Habilidad mágica (Alteración para el hechizo, Destrucción para fuego y rayo)",
    "Abilità magica (Alterazione per l'incantesimo, Distruzione per fuoco e fulmine)",
    "Umiejętność magiczna (Zmiana dla zaklęcia, Zniszczenie dla ognia i błyskawicy)",
    "Magická dovednost (Proměny pro kouzlo, Ničení pro oheň a blesk)")
TRANSLATIONS["ALIO_FrostMalus"] = T(
    "フロストで破壊しやすくなる量", "냉기로 부수기 쉬워지는 정도", "冰霜使锁更易砸开的幅度",
    "Насколько холод облегчает взлом силой", "Frost erleichtert das Aufbrechen um",
    "Le froid facilite la fracture de", "El hielo facilita romper la cerradura en",
    "Il gelo facilita lo sfondamento di", "Mróz ułatwia rozbicie o",
    "Mráz usnadňuje rozbití o")
TRANSLATIONS["ALIO_HelpFrostMalus"] = T(
    "凍結した錠は、破壊に必要な武器スキルがこの分だけ下がります（0～100）。",
    "얼어붙은 자물쇠는 부수는 데 필요한 무기 실력이 이만큼 낮아집니다(0~100).",
    "被冻结的锁砸开时所需的武器技能降低这一数值，范围 0 到 100。",
    "Замёрзшему замку требуется на столько меньше навыка оружия для взлома силой, от 0 до 100.",
    "Ein vereistes Schloss braucht um so viel weniger Waffenfertigkeit zum Aufbrechen, 0 bis 100.",
    "Une serrure gelée demande d'autant moins de compétence d'arme pour être fracturée, de 0 à 100.",
    "Una cerradura congelada necesita esta cantidad menos de habilidad de arma para romperse, de 0 a 100.",
    "Una serratura congelata richiede questa quantità in meno di abilità con l'arma per essere sfondata, da 0 a 100.",
    "Zamrożony zamek wymaga o tyle mniej umiejętności broni do rozbicia, od 0 do 100.",
    "Zmrzlý zámek vyžaduje o tolik méně dovednosti se zbraní k rozbití, 0 až 100.")
TRANSLATIONS["ALIO_FrozenNow"] = T(
    "現在凍結中の錠: %u", "현재 얼어붙은 자물쇠: %u", "当前被冻结的锁：%u",
    "Сейчас заморожено замков: %u", "Derzeit vereiste Schlösser: %u",
    "Serrures actuellement gelées : %u", "Cerraduras congeladas ahora mismo: %u",
    "Serrature attualmente congelate: %u", "Obecnie zamrożone zamki: %u",
    "Právě zmrzlých zámků: %u")
TRANSLATIONS["ALIO_Spells_LockOnly"] = T(
    "Manipulate Lock のみ", "Manipulate Lock만", "仅 Manipulate Lock",
    "Только Manipulate Lock", "Nur Manipulate Lock", "Manipulate Lock uniquement",
    "Solo Manipulate Lock", "Solo Manipulate Lock", "Tylko Manipulate Lock",
    "Jen Manipulate Lock")
TRANSLATIONS["ALIO_Spells_Destruction"] = T(
    "破壊も含む: フロストで凍結、ファイアで解凍または開錠",
    "파괴도 포함: 냉기는 얼리고, 화염은 녹이거나 엽니다",
    "加上毁灭系：冰霜冻结，火焰解冻或开锁",
    "И Разрушение: холод замораживает, огонь растапливает или открывает",
    "Zusätzlich Zerstörung: Frost vereist, Feuer taut auf oder öffnet",
    "Plus la Destruction : le froid gèle, le feu dégèle ou ouvre",
    "Además Destrucción: el hielo congela, el fuego descongela o abre",
    "Più Distruzione: il gelo congela, il fuoco scongela o apre",
    "Dodatkowo Zniszczenie: mróz zamraża, ogień rozmraża lub otwiera",
    "Navíc Ničení: mráz zmrazí, oheň rozmrazí nebo otevře")
TRANSLATIONS["ALIO_Spells_Shock"] = T(
    "上記に加えて、ショック系呪文でも開錠できる",
    "위의 모든 것에 더해 전격 주문으로도 자물쇠를 엽니다",
    "在此基础上，电击法术也能开锁",
    "Всё перечисленное плюс электрические заклинания открывают замки",
    "All das und zusätzlich öffnen Schockzauber Schlösser",
    "Tout cela, et les sorts de foudre ouvrent aussi les serrures",
    "Todo eso y además los hechizos de rayo abren cerraduras",
    "Tutto ciò e in più gli incantesimi di fulmine aprono le serrature",
    "Wszystko powyższe, a do tego zaklęcia błyskawic otwierają zamki",
    "Vše výše uvedené a navíc bleskové kouzlo zámky otevírá")
# --- Pick Angle page -----------------------------------------------------------------------------
TRANSLATIONS["ALIO_AngleIntro"] = T(
    "ロックピックが折れたとき、次のピックは中央に戻らず、前のピックが折れた角度から始まります ― Remember Lockpick Angle の挙動を内蔵しています。特典を得てからのみ有効にすることもできます。",
    "자물쇠 따개가 부러지면 다음 따개는 가운데로 되돌아가지 않고 직전에 부러진 각도에서 시작합니다 ― Remember Lockpick Angle의 동작을 내장했습니다. 원한다면 특전을 얻은 뒤에만 적용할 수도 있습니다.",
    "撬锁器折断时，下一根不会回到中间，而是从上一根折断的角度开始 ― 内置了 Remember Lockpick Angle 的行为。也可以设置为拥有某个特技后才生效。",
    "Когда отмычка ломается, следующая начинает с того угла, где сломалась предыдущая, а не сбрасывается к центру — поведение Remember Lockpick Angle, встроенное сюда. По желанию — только при наличии способности.",
    "Bricht ein Dietrich, beginnt der nächste im Winkel des zuletzt gebrochenen, statt in die Mitte zurückzuspringen – das Verhalten von Remember Lockpick Angle, eingebaut. Wahlweise erst mit einem Vorteil.",
    "Quand un crochet se brise, le suivant repart de l'angle où le précédent a cassé au lieu de revenir au centre – le comportement de Remember Lockpick Angle, intégré. En option, seulement une fois un atout obtenu.",
    "Cuando una ganzúa se rompe, la siguiente empieza en el ángulo donde se rompió la anterior en vez de volver al centro: el comportamiento de Remember Lockpick Angle, integrado. Opcionalmente, solo cuando tengas cierta habilidad.",
    "Quando un grimaldello si spezza, il successivo riparte dall'angolo in cui si è rotto il precedente invece di tornare al centro: il comportamento di Remember Lockpick Angle, integrato. Facoltativamente solo dopo aver ottenuto un talento.",
    "Gdy wytrych pęka, następny zaczyna pod kątem, przy którym złamał się poprzedni, zamiast wracać na środek – wbudowane zachowanie Remember Lockpick Angle. Opcjonalnie dopiero po zdobyciu atutu.",
    "Když se paklíč zlomí, další začne v úhlu, kde se zlomil ten předchozí, místo návratu doprostřed – chování Remember Lockpick Angle, zabudované sem. Volitelně až poté, co získáš schopnost.")
TRANSLATIONS["ALIO_AngleEnabled"] = T(
    "ピックの角度を記憶する", "따개 각도 기억", "记住撬锁角度", "Запоминать угол отмычки",
    "Dietrichwinkel merken", "Mémoriser l'angle du crochet", "Recordar el ángulo de la ganzúa",
    "Ricorda l'angolo del grimaldello", "Zapamiętuj kąt wytrycha", "Pamatovat si úhel paklíče")
TRANSLATIONS["ALIO_HelpAngleEnabled"] = T(
    "オン: 折れたピックの角度を保持します。オフ: バニラ通り、新しいピックは毎回中央から始まります。",
    "켜기: 부러진 따개의 각도를 유지합니다. 끄기: 바닐라처럼 새 따개는 매번 가운데에서 시작합니다.",
    "开启：保留折断撬锁器的角度。关闭：与原版一样，每根新撬锁器都从中间开始。",
    "Вкл.: угол сломанной отмычки сохраняется. Выкл.: как в оригинале — каждая новая отмычка начинает с середины.",
    "An: Der Winkel eines gebrochenen Dietrichs bleibt erhalten. Aus: wie im Original – jeder neue Dietrich beginnt in der Mitte.",
    "Activé : l'angle du crochet brisé est conservé. Désactivé : comme dans le jeu de base – chaque nouveau crochet repart du centre.",
    "Activado: se conserva el ángulo de la ganzúa rota. Desactivado: como en el juego base, cada ganzúa nueva empieza en el centro.",
    "Attivo: l'angolo del grimaldello spezzato viene mantenuto. Disattivo: come nel gioco base, ogni nuovo grimaldello parte dal centro.",
    "Wł.: kąt złamanego wytrycha zostaje zachowany. Wył.: jak w podstawowej grze – każdy nowy wytrych zaczyna na środku.",
    "Zapnuto: úhel zlomeného paklíče se zachová. Vypnuto: jako v základní hře – každý nový paklíč začíná uprostřed.")
TRANSLATIONS["ALIO_AnglePerk"] = T(
    "この特典がある場合のみ", "이 특전이 있을 때만", "仅在拥有此特技时",
    "Только с этой способностью", "Nur mit diesem Vorteil", "Uniquement avec cet atout",
    "Solo con esta habilidad", "Solo con questo talento", "Tylko z tym atutem",
    "Jen s touto schopností")
TRANSLATIONS["ALIO_HelpAnglePerk"] = T(
    "角度が保持されるのは、キャラクターがこの特典を持っている間だけです。カスタム: INI でプラグイン名と特典のフォームIDを指定します（sPerkPlugin、uPerkFormID）。",
    "각도는 캐릭터가 이 특전을 가지고 있는 동안에만 유지됩니다. 사용자 지정: INI에 플러그인 이름과 특전의 폼 ID를 적으세요(sPerkPlugin, uPerkFormID).",
    "只有当角色拥有该特技时才会保留角度。自定义：在 INI 中填写插件名与特技的 Form ID（sPerkPlugin、uPerkFormID）。",
    "Угол сохраняется, только пока у персонажа есть эта способность. Своя: укажите плагин и form ID способности в INI (sPerkPlugin, uPerkFormID).",
    "Der Winkel bleibt nur erhalten, solange dein Charakter diesen Vorteil besitzt. Eigener: Plugin und Form-ID des Vorteils in der INI angeben (sPerkPlugin, uPerkFormID).",
    "L'angle n'est conservé que tant que votre personnage possède cet atout. Personnalisé : indiquez le plugin et l'ID de forme de l'atout dans l'INI (sPerkPlugin, uPerkFormID).",
    "El ángulo solo se conserva mientras tu personaje tenga esa habilidad. Personalizada: indica el plugin y el form ID de la habilidad en el INI (sPerkPlugin, uPerkFormID).",
    "L'angolo viene mantenuto solo finché il personaggio possiede questo talento. Personalizzato: indica il plugin e il form ID del talento nell'INI (sPerkPlugin, uPerkFormID).",
    "Kąt jest zachowywany tylko wtedy, gdy postać ma ten atut. Własny: podaj wtyczkę i form ID atutu w pliku INI (sPerkPlugin, uPerkFormID).",
    "Úhel se zachová jen tehdy, dokud tvá postava má tuto schopnost. Vlastní: uveď v INI plugin a form ID schopnosti (sPerkPlugin, uPerkFormID).")
TRANSLATIONS["ALIO_AnglePerkGate"] = T(
    "特典条件: %s", "특전 조건: %s", "特技条件：%s", "Условие способности: %s",
    "Vorteilsbedingung: %s", "Condition d'atout : %s", "Requisito de habilidad: %s",
    "Requisito del talento: %s", "Warunek atutu: %s", "Podmínka schopnosti: %s")
TRANSLATIONS["ALIO_AngleStandDown"] = T(
    "RememberLockpickAngle.dll が読み込まれています ― このセクションは停止し、角度の保持はそのMODが担当します。",
    "RememberLockpickAngle.dll이 로드되어 있습니다 ― 이 섹션은 물러나고 해당 모드가 각도를 담당합니다.",
    "已加载 RememberLockpickAngle.dll ― 本节停用，由该模组负责保留角度。",
    "Загружен RememberLockpickAngle.dll — этот раздел отключается, и угол сохраняет тот мод.",
    "RememberLockpickAngle.dll ist geladen – dieser Abschnitt tritt zurück und jene Mod behält den Winkel.",
    "RememberLockpickAngle.dll est chargé – cette section se met en retrait et c'est ce mod qui conserve l'angle.",
    "RememberLockpickAngle.dll está cargado: esta sección se aparta y ese mod se encarga del ángulo.",
    "RememberLockpickAngle.dll è caricato: questa sezione si ritira e quella mod mantiene l'angolo.",
    "Wczytano RememberLockpickAngle.dll – ta sekcja się wycofuje, a kąt zachowuje tamta modyfikacja.",
    "Je načten RememberLockpickAngle.dll – tato sekce ustupuje a úhel si drží onen mod.")
TRANSLATIONS["ALIO_AnglePatch"] = T(
    "パッチ: %s", "패치: %s", "补丁：%s", "Патч: %s", "Patch: %s",
    "Patch : %s", "Parche: %s", "Patch: %s", "Łatka: %s", "Patch: %s")
TRANSLATIONS["ALIO_Perk_None"] = T(
    "なし", "없음", "无", "Нет", "Keiner", "Aucun", "Ninguna", "Nessuno", "Brak", "Žádná")
TRANSLATIONS["ALIO_Perk_Locksmith"] = T(
    "鍵師", "자물쇠공", "锁匠", "Медвежатник", "Schlosser",
    "Serrurier", "Cerrajero", "Fabbro", "Ślusarz", "Zámečník")
TRANSLATIONS["ALIO_Perk_Unbreakable"] = T(
    "折れずの技", "불굴", "坚不可摧", "Несгибаемый", "Unzerbrechlich",
    "Incassable", "Irrompible", "Infrangibile", "Niezniszczalny", "Nezlomný")
TRANSLATIONS["ALIO_Perk_QuickHands"] = T(
    "早業", "재빠른 손놀림", "快手", "Ловкие руки", "Schnelle Hände",
    "Mains agiles", "Manos rápidas", "Mani veloci", "Zwinne dłonie", "Rychlé ruce")
TRANSLATIONS["ALIO_Perk_WaxKey"] = T(
    "蝋の鍵", "밀랍 열쇠", "蜡模钥匙", "Восковой ключ", "Wachsschlüssel",
    "Clé de cire", "Llave de cera", "Chiave di cera", "Woskowy klucz", "Voskový klíč")
TRANSLATIONS["ALIO_Perk_GoldenTouch"] = T(
    "黄金の手", "황금손", "点石成金", "Золотые руки", "Goldene Berührung",
    "Toucher d'or", "Toque de oro", "Tocco d'oro", "Złoty dotyk", "Zlatý dotek")
TRANSLATIONS["ALIO_Perk_TreasureHunter"] = T(
    "宝探し", "보물 사냥꾼", "寻宝者", "Кладоискатель", "Schatzsucher",
    "Chasseur de trésors", "Cazatesoros", "Cacciatore di tesori",
    "Poszukiwacz skarbów", "Lovec pokladů")
TRANSLATIONS["ALIO_Perk_Custom"] = T(
    "カスタム（INI の sPerkPlugin + uPerkFormID）",
    "사용자 지정(INI의 sPerkPlugin + uPerkFormID)",
    "自定义（INI 中的 sPerkPlugin + uPerkFormID）",
    "Своя (sPerkPlugin + uPerkFormID в INI)",
    "Eigener (sPerkPlugin + uPerkFormID in der INI)",
    "Personnalisé (sPerkPlugin + uPerkFormID dans l'INI)",
    "Personalizada (sPerkPlugin + uPerkFormID en el INI)",
    "Personalizzato (sPerkPlugin + uPerkFormID nell'INI)",
    "Własny (sPerkPlugin + uPerkFormID w pliku INI)",
    "Vlastní (sPerkPlugin + uPerkFormID v INI)")
# --- General page --------------------------------------------------------------------------------
TRANSLATIONS["ALIO_SkillGainHeader"] = T(
    "スキル上昇", "실력 상승", "技能提升", "Рост навыка", "Fertigkeitszuwachs",
    "Gain de compétence", "Ganancia de habilidad", "Aumento dell'abilità",
    "Przyrost umiejętności", "Zisk dovednosti")
TRANSLATIONS["ALIO_SkillGain"] = T(
    "錠を開けると、開けたスキルが上昇する", "자물쇠를 열면 그 수단이 된 실력이 오릅니다",
    "开锁时提升所使用的技能", "Открытие замка повышает применённый навык",
    "Das Öffnen eines Schlosses steigert die dabei benutzte Fertigkeit",
    "Ouvrir une serrure augmente la compétence utilisée",
    "Abrir una cerradura aumenta la habilidad empleada",
    "Aprire una serratura aumenta l'abilità usata",
    "Otwarcie zamka zwiększa użytą umiejętność",
    "Otevření zámku zvyšuje použitou dovednost")
TRANSLATIONS["ALIO_HelpSkillGain"] = T(
    "ゲーム本来の等級別の値（fSkillUsageLockPick ...）を、錠を開けた開錠・武器スキル・魔法系統に適用します。",
    "게임 본래의 등급별 수치(fSkillUsageLockPick ...)를 자물쇠를 연 자물쇠 따기, 무기 실력 또는 마법 계열에 적용합니다.",
    "采用游戏自身的分级数值（fSkillUsageLockPick ...），应用于开锁、武器技能或开锁所用的魔法学派。",
    "Собственные значения игры по уровням (fSkillUsageLockPick ...), применяемые к Взлому, навыку оружия или школе магии, которой был открыт замок.",
    "Die spieleigenen Werte je Stufe (fSkillUsageLockPick ...), angewandt auf Schlösserknacken, die Waffenfertigkeit oder die Magieschule, die das Schloss geöffnet hat.",
    "Les valeurs propres au jeu par difficulté (fSkillUsageLockPick ...), appliquées au Crochetage, à la compétence d'arme ou à l'école de magie qui a ouvert la serrure.",
    "Los valores propios del juego por nivel (fSkillUsageLockPick ...), aplicados a Allanamiento, a la habilidad de arma o a la escuela de magia que abrió la cerradura.",
    "I valori propri del gioco per grado (fSkillUsageLockPick ...), applicati a Scasso, all'abilità con l'arma o alla scuola di magia che ha aperto la serratura.",
    "Własne wartości gry dla poszczególnych klas (fSkillUsageLockPick ...), stosowane do Otwierania zamków, umiejętności broni lub szkoły magii, która otworzyła zamek.",
    "Vlastní hodnoty hry podle úrovně (fSkillUsageLockPick ...), použité na Páčení zámků, dovednost se zbraní nebo školu magie, která zámek otevřela.")
TRANSLATIONS["ALIO_SkillGainMult"] = T(
    "スキル上昇の倍率", "실력 상승 배율", "技能提升倍率", "Множитель роста навыка",
    "Multiplikator für den Fertigkeitszuwachs", "Multiplicateur de gain de compétence",
    "Multiplicador de ganancia de habilidad", "Moltiplicatore dell'aumento di abilità",
    "Mnożnik przyrostu umiejętności", "Násobitel zisku dovednosti")
TRANSLATIONS["ALIO_HelpSkillGainMult"] = T(
    "その上昇量を倍率で調整します（0.1～5）。", "그 상승량을 배율로 조정합니다(0.1~5).",
    "按倍率缩放该提升量，范围 0.1 到 5。", "Масштабирует этот прирост, от 0,1 до 5.",
    "Skaliert diesen Zuwachs, 0,1 bis 5.", "Met à l'échelle ce gain, de 0,1 à 5.",
    "Escala esa ganancia, de 0,1 a 5.", "Ridimensiona quell'aumento, da 0,1 a 5.",
    "Skaluje ten przyrost, od 0,1 do 5.", "Škáluje tento zisk, 0,1 až 5.")
TRANSLATIONS["ALIO_SoundHeader"] = T(
    "音", "소리", "音效", "Звук", "Ton", "Son", "Sonido", "Suono", "Dźwięk", "Zvuk")
TRANSLATIONS["ALIO_Sound"] = T(
    "錠が開いたときに音を鳴らす", "자물쇠가 열릴 때 소리 재생", "开锁时播放音效",
    "Проигрывать звук при открытии замка", "Beim Öffnen eines Schlosses einen Ton abspielen",
    "Jouer un son à l'ouverture d'une serrure", "Reproducir un sonido al abrirse una cerradura",
    "Riproduci un suono quando una serratura si apre", "Odtwarzaj dźwięk przy otwarciu zamka",
    "Přehrát zvuk při otevření zámku")
TRANSLATIONS["ALIO_HelpSound"] = T(
    "開錠と呪文にはゲーム本来の解錠音、武器には破壊音を使います。",
    "따기와 주문에는 게임 본래의 해제 소리를, 무기에는 부수는 소리를 씁니다.",
    "撬锁与法术使用游戏原本的开锁音效，武器则使用砸开的音效。",
    "Для отмычек и заклинаний — собственный звук отпирания игры, для оружия — звук удара.",
    "Für Dietriche und Zauber der spieleigene Aufschließ-Ton, für Waffen ein Aufbrechgeräusch.",
    "Le son de déverrouillage du jeu pour les crochets et les sorts, un bruit de fracture pour les armes.",
    "El sonido de apertura propio del juego para ganzúas y hechizos, y un golpe para las armas.",
    "Il suono di apertura del gioco per grimaldelli e incantesimi, un colpo per le armi.",
    "Własny dźwięk otwierania z gry dla wytrychów i zaklęć, uderzenie dla broni.",
    "Vlastní zvuk odemčení ze hry pro paklíče a kouzla, náraz pro zbraně.")
TRANSLATIONS["ALIO_Volume"] = T(
    "音量", "음량", "音量", "Громкость", "Lautstärke",
    "Volume", "Volumen", "Volume", "Głośność", "Hlasitost")
TRANSLATIONS["ALIO_HelpVolume"] = T(
    "0～1。", "0~1.", "0 到 1。", "От 0 до 1.", "0 bis 1.",
    "De 0 à 1.", "De 0 a 1.", "Da 0 a 1.", "Od 0 do 1.", "0 až 1.")
TRANSLATIONS["ALIO_CrimeHeader"] = T(
    "犯罪", "범죄", "犯罪", "Преступление", "Verbrechen",
    "Crime", "Delito", "Crimine", "Przestępstwo", "Zločin")
TRANSLATIONS["ALIO_Crime"] = T(
    "自分の物でない錠を開けるのは犯罪とする", "자기 소유가 아닌 자물쇠를 여는 것은 범죄",
    "开启不属于你的锁视为犯罪", "Вскрытие чужого замка — преступление",
    "Das Öffnen eines fremden Schlosses ist ein Verbrechen",
    "Ouvrir une serrure qui ne vous appartient pas est un crime",
    "Abrir una cerradura ajena es un delito", "Aprire una serratura non tua è un crimine",
    "Otwarcie cudzego zamka to przestępstwo", "Otevřít cizí zámek je zločin")
TRANSLATIONS["ALIO_HelpCrime"] = T(
    "目撃判定はゲーム本来のルールに従います。仲間や動物は通報せず、近くの町人は通報します。「早業」はバニラ同様、自動開錠のみを免除します。",
    "목격 판정은 게임 본래의 규칙을 따릅니다. 동료와 동물은 신고하지 않지만 근처 주민은 신고합니다. 재빠른 손놀림은 바닐라와 마찬가지로 자동 따기에만 적용됩니다.",
    "目击判定沿用游戏自身规则：随从与动物不会举报，附近的镇民会。“快手”与原版一样，只对自动开锁免罪。",
    "Свидетели определяются по правилам самой игры: спутники и животные не доносят, а горожанин поблизости — да. «Ловкие руки» освобождают только от автовзлома, как и в оригинале.",
    "Zeugen nach den Regeln des Spiels: Begleiter und Tiere zeigen dich nicht an, ein Stadtbewohner in der Nähe schon. „Schnelle Hände“ befreit nur vom automatischen Knacken, wie im Original.",
    "Témoins selon les règles du jeu : les compagnons et les animaux ne vous dénoncent pas, un citadin proche si. « Mains agiles » n'exempte que le crochetage automatique, comme dans le jeu de base.",
    "Los testigos siguen las reglas del propio juego: seguidores y animales no te denuncian, un lugareño cercano sí. «Manos rápidas» solo exime de la ganzúa automática, igual que en el juego base.",
    "I testimoni seguono le regole del gioco: seguaci e animali non ti denunciano, un cittadino vicino sì. «Mani veloci» esenta solo lo scasso automatico, come nel gioco base.",
    "Świadkowie według zasad samej gry: towarzysze i zwierzęta cię nie zgłaszają, pobliski mieszkaniec tak. „Zwinne dłonie” zwalniają tylko z automatycznego otwierania, tak jak w podstawowej grze.",
    "Svědci podle pravidel samotné hry: společníci a zvířata tě neudají, blízký měšťan ano. „Rychlé ruce“ osvobozují jen automatické páčení, stejně jako v základní hře.")
TRANSLATIONS["ALIO_CrimeGold"] = T(
    "通報される被害額", "신고되는 가치", "举报的赃物价值", "Заявленная стоимость",
    "Gemeldeter Wert", "Valeur déclarée", "Valor denunciado", "Valore denunciato",
    "Zgłoszona wartość", "Nahlášená hodnota")
TRANSLATIONS["ALIO_GoldFormat"] = T(
    "%.0f ゴールド", "%.0f 골드", "%.0f 金币", "%.0f зол.", "%.0f Gold",
    "%.0f pièces d'or", "%.0f de oro", "%.0f oro", "%.0f złota", "%.0f zlatých")
TRANSLATIONS["ALIO_HelpCrimeGold"] = T(
    "その違反がいくら相当として通報されるかです。", "그 범행이 얼마짜리로 신고되는지를 정합니다.",
    "该违法行为被举报时计作的价值。", "На какую сумму заявляется это правонарушение.",
    "Als wie wertvoll das Vergehen gemeldet wird.", "La valeur à laquelle l'infraction est déclarée.",
    "El valor con el que se denuncia la infracción.", "Il valore con cui viene denunciato il reato.",
    "Na jaką wartość zgłaszane jest to wykroczenie.", "Na jakou hodnotu se přestupek nahlásí.")
TRANSLATIONS["ALIO_MessagesHeader"] = T(
    "メッセージ", "메시지", "提示信息", "Сообщения", "Meldungen",
    "Messages", "Mensajes", "Messaggi", "Komunikaty", "Zprávy")
TRANSLATIONS["ALIO_Notifications"] = T(
    "このMODが動作したときにメッセージを表示する", "이 모드가 작동할 때 메시지 표시",
    "本模组生效时显示提示", "Показывать сообщение, когда мод срабатывает",
    "Eine Meldung anzeigen, wenn diese Mod handelt", "Afficher un message quand ce mod agit",
    "Mostrar un mensaje cuando este mod actúe", "Mostra un messaggio quando questa mod agisce",
    "Pokazuj komunikat, gdy ta modyfikacja zadziała", "Zobrazit zprávu, když tento mod zasáhne")
TRANSLATIONS["ALIO_HelpNotifications"] = T(
    "錠が拒否・開錠・凍結・解凍されたとき、画面に短い一文を表示します。",
    "자물쇠가 거부되거나 열리거나 얼거나 녹을 때 화면에 짧은 문구를 표시합니다.",
    "当锁被拒绝、打开、冻结或解冻时，在屏幕上显示一行简短提示。",
    "Короткая строка на экране, когда замок отказал, открылся, замёрз или оттаял.",
    "Eine kurze Zeile auf dem Bildschirm, wenn ein Schloss verweigert, geöffnet, vereist oder aufgetaut wird.",
    "Une courte ligne à l'écran quand une serrure est refusée, ouverte, gelée ou dégelée.",
    "Una línea breve en pantalla cuando una cerradura se rechaza, se abre, se congela o se descongela.",
    "Una breve riga a schermo quando una serratura viene rifiutata, aperta, congelata o scongelata.",
    "Krótki wiersz na ekranie, gdy zamek zostanie odrzucony, otwarty, zamrożony lub rozmrożony.",
    "Krátký řádek na obrazovce, když je zámek odmítnut, otevřen, zmrazen nebo rozmrazen.")
TRANSLATIONS["ALIO_DeactivateHeader"] = T(
    "すべてオフ", "전부 끄기", "全部关闭", "Всё выключить", "Alles aus",
    "Tout désactiver", "Todo desactivado", "Tutto disattivato", "Wszystko wyłączone",
    "Vše vypnuto")
TRANSLATIONS["ALIO_DeactivateBtn"] = T(
    "すべての機能を無効化", "모든 기능 비활성화", "停用所有功能",
    "Отключить все возможности", "Alle Funktionen deaktivieren",
    "Désactiver toutes les fonctions", "Desactivar todas las funciones",
    "Disattiva tutte le funzioni", "Wyłącz wszystkie funkcje", "Vypnout všechny funkce")
TRANSLATIONS["ALIO_StatusDeactivated"] = T(
    "すべての機能をオフにし、呪文も取り除きました。保存を押すと確定します。",
    "모든 기능을 껐고 주문도 제거했습니다. 저장을 눌러야 유지됩니다.",
    "已关闭所有功能并移除该法术。按“保存”以保留此状态。",
    "Все возможности выключены, заклинание удалено. Нажмите «Сохранить», чтобы это сохранить.",
    "Alle Funktionen ausgeschaltet, der Zauber wurde entfernt. Zum Behalten auf Speichern drücken.",
    "Toutes les fonctions sont désactivées et le sort est retiré. Appuyez sur Enregistrer pour conserver cet état.",
    "Se han desactivado todas las funciones y se ha retirado el hechizo. Pulsa Guardar para conservarlo.",
    "Tutte le funzioni sono disattivate e l'incantesimo è stato rimosso. Premi Salva per mantenere lo stato.",
    "Wyłączono wszystkie funkcje, a zaklęcie usunięto. Naciśnij Zapisz, aby to zachować.",
    "Všechny funkce jsou vypnuty a kouzlo bylo odebráno. Stiskni Uložit, aby to zůstalo.")
TRANSLATIONS["ALIO_HelpDeactivate"] = T(
    "要求値、自動開錠、破壊、呪文、ピック角度をまとめてオフにします ― MODを外す前にすべき状態です。",
    "요구 조건, 자동 따기, 부수기, 주문, 따개 각도를 한 번에 끕니다 ― 모드를 제거하기 전에 만들어야 할 상태입니다.",
    "一次性关闭要求、自动开锁、砸锁、法术与撬锁角度 ― 这是移除本模组前应处的状态。",
    "Разом выключает требования, автовзлом, взлом силой, заклинание и запоминание угла — то состояние, в котором мод следует удалять.",
    "Schaltet Anforderungen, automatisches Knacken, Aufbrechen, den Zauber und den Dietrichwinkel auf einmal aus – der Zustand vor dem Entfernen der Mod.",
    "Désactive d'un coup les exigences, le crochetage automatique, la fracture, le sort et l'angle du crochet – l'état à avoir avant de retirer le mod.",
    "Desactiva de una vez los requisitos, la ganzúa automática, el romper cerraduras, el hechizo y el ángulo de la ganzúa: el estado en el que debe estar antes de quitar el mod.",
    "Disattiva in un colpo requisiti, scasso automatico, sfondamento, incantesimo e angolo del grimaldello: lo stato in cui trovarsi prima di rimuovere la mod.",
    "Wyłącza naraz wymagania, automatyczne otwieranie, rozbijanie, zaklęcie i kąt wytrycha – stan, w jakim modyfikacja powinna być przed usunięciem.",
    "Vypne najednou požadavky, automatické páčení, rozbíjení, kouzlo i úhel paklíče – stav, ve kterém má mod být před odinstalací.")
# --- Debug page ----------------------------------------------------------------------------------
TRANSLATIONS["ALIO_LogLevel"] = T(
    "ログレベル", "로그 수준", "日志级别", "Уровень журнала", "Protokollstufe",
    "Niveau de journal", "Nivel de registro", "Livello del log", "Poziom dziennika",
    "Úroveň logu")
TRANSLATIONS["ALIO_HelpLogLevel"] = T(
    "即座に適用されます。ログは Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log にあります。",
    "즉시 적용됩니다. 로그 위치는 Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log 입니다.",
    "立即生效。日志位于 Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log。",
    "Применяется сразу. Журнал находится в Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "Wird sofort wirksam. Das Log liegt unter Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "S'applique immédiatement. Le journal se trouve dans Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "Se aplica de inmediato. El registro está en Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "Si applica subito. Il log si trova in Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "Działa natychmiast. Dziennik znajduje się w Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.",
    "Použije se okamžitě. Log je v Documents\\My Games\\Skyrim Special Edition\\SKSE\\ApocryphaLockInteractionOverhaul.log.")
TRANSLATIONS["ALIO_LiveHeader"] = T(
    "現在の状態", "실시간", "实时状态", "В реальном времени", "Live",
    "En direct", "En vivo", "In tempo reale", "Na żywo", "Živě")
TRANSLATIONS["ALIO_OpenedCount"] = T(
    "このセッションでこのMODが開けた錠: %llu", "이번 세션에 이 모드가 연 자물쇠: %llu",
    "本次游戏中由本模组打开的锁：%llu", "Замков открыто этим модом за сеанс: %llu",
    "Von dieser Mod in dieser Sitzung geöffnete Schlösser: %llu",
    "Serrures ouvertes par ce mod durant cette session : %llu",
    "Cerraduras abiertas por este mod en esta sesión: %llu",
    "Serrature aperte da questa mod in questa sessione: %llu",
    "Zamki otwarte przez tę modyfikację w tej sesji: %llu",
    "Zámků otevřených tímto modem v této relaci: %llu")
TRANSLATIONS["ALIO_FrozenCount"] = T(
    "凍結中の錠: %u", "얼어붙은 자물쇠: %u", "冻结的锁：%u", "Замороженных замков: %u",
    "Vereiste Schlösser: %u", "Serrures gelées : %u", "Cerraduras congeladas: %u",
    "Serrature congelate: %u", "Zamrożone zamki: %u", "Zmrzlé zámky: %u")
TRANSLATIONS["ALIO_LastEvent"] = T(
    "直近の出来事: %s", "최근 이벤트: %s", "最近事件：%s", "Последнее событие: %s",
    "Letztes Ereignis: %s", "Dernier événement : %s", "Último evento: %s",
    "Ultimo evento: %s", "Ostatnie zdarzenie: %s", "Poslední událost: %s")
TRANSLATIONS["ALIO_NothingYet"] = T(
    "まだありません", "아직 없음", "暂无", "пока ничего", "noch nichts",
    "rien pour l'instant", "todavía nada", "ancora nulla", "jeszcze nic", "zatím nic")
TRANSLATIONS["ALIO_SpellState"] = T(
    "呪文: %s", "주문: %s", "法术：%s", "Заклинание: %s", "Zauber: %s",
    "Sort : %s", "Hechizo: %s", "Incantesimo: %s", "Zaklęcie: %s", "Kouzlo: %s")
TRANSLATIONS["ALIO_SpellResolvedKnown"] = T(
    "解決済み・習得済み", "확인됨, 습득함", "已找到，已掌握", "найдено, известно",
    "gefunden, bekannt", "trouvé, connu", "encontrado, conocido", "trovato, conosciuto",
    "znalezione, znane", "nalezeno, známo")
TRANSLATIONS["ALIO_SpellResolvedNotKnown"] = T(
    "解決済み・未習得", "확인됨, 습득하지 않음", "已找到，未掌握", "найдено, неизвестно",
    "gefunden, nicht bekannt", "trouvé, non connu", "encontrado, no conocido",
    "trovato, non conosciuto", "znalezione, nieznane", "nalezeno, neznámo")
TRANSLATIONS["ALIO_SpellUnresolved"] = T(
    "未解決（ESL がありません）", "확인되지 않음(ESL 없음)", "未找到（缺少 ESL）",
    "НЕ найдено (нет ESL)", "NICHT gefunden (ESL fehlt)", "NON trouvé (ESL manquant)",
    "NO encontrado (falta el ESL)", "NON trovato (ESL mancante)",
    "NIE znaleziono (brak ESL)", "NENALEZENO (chybí ESL)")
TRANSLATIONS["ALIO_PatchState"] = T(
    "ピック角度パッチ: %s", "따개 각도 패치: %s", "撬锁角度补丁：%s",
    "Патч угла отмычки: %s", "Dietrichwinkel-Patch: %s",
    "Patch de l'angle du crochet : %s", "Parche del ángulo de la ganzúa: %s",
    "Patch dell'angolo del grimaldello: %s", "Łatka kąta wytrycha: %s",
    "Patch úhlu paklíče: %s")
TRANSLATIONS["ALIO_StandingDown"] = T(
    "停止中: %s", "물러남: %s", "是否停用：%s", "Отключён: %s", "Zurückgetreten: %s",
    "En retrait : %s", "Apartado: %s", "Ritirata: %s", "Wycofanie: %s", "Ustupuje: %s")
TRANSLATIONS["ALIO_StandingDownYes"] = T(
    "はい（Lock Overhaul.esp）", "예 (Lock Overhaul.esp)", "是（Lock Overhaul.esp）",
    "да (Lock Overhaul.esp)", "ja (Lock Overhaul.esp)", "oui (Lock Overhaul.esp)",
    "sí (Lock Overhaul.esp)", "sì (Lock Overhaul.esp)", "tak (Lock Overhaul.esp)",
    "ano (Lock Overhaul.esp)")
TRANSLATIONS["ALIO_CrosshairHeader"] = T(
    "見ている錠", "바라보는 자물쇠", "你正注视的锁", "Замок, на который вы смотрите",
    "Das Schloss, das du ansiehst", "La serrure que vous regardez",
    "La cerradura que estás mirando", "La serratura che stai guardando",
    "Zamek, na który patrzysz", "Zámek, na který se díváš")
TRANSLATIONS["ALIO_Log_Trace"] = T(
    "トレース", "추적", "追踪", "Трассировка", "Trace",
    "Trace", "Traza", "Traccia", "Śledzenie", "Trace")
TRANSLATIONS["ALIO_Log_Debug"] = T(
    "デバッグ", "디버그", "调试", "Отладка", "Debug",
    "Débogage", "Depuración", "Debug", "Debugowanie", "Ladění")
TRANSLATIONS["ALIO_Log_Info"] = T(
    "情報", "정보", "信息", "Информация", "Info",
    "Info", "Información", "Info", "Informacje", "Info")
TRANSLATIONS["ALIO_Log_Warning"] = T(
    "警告", "경고", "警告", "Предупреждение", "Warnung",
    "Avertissement", "Advertencia", "Avviso", "Ostrzeżenie", "Varování")
TRANSLATIONS["ALIO_Log_Error"] = T(
    "エラー", "오류", "错误", "Ошибка", "Fehler",
    "Erreur", "Error", "Errore", "Błąd", "Chyba")
TRANSLATIONS["ALIO_Log_Critical"] = T(
    "重大", "심각", "严重", "Критическая", "Kritisch",
    "Critique", "Crítico", "Critico", "Krytyczny", "Kritické")
TRANSLATIONS["ALIO_Log_Off"] = T(
    "オフ", "끄기", "关闭", "Выкл.", "Aus",
    "Désactivé", "Desactivado", "Disattivato", "Wyłączone", "Vypnuto")

# --- the lock tiers, bare and as "<tier> lock" -----------------------------------------------------
TRANSLATIONS["ALIO_Tier_Novice"] = T(
    "初級", "초급", "新手", "Простой", "Novize",
    "Novice", "Novato", "Novizio", "Nowicjusz", "Nováček")
TRANSLATIONS["ALIO_Tier_Apprentice"] = T(
    "中級", "수습", "学徒", "Ученический", "Lehrling",
    "Apprenti", "Aprendiz", "Apprendista", "Uczeń", "Učeň")
TRANSLATIONS["ALIO_Tier_Adept"] = T(
    "上級", "숙련", "熟练", "Средний", "Adept",
    "Adepte", "Adepto", "Adepto", "Adept", "Adept")
TRANSLATIONS["ALIO_Tier_Expert"] = T(
    "達人", "전문가", "专家", "Сложный", "Experte",
    "Expert", "Experto", "Esperto", "Ekspert", "Expert")
TRANSLATIONS["ALIO_Tier_Master"] = T(
    "マスター", "달인", "大师", "Мастерский", "Meister",
    "Maître", "Maestro", "Maestro", "Mistrz", "Mistr")
TRANSLATIONS["ALIO_TierLock_Novice"] = T(
    "初級の錠", "초급 자물쇠", "新手锁", "Простой замок", "Novizen-Schloss",
    "Serrure de novice", "Cerradura de novato", "Serratura da novizio",
    "Zamek nowicjusza", "Zámek pro nováčka")
TRANSLATIONS["ALIO_TierLock_Apprentice"] = T(
    "中級の錠", "수습 자물쇠", "学徒锁", "Ученический замок", "Lehrlings-Schloss",
    "Serrure d'apprenti", "Cerradura de aprendiz", "Serratura da apprendista",
    "Zamek ucznia", "Zámek pro učně")
TRANSLATIONS["ALIO_TierLock_Adept"] = T(
    "上級の錠", "숙련 자물쇠", "熟练锁", "Средний замок", "Adepten-Schloss",
    "Serrure d'adepte", "Cerradura de adepto", "Serratura da adepto",
    "Zamek adepta", "Zámek pro adepta")
TRANSLATIONS["ALIO_TierLock_Expert"] = T(
    "達人の錠", "전문가 자물쇠", "专家锁", "Сложный замок", "Experten-Schloss",
    "Serrure d'expert", "Cerradura de experto", "Serratura da esperto",
    "Zamek eksperta", "Zámek pro experta")
TRANSLATIONS["ALIO_TierLock_Master"] = T(
    "マスターの錠", "달인 자물쇠", "大师锁", "Мастерский замок", "Meister-Schloss",
    "Serrure de maître", "Cerradura de maestro", "Serratura da maestro",
    "Zamek mistrza", "Zámek pro mistra")

# ------------------------------------------------------------------------------------------------
# Writing the eleven files.
# ------------------------------------------------------------------------------------------------
def write_file(path, order, records):
    lines = []
    for key in order:
        lines.append("$" + key + "\t" + records[key].replace("\n", "\\n"))
    body = "\r\n".join(lines) + "\r\n"
    with io.open(path, "wb") as f:
        f.write(b"\xff\xfe")
        f.write(body.encode("utf-16-le"))


def main():
    order, english = read_keys()
    print("source/UI.cpp: {} keys".format(len(order)))

    missing = [k for k in order if k not in TRANSLATIONS]
    extra = [k for k in TRANSLATIONS if k not in english]
    if missing:
        raise SystemExit("no translations held for {} key(s): {}".format(len(missing), ", ".join(missing)))
    if extra:
        raise SystemExit("translations held for {} key(s) the source does not use: {}".format(len(extra), ", ".join(extra)))

    out_dir = os.path.join(REPO, "dist", "Interface", "Translations")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    for lang in LANGS:
        if lang == "english":
            records = english
        else:
            records = {k: TRANSLATIONS[k][lang] for k in order}
        path = os.path.join(out_dir, "{}_{}.txt".format(STEM, lang))
        write_file(path, order, records)
        print("  {:9s} {:3d} keys -> {}".format(lang, len(order), os.path.basename(path)))


if __name__ == "__main__":
    main()
