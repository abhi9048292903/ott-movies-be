from datetime import date, timedelta
from statistics import median

from sqlalchemy.orm import Session

from app.models import Movie, OttDate

DEFAULT_WINDOWS = {
    "hi": 70,
    "ta": 60,
    "te": 60,
    "ml": 60,
    "kn": 60,
    "en": 75,
}
DEFAULT_WINDOW = 70
MODEL_VERSION = "heuristic-v1"


def _historical_lags(db: Session, language: str, country: str) -> list[int]:
    rows = (
        db.query(Movie, OttDate)
        .join(OttDate, OttDate.movie_id == Movie.id)
        .filter(
            OttDate.status == "available",
            Movie.theatrical_date.is_not(None),
            OttDate.announced_date.is_not(None),
            Movie.language == language,
            Movie.country == country,
        )
        .all()
    )
    lags: list[int] = []
    for movie, ott in rows:
        if movie.theatrical_date and ott.announced_date:
            lag = (ott.announced_date - movie.theatrical_date).days
            if 14 <= lag <= 365:
                lags.append(lag)
    return lags


def predict_ott_date(db: Session, theatrical_date: date | None, language: str, country: str) -> dict:
    if theatrical_date is None:
        return {
            "predicted_date": None,
            "predicted_window_days": None,
            "confidence": None,
            "model_version": MODEL_VERSION,
        }

    lags = _historical_lags(db, language, country)
    if len(lags) >= 5:
        window = int(median(lags))
        confidence = min(0.85, 0.4 + 0.05 * len(lags))
    else:
        window = DEFAULT_WINDOWS.get(language.lower(), DEFAULT_WINDOW)
        confidence = 0.35 if not lags else 0.45

    return {
        "predicted_date": theatrical_date + timedelta(days=window),
        "predicted_window_days": window,
        "confidence": round(confidence, 2),
        "model_version": MODEL_VERSION,
    }
