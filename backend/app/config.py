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

    # Sniper rate-limit resilience.
    #
    # Purdue's limiter on selfservice.mypurdue.purdue.edu is a quota, not a
    # rate: measured 2026-08-27, it allows ~90 requests per ~95-second sliding
    # window and then serves a 519-byte HTTP 200 "too many requests" page.
    # Request spacing did not matter; cumulative count did. The limiter is
    # IP-keyed - a fresh container with a new session and no cookies inherited
    # the worker's block - and it recovers in ~9-20 seconds once we go idle.
    #
    # ~90 per ~95s is a ceiling near 0.95 req/s. We converge on it with AIMD
    # rather than hardcoding a delay, because the ceiling is undocumented, may
    # differ per IP, and may change without notice.
    SNIPER_PACER_START_RATE: float = 0.75
    SNIPER_PACER_MIN_RATE: float = 0.30
    SNIPER_PACER_MAX_RATE: float = 0.90
    # Idle pause after a block, sized to the measured ~9-20s recovery.
    SNIPER_PACER_RECOVERY_SECONDS: float = 12.0
    # Multiplicative decrease on a block, additive increase after a clean run.
    SNIPER_PACER_DECREASE_FACTOR: float = 0.70
    SNIPER_PACER_INCREASE_STEP: float = 0.02
    SNIPER_PACER_INCREASE_AFTER: int = 25

    # How often the continuous worker reloads the tracked-course queue, so new
    # tracks are picked up without restarting the process.
    SNIPER_COURSE_REFRESH_SECONDS: int = 300
    # How often delisted courses are rechecked so Purdue can restore them.
    SNIPER_DELISTED_RECHECK_SECONDS: int = 3600
    # Consecutive "No detailed class info" reads before a section is treated as
    # cancelled. Banner returns that page transiently, so one is not enough.
    SNIPER_SECTION_GONE_THRESHOLD: int = 3

    # Consecutive blocked/network failures before the worker stops walking the
    # queue instead of firing hundreds more requests into an active block.
    SNIPER_MAX_CONSECUTIVE_FAILURES: int = 5
    # Ceiling for the exponential backoff applied after the breaker trips. With
    # the pacer holding us under the quota, backoff is a safety net rather than
    # the normal operating mode, so it is measured in seconds.
    SNIPER_BACKOFF_MAX_SECONDS: float = 300.0
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
