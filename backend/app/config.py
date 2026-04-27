from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator


DEFAULT_INVENTORY_SUBJECTS = [
    "AAE", "AAS", "ABE", "AD", "AFT", "AGEC", "AGR", "AGRY", "AMST", "ANSC", "ANTH",
    "ARAB", "ARCH", "ASAM", "ASEC", "ASL", "ASM", "ASTR", "AT", "BAND", "BCHM", "BIOL",
    "BME", "BMS", "BTNY", "CAND", "CDIS", "CE", "CEM", "CGT", "CHE", "CHM", "CHNS",
    "CIT", "CLCS", "CLPH", "CM", "CMGT", "CMPL", "CNIT", "COM", "CPB", "CS", "CSCI",
    "CSR", "DANC", "DCTC", "EAPS", "ECE", "ECET", "ECON", "EDCI", "EDPS", "EDST", "EEE",
    "ENE", "ENGL", "ENGR", "ENGT", "ENTM", "ENTR", "EPCS", "EXPL", "FLM", "FMGT", "FNR",
    "FR", "FS", "GEOL", "GEP", "GER", "GRAD", "GREK", "GS", "GSLA", "HDFS", "HEBR",
    "HER", "HETM", "HHS", "HIST", "HK", "HONR", "HORT", "HSCI", "HSOP", "HTM", "IDE",
    "IDIS", "IE", "IET", "ILS", "IMPH", "INFO", "INT", "ITAL", "JPNS", "KOR", "LA",
    "LALS", "LATN", "LC", "LING", "MA", "MATH", "MCMP", "ME", "MET", "MFET", "MGMT",
    "MIL", "MSE", "MSL", "MSPE", "MUS", "NRES", "NS", "NUCL", "NUR", "NUTR", "OBHR",
    "OLS", "PES", "PHIL", "PHPR", "PHRM", "PHSC", "PHST", "PHYS", "POL", "PSY", "PTGS",
    "PUBH", "REG", "REL", "RPMP", "RUSS", "SCI", "SCLA", "SFS", "SLHS", "SOC", "SPAN",
    "STAT", "SYS", "TCM", "TDM", "TECH", "THTR", "TLI", "VCS", "VIP", "VM", "WGSS"
]


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./purdue_courses.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Resend Email
    RESEND_API_KEY: Optional[str] = None

    # Proxy (optional)
    PROXY_URL: Optional[str] = None

    # Scraper settings
    INVENTORY_CRON: str = "0 2 * * *"  # Daily at 2 AM
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
