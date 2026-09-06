"""Fast, deterministic answers for the demo pack's common visitor questions.

The resolver is deliberately local: it performs no retrieval, network request,
or model call. Facts are concise translations of the museum-sourced content in
``data/content_packs/demo_pack``. Unmatched questions return ``None`` so the
normal hybrid RAG and Gemini path remains authoritative for deeper questions.
"""

# ruff: noqa: E501

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from atlas.models.languages import normalize_language_code

PUBLIC_SCRIPTED_LANGUAGES = ("en", "fr", "es", "it", "zh")
SCRIPTED_FAQ_INTENTS = (
    "identify",
    "artist",
    "date",
    "subject",
    "technique",
    "meaning",
    "importance",
    "location",
    "detail",
    "fun_fact",
)
_MATCH_PRIORITY = (
    "artist",
    "date",
    "technique",
    "meaning",
    "importance",
    "location",
    "detail",
    "fun_fact",
    "subject",
    "identify",
)

# Static map derived from the catalogue's own text. It keeps the Jetson free of
# a runtime conversion dependency while accepting either Chinese writing form
# and returning the visitor dashboard's validated Traditional Chinese.
_SIMPLIFIED_CHARS = "环约画轻头们蓝黄只闪维尔变笔触让脸发这习并静秘线为术馆请挂钩几颜显来泽绿现阴群唇还冲里远处图层纸鲜鲁对丽与险却长胆强没张会艺样虽岳后实条断损顺别导征举国枪带领过垒复红个从体义卢宫亚标志构顶买经动于进杨盖双叠胧风达种晕涂轮烟雾确开视异窃气时边缘盗两弯缝护转庄树连观关纽无疗养户参创状许谢间谊组伦签周内纯礼胡须额镜秃鹫阳贵细号编统宽厘灵书语么谁历制应该节诉惊识吗听讲释"
_TRADITIONAL_CHARS = "環約畫輕頭們藍黃隻閃維爾變筆觸讓臉發這習並靜祕線爲術館請掛鉤幾顏顯來澤綠現陰羣脣還衝裏遠處圖層紙鮮魯對麗與險卻長膽強沒張會藝樣雖嶽後實條斷損順別導徵舉國槍帶領過壘覆紅個從體義盧宮亞標誌構頂買經動於進楊蓋雙疊朧風達種暈塗輪煙霧確開視異竊氣時邊緣盜兩彎縫護轉莊樹連觀關紐無療養戶參創狀許謝間誼組倫簽週內純禮鬍鬚額鏡禿鷲陽貴細號編統寬釐靈書語麼誰曆製應該節訴驚識嗎聽講釋"
_TO_TRADITIONAL = str.maketrans(_SIMPLIFIED_CHARS, _TRADITIONAL_CHARS)
_TO_SIMPLIFIED = str.maketrans(_TRADITIONAL_CHARS, _SIMPLIFIED_CHARS)

_FACT_FIELDS = (
    "kind",
    "subject",
    "technique",
    "meaning",
    "importance",
    "location",
    "detail",
    "fun_fact",
    "expert_note",
)
_INTENT_FIELD = {
    "subject": "subject",
    "technique": "technique",
    "meaning": "meaning",
    "importance": "importance",
    "location": "location",
    "detail": "detail",
    "fun_fact": "fun_fact",
}


@dataclass(frozen=True)
class ScriptedFaqAnswer:
    response: str
    intent: str
    artwork_id: str | None
    source_ids: tuple[str, ...] = ()


def _facts(*values: str) -> dict[str, str]:
    if len(values) != len(_FACT_FIELDS):
        raise ValueError("scripted FAQ record has the wrong number of fields")
    return dict(zip(_FACT_FIELDS, values, strict=True))


_ARTWORKS = {
    "girl_with_a_pearl_earring": {
        "title": {"en": "Girl with a Pearl Earring", "fr": "La Jeune Fille à la perle", "es": "La joven de la perla", "it": "Ragazza con l'orecchino di perla", "zh": "戴珍珠耳环的少女"},
        "artist": "Johannes Vermeer",
        "date": {"en": "around 1665", "fr": "vers 1665", "es": "hacia 1665", "it": "intorno al 1665", "zh": "约1665年"},
        "aliases": (
            "girl with a pearl earring",
            "jeune fille a la perle",
            "joven de la perla",
            "ragazza con l orecchino di perla",
            "戴珍珠耳环的少女",
        ),
        "sources": ("src_gpe_mauritshuis", "src_gpe_research"),
        "facts": {
            "en": _facts(
                "an oil painting",
                "An imagined young woman turns toward us, wearing a blue-and-yellow headscarf and a large shining earring.",
                "Vermeer used soft changes of light and only a few bright paint marks to make the face and earring glow.",
                "It is a tronie, a study of an imagined character, rather than a portrait of a known person.",
                "Its direct gaze, quiet mystery, and luminous light have made it one of Vermeer's best-known images.",
                "It is in the Mauritshuis in The Hague.",
                "Look for the earring: no hook is visible, and a few white marks create the whole illusion.",
                "Research shows that the background was once a glossy greenish black, not the flat black we see now.",
                "Technical study found ultramarine in the headscarf and the jacket's shadows, plus translucent glazes on the lips.",
            ),
            "fr": _facts(
                "une peinture à l'huile",
                "Une jeune femme imaginée se tourne vers nous, avec un foulard bleu et jaune et une grande boucle brillante.",
                "Vermeer a utilisé de doux passages de lumière et quelques touches claires pour faire briller le visage et la boucle.",
                "C'est une tronie, l'étude d'un personnage imaginé, et non le portrait d'une personne connue.",
                "Son regard direct, son mystère calme et sa lumière lumineuse en ont fait une image célèbre de Vermeer.",
                "Elle se trouve au Mauritshuis, à La Haye.",
                "Regardez la boucle : aucun crochet n'est visible et quelques touches blanches créent toute l'illusion.",
                "Les recherches montrent que le fond était autrefois d'un noir verdâtre brillant.",
                "L'étude technique a trouvé de l'outremer dans le foulard et les ombres de la veste, ainsi que des glacis sur les lèvres.",
            ),
            "es": _facts(
                "una pintura al óleo",
                "Una joven imaginada gira hacia nosotros con un pañuelo azul y amarillo y un gran pendiente brillante.",
                "Vermeer usó cambios suaves de luz y unas pocas marcas claras para hacer brillar el rostro y el pendiente.",
                "Es una tronie, un estudio de un personaje imaginado, no el retrato de una persona conocida.",
                "Su mirada directa, su misterio tranquilo y su luz luminosa la convirtieron en una imagen famosa de Vermeer.",
                "Está en el Mauritshuis de La Haya.",
                "Mira el pendiente: no se ve ningún gancho y unas pocas marcas blancas crean toda la ilusión.",
                "Los estudios muestran que el fondo fue antes negro verdoso y brillante.",
                "El análisis halló ultramar en el pañuelo y las sombras de la chaqueta, además de veladuras en los labios.",
            ),
            "it": _facts(
                "un dipinto a olio",
                "Una giovane immaginata si gira verso di noi con un copricapo blu e giallo e un grande orecchino luminoso.",
                "Vermeer usò passaggi morbidi di luce e pochi segni chiari per far brillare il viso e l'orecchino.",
                "È una tronie, lo studio di un personaggio immaginato, non il ritratto di una persona conosciuta.",
                "Lo sguardo diretto, il mistero quieto e la luce luminosa l'hanno resa una celebre immagine di Vermeer.",
                "Si trova al Mauritshuis dell'Aia.",
                "Guarda l'orecchino: non si vede alcun gancio e pochi tocchi bianchi creano tutta l'illusione.",
                "Le ricerche mostrano che lo sfondo era un tempo nero verdastro e lucido.",
                "L'analisi ha trovato oltremare nel copricapo e nelle ombre della giacca, oltre a velature sulle labbra.",
            ),
            "zh": _facts(
                "一幅油画",
                "一位想象中的年轻女子回头看向我们，戴着蓝黄色头巾和一只闪亮的大耳环。",
                "维米尔用柔和的明暗变化和少量亮色笔触，让脸和耳环像在发光。",
                "这是一幅想象人物习作，并不是某位已知人物的肖像。",
                "直接的目光、安静的神秘感和明亮的光线，让它成为维米尔最著名的作品之一。",
                "它收藏在海牙的莫瑞泰斯皇家美术馆。",
                "请看耳环：画中看不到挂钩，几笔白色颜料就造出了完整的闪光效果。",
                "研究显示，背景原来是有光泽的墨绿色，而不是现在看到的平黑色。",
                "技术分析在头巾和外套阴影中发现了群青，嘴唇上还使用了透明罩染。",
            ),
        },
    },
    "great_wave_off_kanagawa": {
        "title": {"en": "The Great Wave off Kanagawa", "fr": "La Grande Vague de Kanagawa", "es": "La gran ola de Kanagawa", "it": "La grande onda di Kanagawa", "zh": "神奈川冲浪里"},
        "artist": "Katsushika Hokusai",
        "date": {"en": "around 1830 to 1832", "fr": "vers 1830-1832", "es": "hacia 1830-1832", "it": "intorno al 1830-1832", "zh": "约1830至1832年"},
        "aliases": (
            "great wave",
            "wave off kanagawa",
            "grande vague",
            "gran ola",
            "grande onda",
            "神奈川冲浪里",
            "巨浪",
        ),
        "sources": ("src_wave_met", "src_wave_met_essay", "src_wave_bm"),
        "facts": {
            "en": _facts(
                "a colour woodblock print",
                "A huge curling wave rises over three small boats while Mount Fuji sits far away.",
                "Specialists carved separate woodblocks and printed layers of ink, including vivid Prussian blue, onto paper.",
                "The small boats face nature's beauty and danger while distant Mount Fuji appears calm and lasting.",
                "Its bold scale, claw-like foam, strong blue, and wide circulation made the design an international icon.",
                "There is no single original: impressions from the same blocks are held by museums including the Met and British Museum.",
                "Notice how Mount Fuji fits inside the wave's hollow and how the white foam looks like claws.",
                "Despite the title Thirty-six Views of Mount Fuji, the successful series eventually contained forty-six prints.",
                "Surviving impressions differ in line breaks, colour, block wear, and printing sequence while sharing Hokusai's design.",
            ),
            "fr": _facts(
                "une estampe en couleurs imprimée sur bois",
                "Une immense vague se courbe au-dessus de trois petits bateaux tandis que le mont Fuji reste au loin.",
                "Des artisans ont gravé plusieurs blocs de bois puis imprimé des couches d'encre, dont du bleu de Prusse, sur le papier.",
                "Les petits bateaux affrontent la beauté et le danger de la nature, tandis que le mont Fuji paraît calme et durable.",
                "Son échelle audacieuse, son écume en griffes, son bleu intense et sa large diffusion en ont fait une icône mondiale.",
                "Il n'existe pas un seul original : des tirages des mêmes blocs sont conservés notamment au Met et au British Museum.",
                "Remarquez le mont Fuji dans le creux de la vague et l'écume blanche qui ressemble à des griffes.",
                "Malgré le titre Trente-six vues du mont Fuji, la série a finalement compté quarante-six estampes.",
                "Les tirages conservés diffèrent par les lignes, les couleurs, l'usure des blocs et l'ordre d'impression.",
            ),
            "es": _facts(
                "una estampa en color impresa con bloques de madera",
                "Una enorme ola se curva sobre tres pequeñas barcas mientras el monte Fuji queda lejos.",
                "Varios artesanos tallaron bloques de madera e imprimieron capas de tinta, incluido azul de Prusia, sobre papel.",
                "Las pequeñas barcas afrontan la belleza y el peligro de la naturaleza, mientras el Fuji parece tranquilo y duradero.",
                "Su escala atrevida, la espuma como garras, el azul intenso y su gran difusión la hicieron un icono mundial.",
                "No hay un único original: museos como el Met y el British Museum conservan impresiones de los mismos bloques.",
                "Fíjate en el Fuji dentro del hueco de la ola y en la espuma blanca que parece tener garras.",
                "Aunque la serie se llama Treinta y seis vistas del monte Fuji, al final tuvo cuarenta y seis estampas.",
                "Las impresiones conservadas cambian en líneas, color, desgaste de los bloques y orden de impresión.",
            ),
            "it": _facts(
                "una stampa a colori da matrici di legno",
                "Un'onda enorme si curva sopra tre piccole barche mentre il monte Fuji resta lontano.",
                "Diversi artigiani incisero blocchi di legno e stamparono strati d'inchiostro, compreso il blu di Prussia, sulla carta.",
                "Le piccole barche affrontano la bellezza e il pericolo della natura, mentre il Fuji appare calmo e duraturo.",
                "La scala audace, la schiuma ad artiglio, il blu intenso e la grande diffusione ne fecero un'icona mondiale.",
                "Non esiste un unico originale: musei come il Met e il British Museum conservano impressioni dagli stessi blocchi.",
                "Osserva il Fuji nel vuoto dell'onda e la schiuma bianca che sembra formare artigli.",
                "Sebbene la serie si chiami Trentasei vedute del monte Fuji, alla fine comprese quarantasei stampe.",
                "Le impressioni rimaste variano nelle linee, nei colori, nell'usura dei blocchi e nell'ordine di stampa.",
            ),
            "zh": _facts(
                "一幅彩色木版画",
                "巨浪卷向三只小船，远处的富士山显得很小。",
                "工匠把图案刻在不同木板上，再把多层颜料印到纸上，其中包括鲜明的普鲁士蓝。",
                "小船面对大自然的美丽与危险，远处的富士山却显得平静而长久。",
                "大胆的大小对比、爪子般的浪花、强烈蓝色和大量印刷，让它成为世界名作。",
                "它没有唯一的一张原作；大都会艺术博物馆和大英博物馆等都收藏了同一套木板印出的版本。",
                "请看浪洞里的富士山，以及像爪子一样伸出的白色浪花。",
                "这套作品虽叫《富岳三十六景》，最后其实共有四十六幅。",
                "现存版本在线条断裂、颜色、木板磨损和印刷顺序上都有差别。",
            ),
        },
    },
    "liberty_leading_the_people": {
        "title": {"en": "Liberty Leading the People", "fr": "La Liberté guidant le peuple", "es": "La Libertad guiando al pueblo", "it": "La Libertà che guida il popolo", "zh": "自由引导人民"},
        "artist": "Eugène Delacroix",
        "date": {"en": "in 1830", "fr": "en 1830", "es": "en 1830", "it": "nel 1830", "zh": "1830年"},
        "aliases": (
            "liberty leading the people",
            "liberte guidant le peuple",
            "libertad guiando al pueblo",
            "liberta che guida il popolo",
            "自由引导人民",
        ),
        "sources": ("src_lib_louvre_record", "src_lib_louvre_guide"),
        "facts": {
            "en": _facts(
                "a monumental oil painting",
                "A woman who represents Liberty leads people over a Paris barricade, holding the French flag and a rifle.",
                "Delacroix built the crowd as a strong pyramid and repeated blue, white, and red across the scene.",
                "The woman is both a person of the people and an allegory, turning the idea of freedom into a human figure.",
                "The image grew from one Paris uprising into an internationally reused symbol of liberty.",
                "It is in the Louvre Museum in Paris.",
                "Look at Liberty's red Phrygian cap, an old emblem of freedom, and the flag at the pyramid's peak.",
                "It shows the July Revolution of 1830, not the French Revolution of 1789.",
                "The French state bought it in 1831, but its display history shifted before it entered the Louvre in 1874.",
            ),
            "fr": _facts(
                "une peinture à l'huile monumentale",
                "Une femme représentant la Liberté mène le peuple sur une barricade parisienne, avec le drapeau français et un fusil.",
                "Delacroix a construit la foule en pyramide et répété le bleu, le blanc et le rouge dans la scène.",
                "La femme est à la fois une personne du peuple et une allégorie qui donne un corps humain à la liberté.",
                "Née d'une révolte parisienne précise, l'image est devenue un symbole international de liberté.",
                "Elle se trouve au musée du Louvre à Paris.",
                "Regardez le bonnet phrygien rouge de la Liberté, ancien emblème de liberté, et le drapeau au sommet.",
                "La scène montre la révolution de Juillet 1830, et non la Révolution française de 1789.",
                "L'État l'a achetée en 1831, mais son exposition a changé plusieurs fois avant son entrée au Louvre en 1874.",
            ),
            "es": _facts(
                "una pintura al óleo monumental",
                "Una mujer que representa la Libertad guía al pueblo sobre una barricada de París con la bandera francesa y un fusil.",
                "Delacroix organizó la multitud como una gran pirámide y repitió azul, blanco y rojo por toda la escena.",
                "La mujer es a la vez una persona del pueblo y una alegoría que convierte la libertad en figura humana.",
                "La imagen pasó de una revuelta concreta de París a ser un símbolo internacional de libertad.",
                "Está en el Museo del Louvre de París.",
                "Mira el gorro frigio rojo de la Libertad, antiguo emblema de libertad, y la bandera en la cima.",
                "Representa la Revolución de Julio de 1830, no la Revolución francesa de 1789.",
                "El Estado francés la compró en 1831, pero cambió de lugar varias veces antes de llegar al Louvre en 1874.",
            ),
            "it": _facts(
                "un monumentale dipinto a olio",
                "Una donna che rappresenta la Libertà guida il popolo oltre una barricata di Parigi con la bandiera francese e un fucile.",
                "Delacroix costruì la folla come una forte piramide e ripeté blu, bianco e rosso nella scena.",
                "La donna è insieme una persona del popolo e un'allegoria che dà forma umana alla libertà.",
                "Nata da una specifica rivolta parigina, l'immagine è diventata un simbolo internazionale di libertà.",
                "Si trova al Museo del Louvre di Parigi.",
                "Guarda il berretto frigio rosso della Libertà, antico emblema di libertà, e la bandiera al vertice.",
                "Mostra la Rivoluzione di luglio del 1830, non la Rivoluzione francese del 1789.",
                "Lo Stato francese la comprò nel 1831, ma la sua esposizione cambiò prima dell'ingresso al Louvre nel 1874.",
            ),
            "zh": _facts(
                "一幅大型油画",
                "一位象征自由的女子举着法国国旗和步枪，带领人们越过巴黎的街垒。",
                "德拉克洛瓦把人群排成强烈的三角形，并在画面中重复蓝、白、红三色。",
                "这位女子既像普通人，也代表“自由”这个想法，让抽象概念变成人物。",
                "它从一次具体的巴黎起义，变成了世界各地反复使用的自由象征。",
                "它收藏在巴黎卢浮宫。",
                "请看自由女神的红色弗里吉亚帽，那是古老的自由标志；国旗就在三角构图顶端。",
                "画面表现的是1830年七月革命，不是1789年的法国大革命。",
                "法国政府在1831年买下它，经过多次收藏变动后，它于1874年进入卢浮宫。",
            ),
        },
    },
    "mona_lisa": {
        "title": {"en": "Mona Lisa", "fr": "La Joconde", "es": "La Gioconda", "it": "La Gioconda", "zh": "蒙娜丽莎"},
        "artist": "Leonardo da Vinci",
        "date": {"en": "from about 1503 to 1519", "fr": "entre environ 1503 et 1519", "es": "entre aproximadamente 1503 y 1519", "it": "tra circa il 1503 e il 1519", "zh": "约1503至1519年"},
        "aliases": ("mona lisa", "la joconde", "la gioconda", "蒙娜丽莎"),
        "sources": ("src_ml_louvre_gallery", "src_ml_louvre_record"),
        "facts": {
            "en": _facts(
                "an oil portrait painted on a poplar-wood panel",
                "Lisa Gherardini sits with folded hands, a small changing smile, and a hazy invented landscape behind her.",
                "Leonardo layered very thin glazes in a method called sfumato, making edges look soft and smoky.",
                "It portrays a real woman, Lisa Gherardini, while her uncertain smile makes the meeting feel open and mysterious.",
                "Leonardo's soft modelling, direct gaze, unusual landscape, famous smile, and later theft all strengthened its fame.",
                "It is in the Louvre Museum in Paris.",
                "Watch the smile while shifting your gaze: its soft edges can make the expression seem to change.",
                "The painting was stolen from the Louvre in 1911 and recovered more than two years later.",
                "Because the poplar panel has warped and cracked, the Louvre keeps it behind controlled protective glass.",
            ),
            "fr": _facts(
                "un portrait à l'huile peint sur un panneau de peuplier",
                "Lisa Gherardini est assise, les mains croisées, avec un petit sourire changeant et un paysage brumeux derrière elle.",
                "Léonard a superposé de très fins glacis par une méthode appelée sfumato, qui adoucit les contours.",
                "Le tableau représente Lisa Gherardini, mais son sourire incertain rend la rencontre ouverte et mystérieuse.",
                "Le modelé doux, le regard direct, le paysage étrange, le sourire et le vol ont renforcé sa célébrité.",
                "Elle se trouve au musée du Louvre à Paris.",
                "Observez le sourire en déplaçant votre regard : ses contours doux peuvent faire changer l'expression.",
                "Le tableau a été volé au Louvre en 1911 puis retrouvé plus de deux ans plus tard.",
                "Le panneau de peuplier s'étant déformé et fissuré, le Louvre le conserve derrière une vitre contrôlée.",
            ),
            "es": _facts(
                "un retrato al óleo pintado sobre una tabla de álamo",
                "Lisa Gherardini está sentada con las manos cruzadas, una pequeña sonrisa cambiante y un paisaje brumoso detrás.",
                "Leonardo superpuso veladuras muy finas con una técnica llamada sfumato, que vuelve suaves los bordes.",
                "Retrata a Lisa Gherardini, pero su sonrisa incierta hace que el encuentro parezca abierto y misterioso.",
                "El modelado suave, la mirada directa, el paisaje extraño, la sonrisa y el robo aumentaron su fama.",
                "Está en el Museo del Louvre de París.",
                "Mira la sonrisa al mover la vista: sus bordes suaves pueden hacer que la expresión parezca cambiar.",
                "La obra fue robada del Louvre en 1911 y recuperada más de dos años después.",
                "Como la tabla de álamo se deformó y agrietó, el Louvre la protege con vidrio de ambiente controlado.",
            ),
            "it": _facts(
                "un ritratto a olio dipinto su una tavola di pioppo",
                "Lisa Gherardini siede con le mani incrociate, un piccolo sorriso mutevole e un paesaggio nebbioso dietro di lei.",
                "Leonardo sovrappose velature sottilissime con il metodo dello sfumato, rendendo morbidi i contorni.",
                "Ritrae Lisa Gherardini, ma il sorriso incerto rende l'incontro aperto e misterioso.",
                "Il modellato morbido, lo sguardo diretto, il paesaggio, il sorriso e il furto ne aumentarono la fama.",
                "Si trova al Museo del Louvre di Parigi.",
                "Osserva il sorriso mentre sposti lo sguardo: i contorni morbidi possono far cambiare l'espressione.",
                "Il dipinto fu rubato dal Louvre nel 1911 e recuperato più di due anni dopo.",
                "Poiché la tavola di pioppo si è deformata e incrinata, il Louvre la conserva dietro un vetro controllato.",
            ),
            "zh": _facts(
                "一幅画在杨木板上的油画肖像",
                "丽莎·盖拉尔迪尼双手交叠坐着，带着似乎会变化的微笑，身后是朦胧的想象风景。",
                "达·芬奇叠加很薄的透明颜料，这种“晕涂法”让轮廓像烟雾一样柔和。",
                "画中是真实人物丽莎，但不确定的微笑让这次相遇显得开放又神秘。",
                "柔和造型、直视目光、奇异风景、著名微笑和后来的失窃，都增强了它的名气。",
                "它收藏在巴黎卢浮宫。",
                "移动目光时注意她的微笑：柔和的边缘会让表情像是在改变。",
                "这幅画在1911年从卢浮宫被盗，两年多后才被找回。",
                "杨木画板已经弯曲并出现裂缝，所以卢浮宫把它保存在受控环境的防护玻璃后。",
            ),
        },
    },
    "starry_night": {
        "title": {"en": "The Starry Night", "fr": "La Nuit étoilée", "es": "La noche estrellada", "it": "La notte stellata", "zh": "星夜"},
        "artist": "Vincent van Gogh",
        "date": {"en": "in June 1889", "fr": "en juin 1889", "es": "en junio de 1889", "it": "nel giugno 1889", "zh": "1889年6月"},
        "aliases": ("starry night", "nuit etoilee", "noche estrellada", "notte stellata", "星夜"),
        "sources": ("src_sn_moma",),
        "facts": {
            "en": _facts(
                "an oil painting on canvas",
                "A swirling blue night sky shines above a quiet village, with a tall dark cypress joining earth and sky.",
                "Van Gogh used vivid blue and yellow paint with strong visible strokes, building the scene over several daytime sessions.",
                "It mixes observation and invention to turn a landscape into an emotional image of night, nature, and imagination.",
                "Its moving sky, bold colour, and expressive brushwork made it a defining image of modern art.",
                "It is in the Museum of Modern Art, or MoMA, in New York.",
                "Find the bright crescent moon on the right, Venus left of centre, and the flame-shaped cypress in front.",
                "The village could not actually be seen from Van Gogh's asylum window; he built it from other views.",
                "Van Gogh moved the cypress closer and altered the celestial forms, deliberately intensifying the composition.",
            ),
            "fr": _facts(
                "une peinture à l'huile sur toile",
                "Un ciel nocturne bleu tourbillonne au-dessus d'un village calme, avec un grand cyprès sombre reliant terre et ciel.",
                "Van Gogh a utilisé des bleus et jaunes vifs avec des traits visibles, en peignant la scène le jour sur plusieurs séances.",
                "L'œuvre mêle observation et invention pour transformer un paysage en image émotive de la nuit et de la nature.",
                "Son ciel mobile, ses couleurs fortes et sa touche expressive en ont fait une image majeure de l'art moderne.",
                "Elle se trouve au Museum of Modern Art, ou MoMA, à New York.",
                "Cherchez le croissant de lune à droite, Vénus à gauche du centre et le cyprès en forme de flamme.",
                "Le village n'était pas visible depuis la fenêtre de l'asile; Van Gogh l'a construit à partir d'autres vues.",
                "Van Gogh a rapproché le cyprès et modifié les astres pour renforcer volontairement la composition.",
            ),
            "es": _facts(
                "una pintura al óleo sobre lienzo",
                "Un cielo nocturno azul gira sobre un pueblo tranquilo, con un ciprés oscuro que une la tierra y el cielo.",
                "Van Gogh usó azules y amarillos vivos con pinceladas visibles y pintó la escena de día en varias sesiones.",
                "Mezcla observación e invención para convertir un paisaje en una imagen emotiva de la noche y la naturaleza.",
                "Su cielo en movimiento, el color fuerte y las pinceladas expresivas la hicieron una imagen clave del arte moderno.",
                "Está en el Museum of Modern Art, o MoMA, de Nueva York.",
                "Busca la luna creciente a la derecha, Venus a la izquierda del centro y el ciprés con forma de llama.",
                "El pueblo no se veía desde la ventana del asilo; Van Gogh lo construyó a partir de otras vistas.",
                "Van Gogh acercó el ciprés y cambió las formas celestes para intensificar la composición.",
            ),
            "it": _facts(
                "un dipinto a olio su tela",
                "Un cielo notturno blu vortica sopra un villaggio quieto, con un alto cipresso scuro che unisce terra e cielo.",
                "Van Gogh usò blu e gialli vividi con pennellate visibili e dipinse la scena di giorno in più sedute.",
                "Mescola osservazione e invenzione, trasformando il paesaggio in un'immagine emotiva della notte e della natura.",
                "Il cielo in movimento, i colori forti e le pennellate espressive ne fecero un'immagine centrale dell'arte moderna.",
                "Si trova al Museum of Modern Art, o MoMA, di New York.",
                "Cerca la luna crescente a destra, Venere a sinistra del centro e il cipresso a forma di fiamma.",
                "Il villaggio non si vedeva dalla finestra dell'ospedale; Van Gogh lo costruì da altre vedute.",
                "Van Gogh avvicinò il cipresso e cambiò le forme celesti per intensificare la composizione.",
            ),
            "zh": _facts(
                "一幅布面油画",
                "旋转的蓝色夜空照亮安静村庄，一棵高高的黑色柏树把大地和天空连在一起。",
                "梵高用鲜明的蓝色和黄色画出清楚的笔触，并在白天分几次完成夜景。",
                "它把观察和想象放在一起，把风景变成关于夜晚、大自然和想象力的情感画面。",
                "流动的天空、强烈色彩和有表现力的笔触，让它成为现代艺术的重要形象。",
                "它收藏在纽约现代艺术博物馆，也就是MoMA。",
                "请找右边的新月、中央偏左的金星，以及前方像火焰一样的柏树。",
                "画中的村庄其实无法从梵高的疗养院窗户看到，是他参考其他景色创造的。",
                "梵高把柏树移近，并改变天体形状，有意加强整个构图。",
            ),
        },
    },
    "sunflowers": {
        "title": {"en": "Sunflowers", "fr": "Les Tournesols", "es": "Los girasoles", "it": "I girasoli", "zh": "向日葵"},
        "artist": "Vincent van Gogh",
        "date": {"en": "in 1888", "fr": "en 1888", "es": "en 1888", "it": "nel 1888", "zh": "1888年"},
        "aliases": ("sunflowers", "tournesols", "girasoles", "girasoli", "向日葵"),
        "sources": ("src_sf_ng",),
        "facts": {
            "en": _facts(
                "an oil still-life painting",
                "Fifteen sunflowers fill one vase: some are buds, some are open, and others are losing petals and becoming seeds.",
                "Van Gogh used thick raised paint called impasto, energetic strokes, and many shades of yellow.",
                "The flowers' stages of life can suggest time passing, while the series can also evoke friendship and gratitude.",
                "Its daring yellow palette and physical brushwork became a clear statement of Van Gogh's mature Arles style.",
                "This version is in the National Gallery in London.",
                "Notice the rough seed heads, the raised paint, and Van Gogh's blue Vincent signature on the vase.",
                "Van Gogh painted the first four sunflower canvases in one week, before the cut flowers faded.",
                "The seven Arles versions came in two groups: four in August 1888 and three repetitions in January 1889.",
            ),
            "fr": _facts(
                "une nature morte peinte à l'huile",
                "Quinze tournesols remplissent un vase : certains sont en bouton, d'autres ouverts ou déjà en graines.",
                "Van Gogh a utilisé une peinture épaisse en relief appelée empâtement, des traits énergiques et beaucoup de jaunes.",
                "Les étapes des fleurs peuvent évoquer le temps qui passe, mais aussi l'amitié et la gratitude.",
                "Sa palette jaune audacieuse et sa touche physique affirment le style mûr de Van Gogh à Arles.",
                "Cette version se trouve à la National Gallery de Londres.",
                "Observez les graines rugueuses, la peinture en relief et la signature bleue Vincent sur le vase.",
                "Van Gogh a peint les quatre premières toiles de tournesols en une semaine, avant que les fleurs ne fanent.",
                "Les sept versions d'Arles forment deux groupes : quatre d'août 1888 et trois reprises de janvier 1889.",
            ),
            "es": _facts(
                "un bodegón pintado al óleo",
                "Quince girasoles llenan un jarrón: algunos son capullos, otros están abiertos y otros ya forman semillas.",
                "Van Gogh usó pintura gruesa y elevada llamada empaste, pinceladas enérgicas y muchos tonos amarillos.",
                "Las etapas de las flores pueden hablar del paso del tiempo, y también de amistad y gratitud.",
                "Su atrevida paleta amarilla y la pincelada física muestran el estilo maduro de Van Gogh en Arlés.",
                "Esta versión está en la National Gallery de Londres.",
                "Mira las cabezas con semillas, la pintura elevada y la firma azul Vincent en el jarrón.",
                "Van Gogh pintó los cuatro primeros lienzos de girasoles en una semana, antes de que se marchitaran.",
                "Las siete versiones de Arlés forman dos grupos: cuatro de agosto de 1888 y tres repeticiones de enero de 1889.",
            ),
            "it": _facts(
                "una natura morta dipinta a olio",
                "Quindici girasoli riempiono un vaso: alcuni sono boccioli, altri aperti e altri stanno diventando semi.",
                "Van Gogh usò pittura spessa e in rilievo chiamata impasto, pennellate energiche e molte tonalità di giallo.",
                "Le fasi dei fiori possono parlare del tempo che passa, ma anche di amicizia e gratitudine.",
                "La tavolozza gialla audace e la pennellata fisica mostrano lo stile maturo di Van Gogh ad Arles.",
                "Questa versione si trova alla National Gallery di Londra.",
                "Guarda i capolini ruvidi, la pittura in rilievo e la firma blu Vincent sul vaso.",
                "Van Gogh dipinse le prime quattro tele di girasoli in una settimana, prima che i fiori appassissero.",
                "Le sette versioni di Arles formano due gruppi: quattro dell'agosto 1888 e tre repliche del gennaio 1889.",
            ),
            "zh": _facts(
                "一幅油画静物",
                "花瓶里有十五朵向日葵：有的是花苞，有的盛开，有的花瓣掉落并长出种子。",
                "梵高使用叫作厚涂的凸起颜料、有力的笔触和许多不同的黄色。",
                "花从生长到凋谢可以让人想到时间流逝，也可以表达友谊和感谢。",
                "大胆的黄色组合和有力量的笔触，清楚表现了梵高在阿尔勒的成熟风格。",
                "这个版本收藏在伦敦国家美术馆。",
                "请看粗糙的花籽、凸起的颜料，以及花瓶上蓝色的“Vincent”签名。",
                "梵高在一周内画完最早四幅向日葵，因为剪下的花很快会凋谢。",
                "阿尔勒的七个版本分两组：1888年8月四幅，1889年1月又画三幅。",
            ),
        },
    },
    "tutankhamun_mask": {
        "title": {"en": "Golden Burial Mask of Tutankhamun", "fr": "Masque funéraire en or de Toutankhamon", "es": "Máscara funeraria de oro de Tutankamón", "it": "Maschera funeraria d'oro di Tutankhamon", "zh": "图坦卡蒙黄金面具"},
        "artist": {"en": "unknown ancient Egyptian artisans", "fr": "des artisans égyptiens anciens dont les noms sont inconnus", "es": "artesanos del antiguo Egipto cuyos nombres se desconocen", "it": "artigiani dell'antico Egitto di nome sconosciuto", "zh": "姓名不详的古埃及工匠"},
        "date": {"en": "around 1323 BCE", "fr": "vers 1323 avant notre ère", "es": "hacia 1323 antes de nuestra era", "it": "intorno al 1323 avanti era", "zh": "约公元前1323年"},
        "aliases": ("tutankhamun mask", "king tut mask", "masque de toutankhamon", "mascara de tutankamon", "maschera di tutankhamon", "图坦卡蒙面具"),
        "sources": ("src_tut_gem", "src_tut_griffith"),
        "facts": {
            "en": _facts(
                "a solid-gold funerary mask",
                "A polished face wears a blue-and-gold royal headdress, a long false beard, and a cobra and vulture on the forehead.",
                "Ancient artisans shaped gold and added glass, lapis lazuli, obsidian, carnelian, faience, and quartzite.",
                "The mask protected Tutankhamun and joined his royal identity with gods linked to death, rebirth, and the sun.",
                "Its precious materials, craftsmanship, royal symbols, and famous tomb discovery made it an icon of ancient Egypt.",
                "The Grand Egyptian Museum catalogues it as GEM 8.",
                "Look at the cobra and vulture together on the forehead; they represent protection and a united Egypt.",
                "The mask was found directly over Tutankhamun's mummified head and shoulders and is 39.3 centimetres wide.",
                "The back carries a protective text linked to Spell 151b of the Book of the Dead.",
            ),
            "fr": _facts(
                "un masque funéraire en or massif",
                "Un visage poli porte une coiffe royale bleue et or, une longue barbe et un cobra avec un vautour sur le front.",
                "Des artisans anciens ont façonné l'or et ajouté verre, lapis-lazuli, obsidienne, cornaline, faïence et quartzite.",
                "Le masque protégeait Toutankhamon et liait son identité royale aux dieux de la mort, de la renaissance et du soleil.",
                "Ses matériaux précieux, son travail, ses symboles royaux et la tombe célèbre en ont fait une icône de l'Égypte ancienne.",
                "Le Grand Egyptian Museum le répertorie sous le numéro GEM 8.",
                "Regardez le cobra et le vautour réunis sur le front : ils évoquent la protection et l'Égypte unifiée.",
                "Le masque reposait sur la tête et les épaules momifiées de Toutankhamon et mesure 39,3 centimètres de large.",
                "Le dos porte un texte protecteur lié au sort 151b du Livre des Morts.",
            ),
            "es": _facts(
                "una máscara funeraria de oro macizo",
                "Un rostro pulido lleva un tocado real azul y dorado, una barba larga y una cobra con un buitre en la frente.",
                "Artesanos antiguos trabajaron oro y añadieron vidrio, lapislázuli, obsidiana, cornalina, fayenza y cuarcita.",
                "La máscara protegía a Tutankamón y unía su identidad real con dioses de la muerte, el renacer y el sol.",
                "Sus materiales, su artesanía, sus símbolos reales y la famosa tumba la hicieron un icono del antiguo Egipto.",
                "El Grand Egyptian Museum la cataloga como GEM 8.",
                "Mira la cobra y el buitre juntos en la frente: representan protección y un Egipto unido.",
                "Se encontró sobre la cabeza y los hombros momificados de Tutankamón y mide 39,3 centímetros de ancho.",
                "La parte trasera lleva un texto protector relacionado con el hechizo 151b del Libro de los Muertos.",
            ),
            "it": _facts(
                "una maschera funeraria in oro massiccio",
                "Un volto lucido porta un copricapo reale blu e oro, una lunga barba e un cobra con un avvoltoio sulla fronte.",
                "Antichi artigiani lavorarono l'oro e aggiunsero vetro, lapislazzuli, ossidiana, corniola, faience e quarzite.",
                "La maschera proteggeva Tutankhamon e univa la sua identità regale agli dei della morte, rinascita e sole.",
                "Materiali preziosi, maestria, simboli reali e la famosa tomba la resero un'icona dell'antico Egitto.",
                "Il Grand Egyptian Museum la cataloga come GEM 8.",
                "Guarda il cobra e l'avvoltoio insieme sulla fronte: indicano protezione e un Egitto unito.",
                "Fu trovata sulla testa e sulle spalle mummificate di Tutankhamon e misura 39,3 centimetri di larghezza.",
                "Il retro porta un testo protettivo legato alla formula 151b del Libro dei Morti.",
            ),
            "zh": _facts(
                "一件纯金葬礼面具",
                "光亮的脸戴着蓝金相间的王室头巾和长假胡须，额头上有眼镜蛇和秃鹫。",
                "古代工匠塑造黄金，并加入玻璃、青金石、黑曜石、红玉髓、彩陶和石英岩。",
                "面具保护图坦卡蒙，也把他的王室身份与死亡、重生和太阳有关的神连接起来。",
                "珍贵材料、精细工艺、王室符号和著名陵墓的发现，让它成为古埃及的代表形象。",
                "大埃及博物馆把它编为GEM 8号。",
                "请看额头上的眼镜蛇和秃鹫：它们表示保护，也象征统一的埃及。",
                "面具发现时盖在图坦卡蒙木乃伊的头和肩上，宽39.3厘米。",
                "面具背面有一段保护文字，与《亡灵书》第151b咒语有关。",
            ),
        },
    },
}


# Common phrasings are intentionally redundant so ordinary paraphrases and
# minor speech-recognition changes resolve without an embedding model.
_QUESTION_PHRASES = {
    "identify": {
        "en": ("what is this", "what is it", "what am i looking at", "name this artwork", "which artwork is this"),
        "fr": ("qu est ce que c est", "que regardons nous", "nom de cette oeuvre", "quelle oeuvre est ce"),
        "es": ("que es esto", "que estoy mirando", "nombre de esta obra", "que obra es"),
        "it": ("che cos e", "cosa sto guardando", "nome di quest opera", "che opera e"),
        "zh": ("这是什么", "我在看什么", "这件作品叫什么", "这是哪件作品"),
    },
    "artist": {
        "en": ("who painted", "who made", "who created", "which artist", "name the artist"),
        "fr": ("qui a peint", "qui a fait", "qui a cree", "quel artiste", "nom de l artiste"),
        "es": ("quien pinto", "quien hizo", "quien creo", "que artista", "nombre del artista"),
        "it": ("chi ha dipinto", "chi ha fatto", "chi ha creato", "quale artista", "nome dell artista"),
        "zh": ("谁画的", "谁做的", "谁创作的", "哪位艺术家", "作者是谁"),
    },
    "date": {
        "en": ("when was", "what year", "how old is", "when did the artist"),
        "fr": ("quand a ete", "quelle annee", "quel age a", "quand l artiste"),
        "es": ("cuando fue", "en que ano", "cuantos anos tiene", "cuando lo pinto"),
        "it": ("quando e stato", "in che anno", "quanti anni ha", "quando lo dipinse"),
        "zh": ("什么时候创作", "哪一年", "有多少年历史", "什么时候画"),
    },
    "subject": {
        "en": ("what does it show", "what is happening", "what can i see", "describe the scene"),
        "fr": ("que montre", "que se passe", "que voit on", "decris la scene"),
        "es": ("que muestra", "que esta pasando", "que puedo ver", "describe la escena"),
        "it": ("cosa mostra", "cosa sta succedendo", "cosa vedo", "descrivi la scena"),
        "zh": ("画了什么", "发生了什么", "我能看到什么", "描述画面"),
    },
    "technique": {
        "en": ("how was it made", "how did they make", "what is this made of", "what technique", "what materials", "how was it painted"),
        "fr": ("comment a ete fait", "comment l a fait", "quelle technique", "quels materiaux", "comment a ete peint"),
        "es": ("como se hizo", "como lo hizo", "que tecnica", "que materiales", "como fue pintado"),
        "it": ("come e stato fatto", "come lo ha fatto", "quale tecnica", "quali materiali", "come fu dipinto"),
        "zh": ("怎么做的", "怎么画的", "用了什么技法", "用了什么材料", "如何制作"),
    },
    "meaning": {
        "en": ("what does it mean", "what is the meaning", "what does it symbolize", "what is the message"),
        "fr": ("que signifie", "quel est le sens", "que symbolise", "quel est le message"),
        "es": ("que significa", "cual es el significado", "que simboliza", "cual es el mensaje"),
        "it": ("cosa significa", "qual e il significato", "cosa simboleggia", "qual e il messaggio"),
        "zh": ("是什么意思", "有什么含义", "象征什么", "想表达什么"),
    },
    "importance": {
        "en": ("why is it famous", "why is it important", "why is it special", "what made it famous"),
        "fr": ("pourquoi est elle celebre", "pourquoi est ce important", "pourquoi est ce special", "qu est ce qui l a rendu celebre"),
        "es": ("por que es famosa", "por que es importante", "por que es especial", "que la hizo famosa"),
        "it": ("perche e famoso", "perche e importante", "perche e speciale", "cosa lo ha reso famoso"),
        "zh": ("为什么有名", "为什么重要", "为什么特别", "怎么出名的"),
    },
    "location": {
        "en": ("where is it", "where is it now", "which museum", "where can i see", "where is this kept"),
        "fr": ("ou est elle maintenant", "dans quel musee", "ou peut on voir", "ou est conservee"),
        "es": ("donde esta ahora", "en que museo", "donde puedo verla", "donde se conserva"),
        "it": ("dove si trova ora", "in quale museo", "dove posso vederlo", "dove e conservato"),
        "zh": ("现在在哪里", "在哪个博物馆", "哪里能看到", "收藏在哪里"),
    },
    "detail": {
        "en": ("what should i notice", "what detail", "where should i look", "show me a detail"),
        "fr": ("que dois je remarquer", "quel detail", "ou dois je regarder", "montre moi un detail"),
        "es": ("en que debo fijarme", "que detalle", "donde debo mirar", "muestrame un detalle"),
        "it": ("cosa dovrei notare", "quale dettaglio", "dove devo guardare", "mostrami un dettaglio"),
        "zh": ("应该注意什么", "有什么细节", "该看哪里", "告诉我一个细节"),
    },
    "fun_fact": {
        "en": ("tell me a fun fact", "something surprising", "interesting fact", "did you know"),
        "fr": ("raconte un fait amusant", "quelque chose de surprenant", "fait interessant", "le savais tu"),
        "es": ("dime un dato curioso", "algo sorprendente", "dato interesante", "sabias que"),
        "it": ("dimmi una curiosita", "qualcosa di sorprendente", "fatto interessante", "lo sapevi"),
        "zh": ("有趣的事实", "有什么惊喜", "有趣的知识", "你知道吗"),
    },
}

_FOLLOW_UPS = {
    "en": {
        "identify": "Would you like to hear who made it or what to notice?",
        "artist": "Would you like to know how it was made?",
        "date": "Should I tell you what was happening at that time?",
        "subject": "What catches your attention first?",
        "technique": "Should I explain one technique more closely?",
        "meaning": "Which idea stands out to you?",
        "importance": "Would you like one surprising fact?",
        "location": "Would you like to know how it got there?",
        "detail": "Can you spot it?",
        "fun_fact": "Would you like another fact?",
    },
    "fr": {
        "identify": "Voulez-vous savoir qui l'a créée ou quoi observer ?",
        "artist": "Voulez-vous savoir comment elle a été réalisée ?",
        "date": "Dois-je raconter ce qui se passait à cette époque ?",
        "subject": "Qu'est-ce qui attire d'abord votre attention ?",
        "technique": "Dois-je expliquer une technique de plus près ?",
        "meaning": "Quelle idée vous frappe le plus ?",
        "importance": "Voulez-vous un fait surprenant ?",
        "location": "Voulez-vous savoir comment elle y est arrivée ?",
        "detail": "Pouvez-vous le repérer ?",
        "fun_fact": "Voulez-vous un autre fait ?",
    },
    "es": {
        "identify": "¿Quieres saber quién la creó o qué detalle mirar?",
        "artist": "¿Quieres saber cómo se hizo?",
        "date": "¿Te cuento qué ocurría en esa época?",
        "subject": "¿Qué llama primero tu atención?",
        "technique": "¿Quieres que explique una técnica más de cerca?",
        "meaning": "¿Qué idea te llama más la atención?",
        "importance": "¿Quieres un dato sorprendente?",
        "location": "¿Quieres saber cómo llegó allí?",
        "detail": "¿Puedes encontrarlo?",
        "fun_fact": "¿Quieres otro dato?",
    },
    "it": {
        "identify": "Vuoi sapere chi l'ha creata o cosa osservare?",
        "artist": "Vuoi sapere come è stata realizzata?",
        "date": "Vuoi sapere cosa accadeva in quel periodo?",
        "subject": "Cosa attira per prima la tua attenzione?",
        "technique": "Vuoi che spieghi meglio una tecnica?",
        "meaning": "Quale idea ti colpisce di più?",
        "importance": "Vuoi una curiosità sorprendente?",
        "location": "Vuoi sapere come è arrivata lì?",
        "detail": "Riesci a trovarlo?",
        "fun_fact": "Vuoi un'altra curiosità?",
    },
    "zh": {
        "identify": "你想听听是谁创作的，还是先看一个细节？",
        "artist": "你想知道它是怎么做出来的吗？",
        "date": "要我讲讲那个时代发生的事吗？",
        "subject": "什么最先吸引你的注意？",
        "technique": "要我仔细解释一种技法吗？",
        "meaning": "哪个想法最打动你？",
        "importance": "你想听一个意外的小知识吗？",
        "location": "你想知道它怎么到那里的吗？",
        "detail": "你能找到它吗？",
        "fun_fact": "还想听一个小知识吗？",
    },
}

_EARLY_CHILD_FOLLOW_UPS = {
    "en": {
        "identify": "Can you spot one thing you like?",
        "artist": "Want to hear how they made it?",
        "date": "Want a tiny story from long ago?",
        "subject": "What do you see first?",
        "technique": "Want an easy example?",
        "meaning": "What feeling do you get?",
        "importance": "Want a fun surprise?",
        "location": "Want to know how it got there?",
        "detail": "Can you find it?",
        "fun_fact": "Want one more fun fact?",
    },
    "fr": {
        "identify": "Peux-tu trouver une chose que tu aimes ?",
        "artist": "Veux-tu savoir comment cette personne l'a faite ?",
        "date": "Veux-tu une petite histoire d'autrefois ?",
        "subject": "Que vois-tu en premier ?",
        "technique": "Veux-tu un exemple facile ?",
        "meaning": "Quelle émotion ressens-tu ?",
        "importance": "Veux-tu une surprise amusante ?",
        "location": "Veux-tu savoir comment elle est arrivée là ?",
        "detail": "Peux-tu le trouver ?",
        "fun_fact": "Veux-tu un autre fait amusant ?",
    },
    "es": {
        "identify": "¿Puedes encontrar algo que te guste?",
        "artist": "¿Quieres saber cómo la hizo?",
        "date": "¿Quieres un cuento corto de hace mucho tiempo?",
        "subject": "¿Qué ves primero?",
        "technique": "¿Quieres un ejemplo fácil?",
        "meaning": "¿Qué emoción sientes?",
        "importance": "¿Quieres una sorpresa divertida?",
        "location": "¿Quieres saber cómo llegó allí?",
        "detail": "¿Puedes encontrarlo?",
        "fun_fact": "¿Quieres otro dato divertido?",
    },
    "it": {
        "identify": "Riesci a trovare una cosa che ti piace?",
        "artist": "Vuoi sapere come l'ha fatta?",
        "date": "Vuoi una piccola storia di tanto tempo fa?",
        "subject": "Cosa vedi per prima?",
        "technique": "Vuoi un esempio facile?",
        "meaning": "Che emozione senti?",
        "importance": "Vuoi una sorpresa divertente?",
        "location": "Vuoi sapere come è arrivata lì?",
        "detail": "Riesci a trovarlo?",
        "fun_fact": "Vuoi un'altra curiosità divertente?",
    },
    "zh": {
        "identify": "你能找出一個你喜歡的地方嗎？",
        "artist": "想知道他是怎麼做的嗎？",
        "date": "想聽一個很久以前的小故事嗎？",
        "subject": "你先看到了什麼？",
        "technique": "想聽一個簡單的例子嗎？",
        "meaning": "你感到什麼心情？",
        "importance": "想聽一個好玩的驚喜嗎？",
        "location": "想知道它怎麼到那裡的嗎？",
        "detail": "你能找到它嗎？",
        "fun_fact": "還想聽一個有趣的小知識嗎？",
    },
}

_CLARIFY_ARTWORK = {
    "en": "Which artwork are you looking at?",
    "fr": "Quelle œuvre regardez-vous ?",
    "es": "¿Qué obra estás mirando?",
    "it": "Quale opera stai guardando?",
    "zh": "你正在看哪件作品？",
}


def _normalize(text: str) -> str:
    text = str(text).translate(_TO_SIMPLIFIED)
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


@lru_cache(maxsize=len(PUBLIC_SCRIPTED_LANGUAGES))
def _phrase_index(language: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return tuple(
        (intent, normalized, tuple(normalized.split()))
        for intent in _MATCH_PRIORITY
        for phrase in _QUESTION_PHRASES[intent][language]
        if (normalized := _normalize(phrase))
    )


def match_scripted_intent(question: str, language: str) -> str | None:
    """Match a common question, including close paraphrases, without a model."""
    lang = normalize_language_code(language)
    if lang not in PUBLIC_SCRIPTED_LANGUAGES:
        return None
    normalized = _normalize(question)
    if not normalized:
        return None
    phrase_index = _phrase_index(lang)
    for intent in _MATCH_PRIORITY:
        if any(
            phrase in normalized
            for indexed_intent, phrase, _phrase_words in phrase_index
            if indexed_intent == intent
        ):
            return intent
    if len(normalized) < 8:
        return None
    best_intent = None
    best_ratio = 0.0
    words = normalized.split()
    word_set = set(words)
    for intent, normalized_phrase, phrase_words in phrase_index:
        if not word_set.intersection(phrase_words):
            continue
        ratio = SequenceMatcher(None, normalized, normalized_phrase).ratio()
        phrase_word_count = len(phrase_words)
        for start in range(max(0, len(words) - phrase_word_count + 1)):
            window = " ".join(words[start : start + phrase_word_count])
            window_ratio = SequenceMatcher(
                None,
                window,
                normalized_phrase,
            ).ratio()
            if window_ratio >= 0.84:
                return intent
        if ratio > best_ratio:
            best_intent, best_ratio = intent, ratio
    return best_intent if best_ratio >= 0.70 else None


def _named_artwork(question: str) -> str | None:
    normalized = _normalize(question)
    for artwork_id, record in _ARTWORKS.items():
        if any(_normalize(alias) in normalized for alias in record["aliases"]):
            return artwork_id
    return None


def _basic_answer(intent: str, record: dict, facts: dict[str, str], lang: str) -> str:
    title_value = record["title"]
    artist_value = record["artist"]
    date_value = record["date"]
    title = title_value[lang] if isinstance(title_value, dict) else title_value
    artist = artist_value[lang] if isinstance(artist_value, dict) else artist_value
    date = date_value[lang] if isinstance(date_value, dict) else date_value
    if lang == "fr":
        templates = {
            "identify": f"C'est {title}, {facts['kind']}.",
            "artist": f"{artist} a réalisé cette œuvre.",
            "date": f"Cette œuvre a été réalisée {date}.",
        }
    elif lang == "es":
        templates = {
            "identify": f"Es {title}, {facts['kind']}.",
            "artist": f"{artist} creó esta obra.",
            "date": f"Esta obra fue realizada {date}.",
        }
    elif lang == "it":
        templates = {
            "identify": f"È {title}, {facts['kind']}.",
            "artist": f"{artist} realizzò quest'opera.",
            "date": f"Quest'opera fu realizzata {date}.",
        }
    elif lang == "zh":
        templates = {
            "identify": f"这是{title}，{facts['kind']}。",
            "artist": f"这件作品由{artist}创作。",
            "date": f"这件作品创作于{date}。",
        }
    else:
        templates = {
            "identify": f"This is {title}, {facts['kind']}.",
            "artist": f"{artist} made this work.",
            "date": f"This work was made {date}.",
        }
    if intent in templates:
        return templates[intent]
    return facts[_INTENT_FIELD[intent]]


def resolve_scripted_faq(
    question: str,
    *,
    artwork_id: str | None,
    language: str,
    profile: str,
    accessibility: Iterable[str] = (),
) -> ScriptedFaqAnswer | None:
    """Return a local FAQ answer or ``None`` for the deeper RAG/LLM path."""
    lang = normalize_language_code(language)
    intent = match_scripted_intent(question, lang)
    if intent is None:
        return None
    selected_artwork = _named_artwork(question) or artwork_id
    if selected_artwork not in _ARTWORKS:
        return ScriptedFaqAnswer(
            response=_CLARIFY_ARTWORK[lang],
            intent=intent,
            artwork_id=None,
        )
    record = _ARTWORKS[selected_artwork]
    facts = record["facts"][lang]
    response = _basic_answer(intent, record, facts, lang)
    if profile == "expert":
        response = f"{response} {facts['expert_note']}"
    visual_description = profile == "visual_impairment" or (
        "audio_description" in set(accessibility)
    )
    if visual_description and intent not in {"detail", "subject"}:
        response = f"{response} {facts['detail']}"
    if profile != "expert":
        follow_ups = (
            _EARLY_CHILD_FOLLOW_UPS if profile == "early_child" else _FOLLOW_UPS
        )
        response = f"{response} {follow_ups[lang][intent]}"
    if lang == "zh":
        response = response.translate(_TO_TRADITIONAL)
    return ScriptedFaqAnswer(
        response=response,
        intent=intent,
        artwork_id=selected_artwork,
        source_ids=record["sources"],
    )


def scripted_catalog_artwork_ids() -> frozenset[str]:
    """Expose coverage for validation without exposing mutable catalogue data."""
    return frozenset(_ARTWORKS)
