"""Static Baku bus route data used by the simulator.

Stop names are real Baku metro stations / landmarks; coordinates are approximate.
Stop sequences are simplified for the demo and are not official BakuBus timetables.
"""
from app.models import Route, Stop


def _stops(*items: tuple[str, float, float]) -> list[Stop]:
    return [Stop(name=n, lat=lat, lon=lon) for n, lat, lon in items]


ROUTES: list[Route] = [
    Route(id="1", name="İnşaatçılar – Xətai", stops=_stops(
        ("İnşaatçılar m.", 40.3906, 49.8031),
        ("Elmlər Akademiyası m.", 40.3752, 49.8146),
        ("Nizami m.", 40.3797, 49.8300),
        ("28 May m.", 40.3797, 49.8486),
        ("Azadlıq meydanı", 40.3768, 49.8573),
        ("Xətai m.", 40.3836, 49.8724),
    )),
    Route(id="5", name="İçərişəhər – Ulduz", stops=_stops(
        ("İçərişəhər m.", 40.3660, 49.8317),
        ("Fəvvarələr meydanı", 40.3709, 49.8370),
        ("Sahil m.", 40.3717, 49.8443),
        ("28 May m.", 40.3797, 49.8486),
        ("Gənclik m.", 40.4005, 49.8515),
        ("Nərimanov m.", 40.4029, 49.8706),
        ("Ulduz m.", 40.4144, 49.8916),
    )),
    Route(id="65", name="20 Yanvar – Dərnəgül", stops=_stops(
        ("20 Yanvar m.", 40.4040, 49.8085),
        ("Memar Əcəmi m.", 40.4116, 49.8150),
        ("Nəsimi m.", 40.4243, 49.8253),
        ("Azadlıq prospekti m.", 40.4256, 49.8435),
        ("Dərnəgül m.", 40.4253, 49.8622),
    )),
    Route(id="88", name="Koroğlu – Həzi Aslanov", stops=_stops(
        ("Koroğlu m.", 40.4210, 49.9180),
        ("Qara Qarayev m.", 40.4176, 49.9339),
        ("Neftçilər m.", 40.4107, 49.9433),
        ("Xalqlar Dostluğu m.", 40.3975, 49.9524),
        ("Əhmədli m.", 40.3854, 49.9539),
        ("Həzi Aslanov m.", 40.3727, 49.9535),
    )),
]
