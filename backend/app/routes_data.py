"""Static Baku bus route data used by the simulator.

Stop names are real Baku metro stations / landmarks; coordinates are approximate.
Stop sequences are simplified for the demo and are not official BakuBus timetables.
A stop shared by several routes uses the same id (e.g. "28-may" on routes 1 and 5).
"""
from app.models import Route, Stop


def _stops(*items: tuple[str, str, float, float]) -> list[Stop]:
    return [Stop(id=i, name=n, lat=lat, lon=lon) for i, n, lat, lon in items]


ROUTES: list[Route] = [
    Route(id="1", name="İnşaatçılar – Xətai", stops=_stops(
        ("insaatcilar", "İnşaatçılar m.", 40.3906, 49.8031),
        ("elmler", "Elmlər Akademiyası m.", 40.3752, 49.8146),
        ("nizami", "Nizami m.", 40.3797, 49.8300),
        ("28-may", "28 May m.", 40.3797, 49.8486),
        ("azadliq-meydani", "Azadlıq meydanı", 40.3768, 49.8573),
        ("xetai", "Xətai m.", 40.3836, 49.8724),
    )),
    Route(id="5", name="İçərişəhər – Ulduz", stops=_stops(
        ("icerisheher", "İçərişəhər m.", 40.3660, 49.8317),
        ("fevvareler", "Fəvvarələr meydanı", 40.3709, 49.8370),
        ("sahil", "Sahil m.", 40.3717, 49.8443),
        ("28-may", "28 May m.", 40.3797, 49.8486),
        ("genclik", "Gənclik m.", 40.4005, 49.8515),
        ("nerimanov", "Nərimanov m.", 40.4029, 49.8706),
        ("ulduz", "Ulduz m.", 40.4144, 49.8916),
    )),
    Route(id="65", name="20 Yanvar – Dərnəgül", stops=_stops(
        ("20-yanvar", "20 Yanvar m.", 40.4040, 49.8085),
        ("memar-ecemi", "Memar Əcəmi m.", 40.4116, 49.8150),
        ("nesimi", "Nəsimi m.", 40.4243, 49.8253),
        ("azadliq-prospekti", "Azadlıq prospekti m.", 40.4256, 49.8435),
        ("dernegul", "Dərnəgül m.", 40.4253, 49.8622),
    )),
    Route(id="88", name="Koroğlu – Həzi Aslanov", stops=_stops(
        ("koroglu", "Koroğlu m.", 40.4210, 49.9180),
        ("qara-qarayev", "Qara Qarayev m.", 40.4176, 49.9339),
        ("neftciler", "Neftçilər m.", 40.4107, 49.9433),
        ("xalqlar-dostlugu", "Xalqlar Dostluğu m.", 40.3975, 49.9524),
        ("ehmedli", "Əhmədli m.", 40.3854, 49.9539),
        ("hezi-aslanov", "Həzi Aslanov m.", 40.3727, 49.9535),
    )),
]
