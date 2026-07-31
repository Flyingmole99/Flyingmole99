"""Lastgang – die zentrale Zeitreihen-Datenstruktur.

Bewusst ohne numpy/pandas gehalten: der Rechenkern soll überall laufen und
sich leicht in andere Umgebungen (z. B. eine C#/Revit-Seite) portieren lassen.
Für 8760 bzw. 35040 Werte ist reines Python schnell genug.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Lastgang:
    """Leistungszeitreihe in kW mit äquidistanter Auflösung.

    Ein Wert beschreibt die *mittlere Leistung* im jeweiligen Intervall.
    Damit gilt: Energie = Wert [kW] * Intervalldauer [h].
    """

    werte_kw: tuple[float, ...]
    aufloesung_min: int = 60
    bezeichnung: str = ""
    meta: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.werte_kw:
            raise ValueError("Lastgang ohne Werte")
        if self.aufloesung_min <= 0 or 60 % self.aufloesung_min and self.aufloesung_min % 60:
            raise ValueError(f"Unplausible Auflösung: {self.aufloesung_min} min")
        object.__setattr__(self, "werte_kw", tuple(float(w) for w in self.werte_kw))

    # ---------------------------------------------------------------- Basis

    @property
    def dt_h(self) -> float:
        """Intervalldauer in Stunden."""
        return self.aufloesung_min / 60.0

    @property
    def anzahl(self) -> int:
        return len(self.werte_kw)

    @property
    def abgedeckte_stunden(self) -> float:
        return self.anzahl * self.dt_h

    def summe_kwh(self) -> float:
        return sum(self.werte_kw) * self.dt_h

    def spitzenlast_kw(self) -> float:
        return max(self.werte_kw)

    def grundlast_kw(self) -> float:
        return min(self.werte_kw)

    def mittelwert_kw(self) -> float:
        return sum(self.werte_kw) / self.anzahl

    def benutzungsdauer_h(self) -> float:
        """Jahresbenutzungsdauer = Jahresarbeit / Jahresspitze."""
        spitze = self.spitzenlast_kw()
        return self.summe_kwh() / spitze if spitze > 0 else 0.0

    # ------------------------------------------------------------ Ableitung

    def mit_werten(self, werte_kw, bezeichnung: str | None = None) -> "Lastgang":
        return replace(
            self,
            werte_kw=tuple(werte_kw),
            bezeichnung=bezeichnung if bezeichnung is not None else self.bezeichnung,
        )

    def skaliert_auf(self, jahresarbeit_kwh: float) -> "Lastgang":
        """Profilform beibehalten, Jahressumme auf Zielwert bringen."""
        ist = self.summe_kwh()
        if ist <= 0:
            raise ValueError("Lastgang mit Jahressumme 0 kann nicht skaliert werden")
        f = jahresarbeit_kwh / ist
        return self.mit_werten(w * f for w in self.werte_kw)

    def skaliert(self, faktor: float) -> "Lastgang":
        return self.mit_werten(w * faktor for w in self.werte_kw)

    def begrenzt_auf(self, p_max_kw: float) -> tuple["Lastgang", "Lastgang"]:
        """Aufteilung in (gedeckter Anteil bis p_max, Überschuss darüber)."""
        unten = [min(w, p_max_kw) for w in self.werte_kw]
        oben = [max(0.0, w - p_max_kw) for w in self.werte_kw]
        return self.mit_werten(unten), self.mit_werten(oben)

    def dauerlinie(self) -> tuple[float, ...]:
        return tuple(sorted(self.werte_kw, reverse=True))

    def aggregiert_stuendlich(self) -> "Lastgang":
        """Auf 1 h mitteln (nur für Auflösungen < 60 min sinnvoll)."""
        if self.aufloesung_min >= 60:
            return self
        n = 60 // self.aufloesung_min
        werte = [
            sum(self.werte_kw[i : i + n]) / n for i in range(0, self.anzahl - self.anzahl % n, n)
        ]
        return Lastgang(tuple(werte), 60, self.bezeichnung, dict(self.meta))

    def plus(self, anderer: "Lastgang") -> "Lastgang":
        self._pruefe_kompatibel(anderer)
        return self.mit_werten(a + b for a, b in zip(self.werte_kw, anderer.werte_kw))

    def minus(self, anderer: "Lastgang") -> "Lastgang":
        self._pruefe_kompatibel(anderer)
        return self.mit_werten(a - b for a, b in zip(self.werte_kw, anderer.werte_kw))

    def _pruefe_kompatibel(self, anderer: "Lastgang") -> None:
        if self.anzahl != anderer.anzahl or self.aufloesung_min != anderer.aufloesung_min:
            raise ValueError("Lastgänge mit unterschiedlichem Zeitraster")

    # ----------------------------------------------------------- Konstruktion

    @classmethod
    def konstant(cls, leistung_kw: float, aufloesung_min: int = 60, bezeichnung: str = "") -> "Lastgang":
        n = int(8760 * 60 / aufloesung_min)
        return cls(tuple([leistung_kw] * n), aufloesung_min, bezeichnung)

    @classmethod
    def null(cls, aufloesung_min: int = 60, bezeichnung: str = "") -> "Lastgang":
        return cls.konstant(0.0, aufloesung_min, bezeichnung)
