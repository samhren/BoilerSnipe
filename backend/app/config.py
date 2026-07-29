from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator


DEFAULT_INVENTORY_SUBJECTS = [
    "AAE", "AAS", "ABE", "ACCT", "AD", "AFT", "AGEC", "AGR", "AGRY", "AMST", "ANSC", "ANTH",
    "ARAB", "ARCH", "ASAM", "ASEC", "ASL", "ASM", "ASTR", "AT", "BAND", "BCHM", "BIOL",
    "BME", "BMS", "BTNY", "CAND", "CCE", "CDIS", "CE", "CEM", "CGT", "CHE", "CHM", "CHNS",
    "CIT", "CLCS", "CLPH", "CM", "CMGT", "CMPL", "CNIT", "COM", "CPB", "CS", "CSCI",
    "CSR", "DANC", "DCTC", "DSB", "EAPS", "ECE", "ECET", "ECON", "EDCI", "EDPS", "EDST", "EEE",
    "ENE", "ENGL", "ENGR", "ENGT", "ENTM", "ENTR", "EPCS", "EXPL", "FIN", "FLM", "FMGT", "FNR",
    "FR", "FS", "GEOL", "GEP", "GER", "GRAD", "GREK", "GS", "GSLA", "HDFS", "HEBR",
    "HER", "HETM", "HHS", "HIST", "HK", "HONR", "HORT", "HSCI", "HSOP", "HTM", "IBE", "IDE",
    "IDIS", "IE", "IET", "ILS", "IMPH", "INFO", "INT", "ITAL", "JPNS", "JWST", "KOR", "LA",
    "LALS", "LATN", "LC", "LING", "MA", "MATH", "MCMP", "ME", "MET", "MFET", "MGMT",
    "MIL", "MIS", "MKTG", "MSE", "MSL", "MSPE", "MUS", "NRES", "NS", "NUCL", "NUPH", "NUR", "NUTR", "OBHR",
    "OLS", "OPP", "PES", "PHIL", "PHPR", "PHRM", "PHSC", "PHST", "PHYS", "POL", "PSY", "PTGS",
    "PUBH", "QM", "REAL", "REG", "REL", "RPMP", "RUSS", "SA", "SCI", "SCLA", "SCOM", "SFS", "SLHS", "SOC", "SPAN",
    "STAT", "STRT", "SYS", "TCM", "TDM", "TECH", "THTR", "TLI", "VCS", "VIP", "VM", "WGSS"
]


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./purdue_courses.db"

    # JWT - no default, a missing SECRET_KEY must fail startup rather than
    # fall back to a value that is public in the repo
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google OAuth - expected audience for ID tokens sent to /api/auth/google
    GOOGLE_CLIENT_ID: Optional[str] = None

    # Resend Email
    RESEND_API_KEY: Optional[str] = None

    # Proxy (optional)
    PROXY_URL: Optional[str] = None

    # Identify our automated requests instead of impersonating a browser, so
    # Purdue IT can see who is making them and contact us directly.
    USER_AGENT: str = (
        "BoilerSnipe/1.0 (+https://boilersnipe.com/about; contact@boilersnipe.com)"
    )

    # Scraper settings
    INVENTORY_CRON: str = "0 2 * * 0"  # Weekly on Sunday at 2 AM
    SNIPER_INTERVAL_MINUTES: float = 5
    CURRENT_TERM_CODE: str = "202710"
    CURRENT_TERM_NAME: str = "Fall 2026"
    INVENTORY_SUBJECTS: str = ",".join(DEFAULT_INVENTORY_SUBJECTS)
    RUN_STARTUP_INVENTORY_ONCE: bool = True
    ENABLE_RECURRING_INVENTORY: bool = False

    # CORS
    FRONTEND_URL: Optional[str] = None
    
    # Security - use "*" when behind a reverse proxy
    ALLOWED_HOSTS: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def inventory_subject_list(self) -> List[str]:
        return [subject.strip().upper() for subject in self.INVENTORY_SUBJECTS.split(",") if subject.strip()]


settings = Settings()
