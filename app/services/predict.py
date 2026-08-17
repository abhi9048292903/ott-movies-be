from collections import Counter
from datetime import UTC, date, datetime, timedelta
from statistics import median, pstdev

from sqlalchemy.orm import Session

from app.models import Movie, MovieAvailability, OttDate

DEFAULT_WINDOWS = {
    "hi": 70,
    "ta": 60,
    "te": 60,
    "ml": 60,
    "kn": 60,
    "en": 75,
}
DEFAULT_WINDOW = 70
MODEL_VERSION = "heuristic-v2"


def _lag_days(theatrical: date, ott_date: date) -> int | None:
    lag = (ott_date - theatrical).days
    if 14 <= lag <= 365:
        return lag
    return None


def _historical_lags(db: Session, language: str, country: str, *, same_language: bool, same_country: bool) -> list[int]:
    query = (
        db.query(Movie, OttDate)
        .join(OttDate, OttDate.movie_id == Movie.id)
        .filter(
            OttDate.status.in_(("available", "announced")),
            Movie.theatrical_date.is_not(None),
            OttDate.announced_date.is_not(None),
        )
    )
    if same_language:
        query = query.filter(Movie.language == language)
    if same_country:
        query = query.filter(Movie.country == country)

    lags: list[int] = []
    for movie, ott in query.all():
        if movie.theatrical_date and ott.announced_date:
            lag = _lag_days(movie.theatrical_date, ott.announced_date)
            if lag is not None:
                lags.append(lag)
    return lags


def _season_bias(theatrical: date) -> int:
    """Festival / holiday windows in India often mean a longer theatrical hold."""
    if theatrical.month in (10, 11, 12, 1, 4, 5):
        return 7
    return 0


def _empty_prediction() -> dict:
    return {
        "predicted_date": None,
        "predicted_window_days": None,
        "window_start": None,
        "window_end": None,
        "confidence": None,
        "likely_platform_id": None,
        "platform_confidence": None,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(UTC).replace(tzinfo=None),
    }


def _likely_platform(
    db: Session,
    language: str,
    country: str,
    availability_platform_ids: list[int] | None,
) -> tuple[int | None, float | None]:
    if availability_platform_ids:
        return availability_platform_ids[0], 0.7

    rows = (
        db.query(MovieAvailability.platform_id)
        .join(Movie, Movie.id == MovieAvailability.movie_id)
        .join(OttDate, OttDate.movie_id == Movie.id)
        .filter(
            OttDate.status == "available",
            Movie.language == language,
            Movie.country == country,
            MovieAvailability.availability_type == "stream",
        )
        .all()
    )
    counts = Counter(platform_id for (platform_id,) in rows)
    if not counts:
        rows = (
            db.query(MovieAvailability.platform_id)
            .join(Movie, Movie.id == MovieAvailability.movie_id)
            .join(OttDate, OttDate.movie_id == Movie.id)
            .filter(OttDate.status == "available", Movie.country == country)
            .all()
        )
        counts = Counter(platform_id for (platform_id,) in rows)
    if not counts:
        return None, None
    platform_id, votes = counts.most_common(1)[0]
    return platform_id, round(min(0.8, votes / max(sum(counts.values()), 1)), 2)


def predict_ott_date(
    db: Session,
    theatrical_date: date | None,
    language: str,
    country: str,
    availability_platform_ids: list[int] | None = None,
) -> dict:
    result = _empty_prediction()
    platform_id, platform_confidence = _likely_platform(db, language, country, availability_platform_ids)
    result["likely_platform_id"] = platform_id
    result["platform_confidence"] = platform_confidence

    if theatrical_date is None:
        result["confidence"] = 0.2 if platform_id else None
        return result

    lags = _historical_lags(db, language, country, same_language=True, same_country=True)
    source = "lang_country"
    if len(lags) < 3:
        broader = _historical_lags(db, language, country, same_language=False, same_country=True)
        if len(broader) > len(lags):
            lags = broader
            source = "country"
    if len(lags) < 3:
        lang_only = _historical_lags(db, language, country, same_language=True, same_country=False)
        if len(lang_only) > len(lags):
            lags = lang_only
            source = "language"

    if len(lags) >= 3:
        window = int(median(lags))
        spread = int(pstdev(lags)) if len(lags) > 1 else 14
        spread = min(max(spread, 10), 35)
        confidence = min(0.82, 0.42 + 0.04 * len(lags))
        if source != "lang_country":
            confidence = max(0.35, confidence - 0.12)
    else:
        window = DEFAULT_WINDOWS.get(language.lower(), DEFAULT_WINDOW)
        spread = 21
        confidence = 0.38 if lags else 0.32

    window += _season_bias(theatrical_date)
    predicted = theatrical_date + timedelta(days=window)
    result.update(
        {
            "predicted_date": predicted,
            "predicted_window_days": window,
            "window_start": predicted - timedelta(days=spread),
            "window_end": predicted + timedelta(days=spread),
            "confidence": round(confidence, 2),
        }
    )
    return result


def apply_prediction(ott: OttDate, prediction: dict) -> None:
    ott.predicted_date = prediction["predicted_date"]
    ott.predicted_window_days = prediction["predicted_window_days"]
    ott.window_start = prediction["window_start"]
    ott.window_end = prediction["window_end"]
    ott.confidence = prediction["confidence"]
    ott.likely_platform_id = prediction["likely_platform_id"]
    ott.platform_confidence = prediction["platform_confidence"]
    ott.model_version = prediction["model_version"]
    ott.generated_at = prediction["generated_at"]


def clear_prediction(ott: OttDate) -> None:
    ott.predicted_date = None
    ott.predicted_window_days = None
    ott.window_start = None
    ott.window_end = None
    ott.confidence = None
    ott.likely_platform_id = None
    ott.platform_confidence = None
    ott.model_version = None
    ott.generated_at = None
