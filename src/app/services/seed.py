from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.models import Movie, MovieAvailability, OttDate, Platform, User
from app.services.predict import predict_ott_date

PLATFORMS = [
    ("Netflix", "netflix"),
    ("Amazon Prime Video", "prime"),
    ("JioHotstar", "jiohotstar"),
    ("SonyLIV", "sonyliv"),
    ("Zee5", "zee5"),
    ("Apple TV", "apple-tv"),
    ("YouTube", "youtube"),
]


def seed(db: Session) -> None:
    admin_email = settings.admin_email.lower()
    admin = db.query(User).filter(User.email == admin_email).first()
    if admin is None:
        db.add(
            User(
                email=admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
        )
    elif not admin.password_hash.startswith("pbkdf2_sha256$"):
        admin.password_hash = hash_password(settings.admin_password)

    if db.query(Platform).count() == 0:
        db.add_all([Platform(name=name, slug=slug) for name, slug in PLATFORMS])
        db.flush()

    if db.query(Movie).count() == 0:
        netflix = db.query(Platform).filter_by(slug="netflix").one()
        prime = db.query(Platform).filter_by(slug="prime").one()
        hotstar = db.query(Platform).filter_by(slug="jiohotstar").one()

        available = Movie(
            title="Sample: Streaming now",
            overview="Demo title already on Netflix in India.",
            theatrical_date=date.today() - timedelta(days=90),
            language="hi",
            country="IN",
        )
        available.availability.append(
            MovieAvailability(platform=netflix, region="IN", availability_type="stream")
        )
        available.ott = OttDate(
            status="available",
            announced_date=date.today() - timedelta(days=20),
        )

        announced = Movie(
            title="Sample: Date announced",
            overview="Demo title with an official upcoming OTT date on Prime.",
            theatrical_date=date.today() - timedelta(days=30),
            language="en",
            country="IN",
        )
        announced.availability.append(
            MovieAvailability(
                platform=prime,
                region="IN",
                availability_type="stream",
                available_from=date.today() + timedelta(days=21),
            )
        )
        announced.ott = OttDate(
            status="announced",
            announced_date=date.today() + timedelta(days=21),
        )

        unknown = Movie(
            title="Sample: Predicted OTT date",
            overview="Demo title with no announced OTT date yet.",
            theatrical_date=date.today() - timedelta(days=14),
            language="hi",
            country="IN",
        )
        unknown.availability.append(
            MovieAvailability(platform=hotstar, region="IN", availability_type="stream")
        )
        prediction = predict_ott_date(
            db,
            unknown.theatrical_date,
            unknown.language,
            unknown.country,
            availability_platform_ids=[hotstar.id],
        )
        unknown.ott = OttDate(status="unknown", **prediction)

        db.add_all([available, announced, unknown])

    db.commit()
