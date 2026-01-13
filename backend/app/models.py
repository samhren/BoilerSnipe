from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """User account for authentication and tracking"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tracks = relationship("Track", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)


class Course(Base):
    """Course information scraped from Purdue"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    crn = Column(String, unique=True, index=True, nullable=False)  # Course Reference Number
    course_code = Column(String, index=True, nullable=False)  # e.g., "MA 35100"
    title = Column(String, nullable=False)  # e.g., "Elementary Linear Algebra"
    instructor = Column(String)
    time = Column(String)  # e.g., "10:30 am - 11:20 am"
    days = Column(String)  # e.g., "TR"
    schedule_type = Column(String)  # e.g., "Lecture", "Laboratory", "Recitation"
    term_code = Column(String, nullable=False)  # e.g., "202620"
    term_name = Column(String)  # e.g., "Spring 2026"

    # Seat information (updated by sniper)
    seats_available = Column(Integer, default=0)
    seats_capacity = Column(Integer, default=0)
    seats_remaining = Column(Integer, default=0)

    # Metadata
    last_checked = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tracks = relationship("Track", back_populates="course", cascade="all, delete-orphan")


class Track(Base):
    """User's tracked courses with notification status"""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    # Status tracking
    last_status = Column(String, default="closed")  # "open" or "closed"
    last_seats = Column(Integer, default=0)
    last_notified = Column(DateTime(timezone=True))
    last_checked = Column(DateTime(timezone=True))

    # Notification preferences
    notify_on_open = Column(Boolean, default=True)
    notify_on_close = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tracks")
    course = relationship("Course", back_populates="tracks")


class NotificationLog(Base):
    """Log of all sent notifications"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))

    notification_type = Column(String)  # "seat_open", "seat_closed"
    message = Column(String)
    status = Column(String)  # "sent", "failed"
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GradeDistribution(Base):
    """Historical grade distribution for courses by instructor and semester"""
    __tablename__ = "grade_distributions"

    id = Column(Integer, primary_key=True, index=True)

    # Course identification
    subject = Column(String, index=True, nullable=False)  # e.g., "CS"
    course_number = Column(String, index=True, nullable=False)  # e.g., "18000"
    title = Column(String)  # e.g., "Problem Solving And OO Programming"

    # Section details
    academic_period = Column(String, index=True, nullable=False)  # e.g., "202510"
    academic_period_desc = Column(String)  # e.g., "Fall 2024"
    section = Column(String)  # e.g., "001"
    crn = Column(String, index=True)  # e.g., "17446"
    instructor = Column(String, index=True)  # e.g., "Dunsmore, Hubert E."

    # Letter grade percentages (as decimals 0.0-1.0)
    grade_a_plus = Column(Float, nullable=True)
    grade_a = Column(Float, nullable=True)
    grade_a_minus = Column(Float, nullable=True)
    grade_b_plus = Column(Float, nullable=True)
    grade_b = Column(Float, nullable=True)
    grade_b_minus = Column(Float, nullable=True)
    grade_c_plus = Column(Float, nullable=True)
    grade_c = Column(Float, nullable=True)
    grade_c_minus = Column(Float, nullable=True)
    grade_d_plus = Column(Float, nullable=True)
    grade_d = Column(Float, nullable=True)
    grade_d_minus = Column(Float, nullable=True)
    grade_e = Column(Float, nullable=True)  # Some use E instead of F
    grade_f = Column(Float, nullable=True)

    # Other grade types
    grade_w = Column(Float, nullable=True)  # Withdrawal
    grade_i = Column(Float, nullable=True)  # Incomplete
    grade_p = Column(Float, nullable=True)  # Pass
    grade_n = Column(Float, nullable=True)  # No grade
    grade_s = Column(Float, nullable=True)  # Satisfactory
    grade_u = Column(Float, nullable=True)  # Unsatisfactory
    grade_au = Column(Float, nullable=True)  # Audit
    grade_pi = Column(Float, nullable=True)  # Pass/Incomplete
    grade_si = Column(Float, nullable=True)  # Satisfactory/Incomplete

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite indexes for efficient lookups
    __table_args__ = (
        Index('ix_grade_subject_course', 'subject', 'course_number'),
        Index('ix_grade_instructor_lookup', 'subject', 'course_number', 'instructor'),
    )
