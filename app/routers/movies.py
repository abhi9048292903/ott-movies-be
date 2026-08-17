from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_admin
from app.db import get_db
from app.models import Movie, MovieAvailability, OttDate, Platform, User
from app.schemas import MovieListResponse, MovieOut, MovieWrite, PlatformOut
from app.services.predict import apply_prediction, clear_prediction, predict_ott_date

router = APIRouter()


def _movie_query(db: Session):
    return db.query(Movie).options(
        joinedload(Movie.availability).joinedload(MovieAvailability.platform),
        joinedload(Movie.ott).joinedload(OttDate.likely_platform),
    )


def _apply_write(db: Session, movie: Movie, payload: MovieWrite) -> Movie:
    movie.title = payload.title.strip()
    movie.overview = payload.overview
    movie.poster_url = payload.poster_url
    movie.theatrical_date = payload.theatrical_date
    movie.language = payload.language
    movie.country = payload.country
    movie.tmdb_id = payload.tmdb_id

    movie.availability.clear()
    for item in payload.availability:
        platform = db.get(Platform, item.platform_id)
        if platform is None:
            raise HTTPException(status_code=400, detail=f"Unknown platform_id {item.platform_id}")
        movie.availability.append(
            MovieAvailability(
                platform_id=item.platform_id,
                availability_type=item.availability_type,
                region=item.region.upper(),
                available_from=item.available_from,
                source="admin",
            )
        )

    if movie.ott is None:
        movie.ott = OttDate(status=payload.ott_status)
    movie.ott.status = payload.ott_status
    movie.ott.announced_date = payload.announced_date if payload.ott_status != "unknown" else None

    if payload.ott_status == "unknown":
        prediction = predict_ott_date(
            db,
            payload.theatrical_date,
            payload.language,
            payload.country,
            availability_platform_ids=[item.platform_id for item in payload.availability],
        )
        apply_prediction(movie.ott, prediction)
    else:
        clear_prediction(movie.ott)

    return movie


def _to_out(movie: Movie) -> MovieOut:
    return MovieOut.model_validate(movie)


@router.get("/platforms", response_model=list[PlatformOut])
def list_platforms(db: Session = Depends(get_db)):
    return db.query(Platform).order_by(Platform.name).all()


@router.get("/movies", response_model=MovieListResponse)
def list_movies(
    q: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = _movie_query(db)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Movie.title.ilike(like), Movie.overview.ilike(like)))
    if status:
        query = query.filter(Movie.ott.has(OttDate.status == status))
    if platform:
        query = query.filter(
            Movie.availability.any(MovieAvailability.platform.has(Platform.slug == platform))
        )

    movies = query.order_by(Movie.title).all()
    return MovieListResponse(items=[_to_out(m) for m in movies], total=len(movies))


@router.get("/movies/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = _movie_query(db).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _to_out(movie)


@router.post("/movies", response_model=MovieOut, status_code=201)
def create_movie(
    payload: MovieWrite,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    movie = _apply_write(db, Movie(), payload)
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return _to_out(_movie_query(db).filter(Movie.id == movie.id).first())


@router.put("/movies/{movie_id}", response_model=MovieOut)
def update_movie(
    movie_id: int,
    payload: MovieWrite,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    movie = _movie_query(db).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    _apply_write(db, movie, payload)
    db.commit()
    return _to_out(_movie_query(db).filter(Movie.id == movie_id).first())


@router.post("/movies/{movie_id}/predict", response_model=MovieOut)
def refresh_prediction(
    movie_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    movie = _movie_query(db).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    if movie.ott is None:
        movie.ott = OttDate(status="unknown")
    prediction = predict_ott_date(
        db,
        movie.theatrical_date,
        movie.language,
        movie.country,
        availability_platform_ids=[item.platform_id for item in movie.availability],
    )
    movie.ott.status = "unknown"
    movie.ott.announced_date = None
    apply_prediction(movie.ott, prediction)
    db.commit()
    return _to_out(_movie_query(db).filter(Movie.id == movie_id).first())
