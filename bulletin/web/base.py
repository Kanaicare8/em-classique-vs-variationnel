"""
Base de l'outil (SQLAlchemy) : comptes, relevés saisis, extraits du PAM chargés, journal des actions.

DATABASE_URL : Postgres en ligne (Railway la fournit) ; à défaut, SQLite dans bulletin/instance/outil.db.
Un relevé saisi par un agent est « en attente » jusqu'à sa validation par un analyste ; seuls les relevés validés
entrent dans le bulletin. Les relevés saisis par un analyste ou un administrateur sont validés d'office.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, create_engine, func,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

ROLES = {"admin": "Administrateur", "analyste": "Analyste", "agent": "Agent de collecte"}
STATUTS = {"en_attente": "en attente", "valide": "validé", "rejete": "rejeté"}


def _url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        dossier = Path(__file__).resolve().parent.parent / "instance"
        dossier.mkdir(exist_ok=True)
        return f"sqlite:///{dossier / 'outil.db'}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url


MOTEUR = create_engine(_url(), pool_pre_ping=True)


def maintenant():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    nom: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    organisation: Mapped[str | None] = mapped_column(String(200))
    mot_de_passe: Mapped[str] = mapped_column(String(300))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    def verifier(self, mdp: str) -> bool:
        return self.actif and check_password_hash(self.mot_de_passe, mdp)


class Releve(Base):
    __tablename__ = "releves"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marche: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(200))
    denree: Mapped[str] = mapped_column(String(200))          # libellé du PAM (ex. « Maize (white) »)
    mois: Mapped[str] = mapped_column(String(7))               # aaaa-mm
    prix: Mapped[float] = mapped_column(Float)                 # XAF/kg, prix de détail
    commentaire: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(20), default="en_attente")
    saisi_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    saisi_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    valide_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime)
    saisi_par = relationship(Utilisateur, foreign_keys=[saisi_par_id])
    valide_par = relationship(Utilisateur, foreign_keys=[valide_par_id])


class Extrait(Base):
    __tablename__ = "extraits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    lignes: Mapped[int] = mapped_column(Integer)
    debut: Mapped[str] = mapped_column(String(7))
    fin: Mapped[str] = mapped_column(String(7))
    origine: Mapped[str] = mapped_column(String(300))          # URL HDX ou nom du fichier déposé
    charge_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    charge_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    actif: Mapped[bool] = mapped_column(Boolean, default=False)


class Journal(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quand: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str | None] = mapped_column(Text)
    utilisateur = relationship(Utilisateur)


def session() -> Session:
    return Session(MOTEUR, expire_on_commit=False)


def initialiser():
    """Crée les tables ; crée le premier administrateur depuis OUTIL_ADMIN_EMAIL et OUTIL_ADMIN_MOT_DE_PASSE si la base
    n'a encore aucun compte."""
    Base.metadata.create_all(MOTEUR)
    with session() as s:
        if s.scalar(select(func.count(Utilisateur.id))):
            return
        email, mdp = os.environ.get("OUTIL_ADMIN_EMAIL"), os.environ.get("OUTIL_ADMIN_MOT_DE_PASSE")
        if email and mdp:
            s.add(Utilisateur(email=email.lower(), nom="Administrateur", role="admin", mot_de_passe=hacher(mdp)))
            s.add(Journal(action="compte créé", detail=f"premier administrateur {email}"))
            s.commit()


def hacher(mdp: str) -> str:
    return generate_password_hash(mdp, method="pbkdf2:sha256:600000")


def journaliser(s: Session, utilisateur_id, action, detail=None):
    s.add(Journal(utilisateur_id=utilisateur_id, action=action, detail=detail))


def releves_valides():
    with session() as s:
        return [{"marche": r.marche, "region": r.region, "denree": r.denree, "mois": r.mois, "prix": r.prix}
                for r in s.scalars(select(Releve).where(Releve.statut == "valide"))]


def empreinte_releves():
    """Change dès qu'un relevé est ajouté, validé ou rejeté : sert de clé de cache aux calculs."""
    with session() as s:
        return (s.scalar(select(func.count(Releve.id)).where(Releve.statut == "valide")),
                s.scalar(select(func.max(Releve.valide_le))))


def extrait_actif():
    with session() as s:
        return s.scalar(select(Extrait).where(Extrait.actif))
