from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    Boolean, DateTime, Float, ForeignKey, Date
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import bcrypt
import os

Base = declarative_base()


class Utilizator(Base):
    __tablename__ = "utilizator"

    id_utilizator = Column(Integer, primary_key=True, autoincrement=True)
    nume_utilizator = Column(String(100), nullable=False, unique=True)
    parola = Column(Text, nullable=False)
    nume = Column(String(100))
    prenume = Column(String(100))
    varsta = Column(Integer)
    adresa = Column(Text)
    nr_telefon = Column(String(20))

    # ROLURI ACTUALIZATE: utilizator / admin / developer
    rol = Column(String(50), default="utilizator")

    istoric_medical = Column(Integer, ForeignKey("istoric_medical.id_medical"), nullable=True)
    persoana_contact = Column(Integer, ForeignKey("persoana_contact.id_contact"), nullable=True)
    istoric_logare = Column(Integer, ForeignKey("istoric_logare.id_logare"), nullable=True)
    creat_la = Column(DateTime, default=datetime.now)

    # Relatii (nemodificate)
    istorice_medicale = relationship("IstoricMedical", foreign_keys="IstoricMedical.id_utilizator",
                                     back_populates="utilizator")
    persoane_contact = relationship("PersoanaContact", foreign_keys="PersoanaContact.id_utilizator",
                                    back_populates="utilizator")
    logari = relationship("IstoricLogare", foreign_keys="IstoricLogare.id_utilizator", back_populates="utilizator")

    site_rules = relationship(
        "SiteRule",
        back_populates="utilizator",
        lazy="dynamic")
    activity_logs = relationship(
        "ActivityLog",
        back_populates="utilizator",
        lazy="dynamic")
    daily_stats = relationship(
        "DailyStats",
        back_populates="utilizator",
        lazy="dynamic")

    def set_parola(self, parola_text):
        """Cripteaza parola cu bcrypt"""
        salt = bcrypt.gensalt()
        self.parola = bcrypt.hashpw(parola_text.encode("utf-8"), salt).decode("utf-8")

    def verifica_parola(self, parola_text):
        """Verifica parola introdusa"""
        return bcrypt.checkpw(parola_text.encode("utf-8"), self.parola.encode("utf-8"))

    def __repr__(self):
        return f"<Utilizator {self.nume_utilizator} ({self.rol})>"


class IstoricMedical(Base):
    __tablename__ = "istoric_medical"

    id_medical = Column(Integer, primary_key=True, autoincrement=True)
    id_utilizator = Column(Integer, ForeignKey("utilizator.id_utilizator"), nullable=False)
    data_observatie = Column(DateTime, default=datetime.now)
    simptom = Column(Text)
    sugestii = Column(Text)
    urgenta = Column(Boolean, default=False)
    observatii = Column(Text)

    utilizator = relationship("Utilizator", foreign_keys=[id_utilizator], back_populates="istorice_medicale")


class PersoanaContact(Base):
    __tablename__ = "persoana_contact"

    id_contact = Column(Integer, primary_key=True, autoincrement=True)
    id_utilizator = Column(Integer, ForeignKey("utilizator.id_utilizator"), nullable=False)
    cheie_pushbullet = Column(Text)
    nr_telefon = Column(String(20))
    adresa = Column(Text)
    nume = Column(String(100))
    prenume = Column(String(100))
    observatii = Column(Text)

    utilizator = relationship("Utilizator", foreign_keys=[id_utilizator], back_populates="persoane_contact")


class IstoricLogare(Base):
    __tablename__ = "istoric_logare"

    id_logare = Column(Integer, primary_key=True, autoincrement=True)
    id_utilizator = Column(Integer, ForeignKey("utilizator.id_utilizator"), nullable=False)
    adresa_ip = Column(String(45))
    data_ora = Column(DateTime, default=datetime.now)
    durata = Column(Float)
    observatii = Column(Text)

    utilizator = relationship("Utilizator", foreign_keys=[id_utilizator], back_populates="logari")

# ── Monitorizare activitate ───────────────────────────────────────────────────

class SiteRule(Base):
    """Reguli pentru site-uri — interzis/limitat."""
    __tablename__ = "site_rules"

    id            = Column(Integer, primary_key=True)
    id_utilizator = Column(
        Integer,
        ForeignKey("utilizator.id_utilizator"),
        nullable=False)
    domeniu       = Column(String, nullable=False)
    tip           = Column(
        String, nullable=False,
        default="blocat")
    # tip: "blocat" | "limitat" | "permis"
    limita_minute = Column(
        Integer, nullable=True)
    # NULL daca tip != "limitat"
    activ         = Column(
        Boolean, default=True)
    creat_la      = Column(
        DateTime,
        default=datetime.utcnow)

    utilizator = relationship(
        "Utilizator",
        back_populates="site_rules")


class ActivityLog(Base):
    """Log activitate browser + desktop."""
    __tablename__ = "activity_log"

    id            = Column(
        Integer, primary_key=True)
    id_utilizator = Column(
        Integer,
        ForeignKey("utilizator.id_utilizator"),
        nullable=False)
    tip           = Column(
        String, nullable=False)
    # tip: "site" | "aplicatie"
    nume          = Column(String, nullable=False)
    domeniu       = Column(
        String, nullable=True)
    inceput_la    = Column(
        DateTime, nullable=False)
    sfarsit_la    = Column(
        DateTime, nullable=True)
    durata_secunde = Column(
        Integer, nullable=True)
    blocat        = Column(
        Boolean, default=False)

    utilizator = relationship(
        "Utilizator",
        back_populates="activity_logs")


class DailyStats(Base):
    """Statistici zilnice agregate."""
    __tablename__ = "daily_stats"

    id               = Column(
        Integer, primary_key=True)
    id_utilizator    = Column(
        Integer,
        ForeignKey("utilizator.id_utilizator"),
        nullable=False)
    data             = Column(
        Date, nullable=False)
    timp_total_sec   = Column(
        Integer, default=0)
    timp_blocat_sec  = Column(
        Integer, default=0)
    site_uri_vizitate = Column(
        Integer, default=0)
    sesiuni_pomodoro = Column(
        Integer, default=0)
    pauze_luate      = Column(
        Integer, default=0)
    litri_apa        = Column(
        Float, default=0.0)

    utilizator = relationship(
        "Utilizator",
        back_populates="daily_stats")


# ─── Initializare DB ─────────────────────────────────────────────────────────

def get_db_path():
    db_dir = os.path.join(os.path.expanduser("~"), ".coffee_axl")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "coffee_axl.db")


def _migrate_add_columns(engine):
    """Adauga coloane noi in tabele existente (migrare automata)."""
    migrations = [
        ("daily_stats",   "litri_apa",       "REAL DEFAULT 0.0"),
        ("daily_stats",   "sesiuni_pomodoro", "INTEGER DEFAULT 0"),
    ]
    try:
        with engine.connect() as conn:
            for table, column, col_def in migrations:
                try:
                    conn.execute(
                        __import__("sqlalchemy").text(
                            f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
                        )
                    )
                    print(f"[DB] Migrare: {table}.{column} adaugat.")
                except Exception:
                    pass  # coloana exista deja
    except Exception as e:
        print(f"[DB] Migration err: {e}")


def init_db():
    """Creeaza baza de date si tabelele daca nu exista"""
    engine = create_engine(f"sqlite:///{get_db_path()}", echo=False)
    Base.metadata.create_all(engine)

    # Migrare automata: adauga coloane noi daca lipsesc
    _migrate_add_columns(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Verificam daca baza de date este goala pentru a popula rolurile cerute
    if session.query(Utilizator).count() == 0:
        # 1. Cont ADMIN
        admin = Utilizator(
            nume_utilizator="admin",
            nume="Nu",
            prenume="zic",
            rol="admin"
        )
        admin.set_parola("admin123")
        session.add(admin)

        # 2. Cont DEVELOPER (pentru Debug)
        developer = Utilizator(
            nume_utilizator="dev",
            nume="Petrea",
            prenume="Maria",
            rol="developer"
        )
        developer.set_parola("dev123")
        session.add(developer)

        # 3. Cont UTILIZATOR (Standard)
        utilizator = Utilizator(
            nume_utilizator="user",
            nume="Popescu",
            prenume="Ion",
            varsta=30,
            rol="utilizator"
        )
        utilizator.set_parola("user123")
        session.add(utilizator)

        session.commit()
        print("[DB] Initializat cu rolurile: admin, developer, utilizator.")

    session.close()
    return engine


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()