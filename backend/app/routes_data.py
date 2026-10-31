"""Static Baku bus network used by the simulator.

SIMPLIFIED DEMO DATA: route numbers and stop names are real Baku ones, but the
coordinates are approximate and the stop sequences are simplified; they are not
official BakuBus timetables or exact route paths.

Stops are defined once in STOP_DATA and referenced by id from ROUTE_DATA, so a stop
shared by several routes (e.g. "28-may") is the same stop everywhere.
"""
from app.models import Route, Stop

# (id, display name, lat, lon), grouped by district.
STOP_DATA: list[tuple[str, str, float, float]] = [
    # Səbail / city centre
    ("icerisheher", "İçərişəhər m.", 40.3660, 49.8317),
    ("fevvareler", "Fəvvarələr meydanı", 40.3709, 49.8370),
    ("sahil", "Sahil m.", 40.3717, 49.8443),
    ("azadliq-meydani", "Azadlıq meydanı", 40.3768, 49.8573),
    ("filarmoniya", "Filarmoniya", 40.3647, 49.8345),
    ("kukla-teatri", "Kukla Teatrı", 40.3672, 49.8400),
    ("port-baku", "Port Baku", 40.3770, 49.8640),
    ("dagustu-park", "Dağüstü park", 40.3590, 49.8290),
    ("bayil", "Bayıl", 40.3480, 49.8310),
    ("badamdar", "Badamdar", 40.3330, 49.8120),
    ("sixov", "Şıxov", 40.3170, 49.8090),
    ("bibiheybet", "Bibiheybət məscidi", 40.3060, 49.8240),
    ("lokbatan", "Lökbatan", 40.3270, 49.7300),
    # Nəsimi
    ("28-may", "28 May m.", 40.3797, 49.8486),
    ("nizami", "Nizami m.", 40.3797, 49.8300),
    ("nesimi-bazari", "Nəsimi bazarı", 40.3860, 49.8295),
    ("samed-vurgun", "Səməd Vurğun bağı", 40.3770, 49.8410),
    ("unec", "İqtisad Universiteti", 40.3828, 49.8420),
    ("fuzuli-meydani", "Füzuli meydanı", 40.3738, 49.8378),
    ("tibb-universiteti", "Tibb Universiteti", 40.3860, 49.8460),
    ("respublika-stadionu", "Respublika stadionu", 40.3985, 49.8555),
    ("genclik", "Gənclik m.", 40.4005, 49.8515),
    # Yasamal
    ("elmler", "Elmlər Akademiyası m.", 40.3752, 49.8146),
    ("bdu", "Bakı Dövlət Universiteti", 40.3730, 49.8110),
    ("huseyn-cavid", "Hüseyn Cavid parkı", 40.3800, 49.8090),
    ("insaatcilar", "İnşaatçılar m.", 40.3906, 49.8031),
    ("yeni-yasamal", "Yeni Yasamal", 40.3950, 49.7880),
    ("metbuat", "Mətbuat prospekti", 40.3815, 49.7990),
    ("serifzade", "Şərifzadə küçəsi", 40.3870, 49.8120),
    ("20-yanvar", "20 Yanvar m.", 40.4040, 49.8085),
    ("yasamal-bazari", "Yasamal bazarı", 40.3905, 49.8190),
    ("memar-ecemi", "Memar Əcəmi m.", 40.4116, 49.8150),
    ("8-noyabr", "8 Noyabr m.", 40.4025, 49.8205),
    # Binəqədi (and Abşeron suburbs to the north-west)
    ("nesimi", "Nəsimi m.", 40.4243, 49.8253),
    ("azadliq-prospekti", "Azadlıq prospekti m.", 40.4256, 49.8435),
    ("dernegul", "Dərnəgül m.", 40.4253, 49.8622),
    ("avtovagzal", "Avtovağzal m.", 40.4210, 49.7950),
    ("xocesen", "Xocəsən m.", 40.4235, 49.7810),
    ("7-mkr", "7-ci mikrorayon", 40.4180, 49.8240),
    ("8-mkr", "8-ci mikrorayon", 40.4300, 49.8180),
    ("9-mkr", "9-cu mikrorayon", 40.4330, 49.8050),
    ("resulzade", "M.Ə. Rəsulzadə qəsəbəsi", 40.4440, 49.8380),
    ("bineqedi-qesebesi", "Binəqədi qəsəbəsi", 40.4650, 49.8260),
    ("bilecari", "Biləcəri", 40.4320, 49.7650),
    ("sulutepe", "Sulutəpə", 40.4440, 49.7380),
    ("xirdalan", "Xırdalan", 40.4480, 49.7550),
    ("masazir", "Masazır", 40.4870, 49.7600),
    ("mehdiabad", "Mehdiabad", 40.4930, 49.8600),
    # Nərimanov
    ("nerimanov", "Nərimanov m.", 40.4029, 49.8706),
    ("heydar-aliyev-merkezi", "Heydər Əliyev Mərkəzi", 40.3958, 49.8678),
    ("ataturk-parki", "Atatürk parkı", 40.4060, 49.8640),
    ("montin", "Montin", 40.4095, 49.8775),
    ("bakmil", "Bakmil m.", 40.4180, 49.8790),
    ("ulduz", "Ulduz m.", 40.4144, 49.8916),
    ("boyuksor", "Böyükşor gölü", 40.4270, 49.8990),
    ("olimpiya", "Olimpiya stadionu", 40.4302, 49.9196),
    ("tebriz-kucesi", "Təbriz küçəsi", 40.4000, 49.8790),
    # Xətai
    ("xetai", "Xətai m.", 40.3836, 49.8724),
    ("ag-seher", "Ağ Şəhər", 40.3785, 49.8830),
    ("nobel", "Nobel prospekti", 40.3810, 49.8930),
    ("babek", "Babək prospekti", 40.3940, 49.9050),
    ("ehmedli", "Əhmədli m.", 40.3854, 49.9539),
    ("hezi-aslanov", "Həzi Aslanov m.", 40.3727, 49.9535),
    ("kohne-gunesli", "Köhnə Günəşli", 40.3700, 49.9420),
    ("yeni-ehmedli", "Yeni Əhmədli", 40.3900, 49.9650),
    # Nizami
    ("koroglu", "Koroğlu m.", 40.4210, 49.9180),
    ("qara-qarayev", "Qara Qarayev m.", 40.4176, 49.9339),
    ("neftciler", "Neftçilər m.", 40.4107, 49.9433),
    ("xalqlar-dostlugu", "Xalqlar Dostluğu m.", 40.3975, 49.9524),
    ("kesle", "Keşlə", 40.4060, 49.9080),
    ("8-km", "8-ci kilometr bazarı", 40.4020, 49.9420),
    # Sabunçu
    ("bakixanov", "Bakıxanov qəsəbəsi", 40.4270, 49.9560),
    ("sabuncu", "Sabunçu qəsəbəsi", 40.4420, 49.9480),
    ("balaxani", "Balaxanı", 40.4620, 49.9230),
    ("zabrat", "Zabrat", 40.4880, 49.9440),
    ("ramana", "Ramana", 40.4600, 49.9780),
    ("mastaga", "Maştağa", 40.5320, 49.9950),
    ("kurdexani", "Kürdəxanı", 40.5500, 49.9250),
    # Suraxanı (and the airport road)
    ("qaracuxur", "Qaraçuxur", 40.3970, 49.9820),
    ("yeni-gunesli", "Yeni Günəşli", 40.3800, 49.9650),
    ("zig", "Zığ", 40.3640, 49.9830),
    ("emircan", "Əmircan", 40.4260, 49.9880),
    ("dede-qorqud", "Dədə Qorqud qəsəbəsi", 40.4100, 49.9930),
    ("suraxani", "Suraxanı qəsəbəsi", 40.4180, 50.0070),
    ("yeni-suraxani", "Yeni Suraxanı", 40.4310, 50.0330),
    ("hovsan", "Hövsan", 40.3750, 50.0640),
    ("bulbule", "Bülbülə", 40.4420, 50.0000),
    ("bine", "Binə", 40.4530, 50.0750),
    ("hava-limani", "Heydər Əliyev Hava Limanı", 40.4675, 50.0467),
]

# (route number, stop ids in travel order). Route name = "first stop – last stop".
ROUTE_DATA: list[tuple[str, list[str]]] = [
    ("1", ["yeni-yasamal", "insaatcilar", "huseyn-cavid", "elmler", "nizami", "samed-vurgun",
           "28-may", "azadliq-meydani", "port-baku", "xetai", "ag-seher"]),
    ("2", ["sixov", "badamdar", "bayil", "dagustu-park", "filarmoniya", "icerisheher",
           "fevvareler", "nizami", "nesimi-bazari", "28-may", "genclik"]),
    ("3", ["lokbatan", "bibiheybet", "sixov", "badamdar", "bayil", "kukla-teatri", "sahil", "28-may"]),
    ("5", ["icerisheher", "fevvareler", "sahil", "28-may", "tibb-universiteti", "genclik",
           "ataturk-parki", "nerimanov", "montin", "ulduz"]),
    ("8", ["avtovagzal", "9-mkr", "20-yanvar", "insaatcilar", "metbuat", "bdu", "elmler",
           "fuzuli-meydani", "fevvareler", "sahil"]),
    ("11", ["xirdalan", "bilecari", "xocesen", "avtovagzal", "20-yanvar", "8-noyabr",
            "yasamal-bazari", "nizami", "unec", "28-may"]),
    ("13", ["sulutepe", "xirdalan", "masazir", "9-mkr", "8-mkr", "7-mkr", "nesimi",
            "memar-ecemi", "8-noyabr", "serifzade"]),
    ("14", ["bineqedi-qesebesi", "resulzade", "azadliq-prospekti", "nesimi", "7-mkr", "memar-ecemi",
            "8-noyabr", "nesimi-bazari", "unec", "samed-vurgun", "sahil"]),
    ("17", ["mehdiabad", "bineqedi-qesebesi", "resulzade", "azadliq-prospekti", "dernegul", "bakmil",
            "montin", "nerimanov", "genclik", "respublika-stadionu"]),
    ("18", ["dernegul", "azadliq-prospekti", "nesimi", "memar-ecemi", "20-yanvar", "insaatcilar",
            "elmler", "bdu", "icerisheher", "fevvareler"]),
    ("20", ["ulduz", "bakmil", "montin", "tebriz-kucesi", "heydar-aliyev-merkezi", "xetai",
            "azadliq-meydani", "port-baku", "ag-seher", "nobel"]),
    ("21", ["genclik", "respublika-stadionu", "heydar-aliyev-merkezi", "xetai", "ag-seher", "nobel",
            "babek", "xalqlar-dostlugu", "ehmedli", "hezi-aslanov"]),
    ("24", ["28-may", "azadliq-meydani", "xetai", "babek", "kesle", "8-km", "xalqlar-dostlugu",
            "yeni-ehmedli", "qaracuxur"]),
    ("30", ["koroglu", "qara-qarayev", "bakixanov", "sabuncu", "balaxani", "zabrat", "kurdexani", "mastaga"]),
    ("35", ["ulduz", "boyuksor", "koroglu", "olimpiya", "bakixanov", "emircan", "bulbule", "ramana", "zabrat"]),
    ("46", ["qara-qarayev", "neftciler", "8-km", "xalqlar-dostlugu", "yeni-ehmedli", "yeni-gunesli",
            "zig", "hovsan"]),
    ("49", ["koroglu", "qara-qarayev", "neftciler", "qaracuxur", "dede-qorqud", "emircan", "suraxani",
            "yeni-suraxani", "bine"]),
    ("53", ["hezi-aslanov", "kohne-gunesli", "yeni-gunesli", "qaracuxur", "dede-qorqud", "suraxani",
            "yeni-suraxani", "bine", "hava-limani"]),
    ("61", ["28-may", "sahil", "kukla-teatri", "filarmoniya", "dagustu-park", "bayil", "badamdar", "sixov"]),
    ("65", ["20-yanvar", "memar-ecemi", "7-mkr", "nesimi", "8-mkr", "resulzade", "azadliq-prospekti",
            "dernegul"]),
    ("67", ["yeni-yasamal", "metbuat", "huseyn-cavid", "serifzade", "yasamal-bazari", "nizami",
            "nesimi-bazari", "tibb-universiteti", "genclik", "ataturk-parki", "nerimanov"]),
    ("70", ["azadliq-meydani", "port-baku", "ag-seher", "nobel", "babek", "kesle", "koroglu", "olimpiya",
            "bakixanov", "sabuncu"]),
    ("77", ["xocesen", "avtovagzal", "9-mkr", "yeni-yasamal", "insaatcilar", "metbuat", "huseyn-cavid",
            "bdu", "elmler"]),
    ("88", ["koroglu", "qara-qarayev", "neftciler", "8-km", "xalqlar-dostlugu", "ehmedli",
            "kohne-gunesli", "hezi-aslanov"]),
    ("H1", ["28-may", "genclik", "nerimanov", "ulduz", "koroglu", "qara-qarayev", "bakixanov",
            "emircan", "bulbule", "hava-limani"]),
]

STOPS: dict[str, Stop] = {
    stop_id: Stop(id=stop_id, name=name, lat=lat, lon=lon) for stop_id, name, lat, lon in STOP_DATA
}


def _build_route(route_id: str, stop_ids: list[str]) -> Route:
    stops = [STOPS[stop_id] for stop_id in stop_ids]
    return Route(id=route_id, name=f"{stops[0].name} – {stops[-1].name}", stops=stops)


ROUTES: list[Route] = [_build_route(route_id, stop_ids) for route_id, stop_ids in ROUTE_DATA]
