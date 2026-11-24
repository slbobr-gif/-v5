"""V5-67 (24.11): правки поверх контента. Запускать после postpatch.py. Идемпотентно.

1. Спички — коробок из 10 штук: костёр/дымокур по ходу события тратит спички (burnMatches), а не весь коробок;
   потеря или отдача коробка (украли, промок, отдал духу) — по-прежнему remove.
2. Монеты в тексте = монеты в эффекте: одна монета в тексте — уровень coin; «горсть» — small и т.д.
3. «Эскалатор вниз» — только глава 1 (Москва) и без намёка, что это его родная станция в другой главе.
"""
import json
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[3] / "app" / "assets" / "content"


def events_in(data):
    for x in data:
        if "steps" in x:
            for s in x["steps"]:
                if "event" in s:
                    yield s["event"]
                for b in s.get("branches", []):
                    yield b["event"]
        else:
            yield x


def choice(ev, cid):
    """Вариант по id; нет (событие переписано ниже по файлу) — пустой вариант, правки к нему не применяются."""
    return next((c for c in ev["choices"] if c["id"] == cid), {"outcomes": [], "text": ""})


# --- 1. костры: (событие, вариант) → спичек; True — добавить requires matches
FIRES = {
    ("rnd_ford_dusk", "camp"): 2,
    ("rnd_wild_ch2_mosquitoes", "smoke"): 3,
    ("rnd_sub_north_midges", "smoke"): 3,
    ("rnd_wild_north_first_frost", "fire"): 3,
    ("rnd_wild_north_midges", "smoke"): 3,
    ("fq_vodyanoy_s3", "fire"): 3,
    ("fq_ovinnik_s1", "outside"): 2,
}


def fires(ev):
    n = 0
    for (eid, cid), k in FIRES.items():
        if ev.get("id") != eid:
            continue
        c = choice(ev, cid)
        req = c.setdefault("requires", {}) if c.get("requires") is not None else None
        if req is None:
            c["requires"] = {"item": "matches"}
        elif "item" not in req:
            req["item"] = "matches"
        for o in c["outcomes"]:
            eff = o.setdefault("effects", {})
            rm = eff.get("remove") or {}
            if "matches" in rm:  # дымокур жёг коробок целиком — теперь несколько спичек
                rm.pop("matches")
                if not rm:
                    eff.pop("remove")
            if eff.get("burnMatches") != k:
                eff["burnMatches"] = k
                n += 1
    return n


# --- 2. монеты: (событие, вариант, номер исхода) → (уровень, замена в тексте исхода или None)
COINS = {
    ("ch3_fog_kikimora", "shiny", 0): ("-coin", None),
    ("ch1_domovoy_night", "treat", None): (None, ("лежит старая монета — тяжёлая, потёртая, вроде бы медная",
                                                  "лежат несколько старых монет — тяжёлых, потёртых, вроде бы медных")),
    ("ch2_kresttsy_rusalki", "towel", None): (None, ("кладёт ему в ладонь холодную старинную монетку",
                                                     "высыпает ему в ладонь горсть холодных старинных монет")),
    ("rnd_strap_snap", "search", None): (None, ("чужая монета — старая, тусклая, с орлом. Сергей кладёт её",
                                                "горстка чужих монет — старых, тусклых, с орлами. Сергей кладёт их")),
    ("rnd_ch1_leshy_circle", "bread", None): (None, ("во мху блестит старая монета", "во мху блестят старые монеты")),
    ("rnd_city_fountain_coins", "wish", None): (None, ("добавляет к монете ещё одну, на всякий случай",
                                                       "добавляет к монете ещё горсть, на всякий случай")),
}


def coins(ev):
    n = 0
    for (eid, cid, oi), (lvl, repl) in COINS.items():
        if ev.get("id") != eid:
            continue
        c = choice(ev, cid)
        outs = c["outcomes"] if oi is None else c["outcomes"][oi:oi + 1]
        for o in outs:
            eff = o.setdefault("effects", {})
            if lvl and eff.get("coins") != lvl:
                eff["coins"] = lvl
                if lvl.startswith("-"):
                    c.setdefault("requires", {})["coins"] = lvl[1:]
                n += 1
            if repl and repl[0] in o["text"]:
                o["text"] = o["text"].replace(*repl)
                n += 1
    return n


def escalator(ev):
    if ev.get("id") != "rnd_city_metro_escalator":
        return 0
    n = 0
    if ev["tags"] != ["ch1"]:
        ev["tags"] = ["ch1"]
        n += 1
    old = "Девять лет он сам был этим потоком: наушники, телефон, взгляд в точку над чужим плечом."
    new = ("Девять лет он сам был этим потоком — дома, на своей станции метро: наушники, телефон, "
           "взгляд в точку над чужим плечом.")
    if old in ev["text"]:
        ev["text"] = ev["text"].replace(old, new)
        n += 1
    old = "_Оказывается, у этого эскалатора есть конец. Девять лет не замечал._"
    new = "_Оказывается, у эскалатора есть конец. Девять лет бегал по таким и ни разу не заметил._"
    if old in ev["text"]:
        ev["text"] = ev["text"].replace(old, new)
        n += 1
    return n


def main():
    total = 0
    for f in sorted(CONTENT.glob("*.json")):
        data = json.loads(f.read_text())
        if not isinstance(data, list):
            continue
        n = 0
        for ev in events_in(data):
            if isinstance(ev, dict) and "choices" in ev:
                n += fires(ev) + coins(ev) + escalator(ev)
        if n:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"{f.name}: {n} правок")
            total += n
    print("итого правок:", total)



# --- 4. Угостить «чем есть» (24.11): встречи без духов — не только хлеб. Список — в порядке «что не жалко»;
#        шоколад зверям не даём (вреден), людям — можно. remove {вещь: 1} → {"$offer": 1}.
PEOPLE = ["bread", "berries", "pie", "tver_pryanik", "valdai_baranki", "chocolate", "kalitka_potato",
          "kalitka_millet", "kalitka_berry", "oatmeal", "dried_fish", "stew", "pozharsky", "rybnik"]
DOGS = ["bread", "fish", "dried_fish", "ryapushka", "stew", "pie", "kalitka_potato", "cod", "reindeer_tongue"]
FOX = ["fish", "dried_fish", "ryapushka", "bread", "stew", "cod", "reindeer_tongue"]
CAT = ["fish", "dried_fish", "ryapushka", "cod", "stew", "bread"]
BIRDS = ["bread", "berries", "oatmeal", "valdai_baranki", "kalitka_millet"]
SQUIRREL = ["berries", "bread", "valdai_baranki", "oatmeal", "cloudberry"]
OFFER = {
    ("ch1_chester_photo", "bread"): (DOGS, "Поделиться с рыжим едой"),
    ("rnd_village_dogs", "bread"): (DOGS, "Бросить им чего-нибудь съестного"),
    ("rnd_fox_snack", "share"): (FOX, "Отломить ей кусок из своих запасов"),
    ("wild_arctic_fox", "share"): (FOX, None),
    ("rnd_sub_cat_gate", "fish"): (CAT, None),
    ("rnd_city_pigeons", "feed"): (BIRDS, "Покрошить птицам чего-нибудь"),
    ("wild_squirrel", "share"): (SQUIRREL, "Положить ей ягод или кусочек хлеба"),
    ("rnd_sub_snt_barrier", "bread"): (PEOPLE, "Угостить сторожа чем есть"),
    ("rnd_wild_campfire_pair", "bread"): (PEOPLE, "Поделиться едой из рюкзака"),
    ("ch2_bronnitsa_digs", "share"): (PEOPLE, "Угостить студентов чем есть"),
    ("ch1_senezh_fire", "stew"): (PEOPLE, "Поделиться едой из рюкзака"),
}


def offers(ev):
    n = 0
    for (eid, cid), (lst, text) in OFFER.items():
        if ev.get("id") != eid:
            continue
        c = choice(ev, cid)
        req = c.get("requires") or {}
        old = req.pop("item", None)
        if req.get("offer") != lst:
            req["offer"] = lst
            n += 1
        c["requires"] = req
        if text and c["text"] != text:
            c["text"] = text
            n += 1
        for o in c["outcomes"]:
            rm = (o.get("effects") or {}).get("remove") or {}
            if old and old in rm:
                rm["$offer"] = rm.pop(old)
                n += 1
    return n


_main = main


def main():  # noqa: F811 — второй проход: угощения
    _main()
    total = 0
    for f in sorted(CONTENT.glob("*.json")):
        data = json.loads(f.read_text())
        if not isinstance(data, list):
            continue
        n = sum(offers(ev) for ev in events_in(data) if isinstance(ev, dict) and "choices" in ev)
        if n:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"{f.name}: угощений {n}")
            total += n
    print("угощений правок:", total)



# тексты исходов угощений — без конкретного хлеба/тушёнки (отдаётся то, что есть)
OFFER_TEXT = [
    ("Хлеб растворяется за секунду.", "Угощение исчезает за секунду."),
    ("Хлеб делят без драки, по старшинству.", "Угощение делят без драки, по старшинству."),
    ("Сторож принимает хлеб как знак доверия.", "Сторож принимает угощение как знак доверия."),
    ("У них закончился хлеб, и корка принимается как драгоценность.",
     "У них закончилась еда, и угощение принимается как драгоценность."),
    ("Сергей просовывает горбушку через сетку.", "Сергей просовывает кусок через сетку."),
    ("Тушёнку встречают аплодисментами.", "Угощение встречают аплодисментами."),
    ("Шоколадку делят на семерых, по квадратику,", "Угощение делят на семерых, по кусочку,"),
]


def offer_texts(ev):
    n = 0
    for (eid, cid) in OFFER:
        if ev.get("id") != eid:
            continue
        for o in choice(ev, cid)["outcomes"]:
            for a, b in OFFER_TEXT:
                if a in o["text"]:
                    o["text"] = o["text"].replace(a, b)
                    n += 1
    return n


_main2 = main


def main():  # noqa: F811
    _main2()
    for f in sorted(CONTENT.glob("*.json")):
        data = json.loads(f.read_text())
        if not isinstance(data, list):
            continue
        n = sum(offer_texts(ev) for ev in events_in(data) if isinstance(ev, dict) and "choices" in ev)
        if n:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"{f.name}: тексты угощений {n}")



# --- 5. Ключ овинника стал огнивом (аудит даров 24.11): тексты финала q_ovinnik
OGNIVO = [
    ("Ладно. Держи ключ. Где ни встретишь ригу, сарай, овин — открой им. Раз в неделю пущу тебя к себе, и спать будешь в тепле, как на печи.",
     "Ладно. Держи огниво. Чиркнешь — и огонь займётся, хоть в дождь, хоть на ветру, хоть у тебя руки от холода не гнутся. Мой огонь, не чужой."),
    ("На пороге лежит старый кованый ключ, тёплый от невидимого огня.",
     "На пороге лежит старое кованое огниво с кремнём, тёплое от невидимого огня."),
    ("_Мне подарили ключ от всех сеновалов России. Илья попросил бы ключ от всех шоколадных фабрик._",
     "_Мне подарили огонь. Настоящий, в кармане. Илья решил бы, что я теперь волшебник._"),
    ("Взять ключ и поклониться", "Взять огниво и поклониться"),
    ("Ключ тяжёлый и тёплый, как кружка чая.", "Огниво тяжёлое и тёплое, как кружка чая."),
    ("Ключ остаётся у Сергея.", "Огниво остаётся у Сергея."),
]


def ognivo(ev):
    if ev.get("id") != "fq_ovinnik_kind":
        return 0
    raw = json.dumps(ev, ensure_ascii=False)
    new = raw
    for a, b in OGNIVO:
        new = new.replace(json.dumps(a, ensure_ascii=False)[1:-1], json.dumps(b, ensure_ascii=False)[1:-1])
    if new == raw:
        return 0
    ev.clear()
    ev.update(json.loads(new))
    return 1


_main3 = main


def main():  # noqa: F811
    _main3()
    f = CONTENT / "quests.json"
    data = json.loads(f.read_text())
    n = sum(ognivo(ev) for ev in events_in(data) if isinstance(ev, dict) and "choices" in ev)
    if n:
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print("огниво:", n)



# --- 6. Дубли по смыслу (24.11): «Лось на дороге» дважды (rnd_moose_crossing и зверь wild_elk) —
#        случайное событие переписано в другое; одинаковые заголовки разведены.
LOGGING_TRUCK = {
    "title": "Лесовоз на повороте",
    "text": ("На узкой лесной дороге поперёк проезда стоит лесовоз: прицеп с брёвнами занесло на повороте, и задние "
             "колёса ушли в мягкую обочину. Водитель, усатый мужик в майке, ходит вокруг и курит одну за другой. "
             "Сдать назад он не может: прицеп не видно в зеркала, а напарник уехал в посёлок за трактором ещё утром. "
             "Объехать лесовоз пешком можно только по канаве с водой. Увидев Сергея, водитель оживляется: «Слышь, "
             "постой сзади, покажи, куда рулить. Метр влево, метр вправо — и я на асфальте». _Девять лет я говорил "
             "людям, куда рулить. Ни разу при этом не стоял сзади прицепа с брёвнами._"),
    "choices": [
        {"id": "guide", "text": "Встать сзади и показывать руками", "risk": "low", "outcomes": [
            {"weight": 3, "text": "«Левее! Стоп! Ещё чуть!» — через двадцать минут прицеп на асфальте. Водитель жмёт руку "
                                  "и отсыпает горсть монет: «За работу, не спорь».", "effects": {"coins": "small", "delay": "short"}},
            {"weight": 1, "text": "На втором заходе колесо проваливается ещё глубже, и Сергея окатывает грязью с ног до "
                                  "головы. Трактор всё-таки приходит, но ждать его приходится долго.",
             "effects": {"warmth": "-small", "delay": "medium"}}]},
        {"id": "ditch", "text": "Перейти канаву и идти дальше", "risk": "low", "outcomes": [
            {"weight": 2, "text": "Вода в канаве по колено и ледяная. Ботинки хлюпают ещё километр, зато дорога свободна.",
             "effects": {"warmth": "-small"}},
            {"weight": 1, "text": "Канава оказывается мельче, чем выглядела. Сергей перепрыгивает её почти посуху и "
                                  "чувствует себя ловким, как в двадцать лет.", "effects": {}}]},
        {"id": "wait", "text": "Сесть на бревно и подождать трактор", "risk": "none", "outcomes": [
            {"weight": 1, "text": "Водитель делится чаем из термоса и рассказывает про лесосеки, медведей и жену в "
                                  "Вологде. Трактор приходит через два часа. Время пролетает незаметно.",
             "effects": {"delay": "medium", "water": "small", "warmth": "small"}}]},
    ],
}
TITLES = {"rnd_wild_north_vodyanoy_ford": "Лягушка на свае", "rnd_wild_north_seid_hill": "Сейд на склоне сопки",
          "ch2_yazhelbitsy_bannik": "Баня для дальнобойщиков", "ch5_call_sasha_words": "Илья складывает слова",
          "fq_ovinnik_kind": "Огниво овинника"}


def dups(ev):
    n = 0
    if ev.get("id") == "rnd_moose_crossing" and ev.get("title") != LOGGING_TRUCK["title"]:
        ev.update(json.loads(json.dumps(LOGGING_TRUCK)))
        ev["tags"] = ["any", "road", "forest", "risk"]
        ev["art"] = "road"
        n += 1
    t = TITLES.get(ev.get("id"))
    if t and ev.get("title") != t:
        ev["title"] = t
        n += 1
    return n


_main4 = main


def main():  # noqa: F811
    _main4()
    for f in sorted(CONTENT.glob("*.json")):
        data = json.loads(f.read_text())
        if not isinstance(data, list):
            continue
        n = sum(dups(ev) for ev in events_in(data) if isinstance(ev, dict) and "choices" in ev)
        if n:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"{f.name}: дубли {n}")



# --- 7. Кикимора «Свой голос» (24.11): ch3_fog_kikimora больше не решается правилом «не отзывайся».
#        Кикимора умеет только повторять услышанное. Разоблачить — спросить то, чего она не слышала.
#        В этот раз по-настоящему звонит и Саша: кто молчит по привычке — пропускает живой звонок.
KIKIMORA = {
    "text": ("Дорогу пересекает болото, и гать — старые доски, полузатонувшие, скользкие — уходит прямо в туман. "
             "Белая ночь делает туман светящимся, как молоко в стакане у лампы. И из этого молока — смешок. Потом "
             "голос, тонкий, знакомый:\n\n— Серёжа! Серёжа, сюда! Я тут, у кочки!\n\nГолос Саши. И в ту же секунду в "
             "кармане вибрирует телефон: одна полоска связи, на экране — «Саша». Звонок настоящий. А голос в тумане "
             "всё равно её, слово в слово повторяет: «Серёжа, сюда!»\n\nБабушка говорила: кикимора своих слов не "
             "знает — только чужие, подслушанные.\n\n_Под Крестцами я просто промолчал. Тут молчанием, кажется, не "
             "обойтись: одна из двух Саш — настоящая._"),
    "choices": [
        {"id": "ask", "text": "Спросить в туман: «Как Илья зовёт Честера?»", "risk": "low", "outcomes": [
            {"weight": 3, "text": "Туман молчит, потом неуверенно повторяет: «Как Илья зовёт Честера?» — и обиженно "
                                  "фыркает. Своих слов у неё нет. Морок редеет, гать видна до края болота, а Сергей "
                                  "перезванивает Саше: «Чеся», — смеётся она.", "effects": {"shortcut": "short", "warmth": "small"}},
            {"weight": 1, "text": "Голос повторяет вопрос — и тут же, из кармана, Сашин: «Чеся, конечно!» Кикимора "
                                  "подслушала и подхватывает: «Чеся! Чеся!» Пока Сергей разбирается, где кто, он "
                                  "сходит с гати и черпает болото ботинком.", "effects": {"warmth": "-small"}}]},
        {"id": "phone", "text": "Ответить на звонок, не сходя с гати", "risk": "none", "outcomes": [
            {"weight": 2, "text": "«Ты где, у тебя там кто-то смеётся?» — спрашивает Саша. Голос в тумане пытается "
                                  "повторять, но за живым разговором не успевает и путается. Сергей идёт по доскам, "
                                  "говорит с женой, и болото кончается само.", "effects": {"warmth": "small"}},
            {"weight": 1, "text": "Связь рвётся на полуслове, и туман тут же договаривает Сашиным голосом: «…сюда, у "
                                  "кочки!» Сергей стоит, сжимая телефон, и не сразу находит следующую доску.",
             "effects": {"delay": "short"}}]},
        {"id": "silent", "text": "Не отвечать никому и идти, глядя под ноги", "risk": "none", "outcomes": [
            {"weight": 2, "text": "Он идёт, считая доски. Голос в тумане зовёт, телефон вибрирует и замолкает. На том "
                                  "берегу Сергей видит пропущенный и сообщение: «Илья сказал новое слово, хотела, "
                                  "чтобы ты услышал». _Правило сработало. А на душе гадко._", "effects": {"warmth": "-small"}},
            {"weight": 1, "text": "Одна доска ломается под ногой, и он проваливается в жижу по колено. Из тумана — "
                                  "тихое хихиканье. Телефон он так и не достал.", "effects": {"warmth": "-medium"}}]},
        {"id": "answer", "text": "Крикнуть в туман: «Саша?!»", "risk": "low", "outcomes": [
            {"weight": 1, "text": "Туман хохочет на десять голосов сразу и смыкается вокруг. Гать раздваивается, потом "
                                  "расстраивается, и Сергей час кружит между кочками, пока не выходит туда же, откуда "
                                  "начал. _Сам виноват. Бабушка же говорила._", "effects": {"detour": "medium", "warmth": "-small"}}]},
    ],
}


def kikimora(ev):
    if ev.get("id") != "ch3_fog_kikimora" or ev.get("text") == KIKIMORA["text"]:
        return 0
    ev.update(json.loads(json.dumps(KIKIMORA)))
    return 1


_main5 = main


def main():  # noqa: F811
    _main5()
    f = CONTENT / "events_ch3.json"
    data = json.loads(f.read_text())
    n = sum(kikimora(ev) for ev in events_in(data) if isinstance(ev, dict) and "choices" in ev)
    if n:
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print("кикимора:", n)


if __name__ == "__main__":
    main()
