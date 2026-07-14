# 대(전)유잼 Backend

대전/충청권 관광 데이터를 기반으로 장소 조회, 게시글, 리뷰, 추천, AI 기능을 제공하는 FastAPI 백엔드 서비스입니다. SQLite 데이터베이스를 기본으로 사용하며, `backend/data/raw`의 TourAPI JSON 데이터를 시드하여 장소 API에서 조회할 수 있습니다.

## 주요 기능

- `/health` 서버 상태 확인
- `/api/v1/places` 장소 목록, 검색, 상세 조회
- `/api/v1/posts` 게시글 및 댓글 API
- `/api/v1/reviews` 리뷰 API
- `/api/v1/recommendations` 사용자 조건 기반 추천 API
- `/api/ai` AI 채팅 및 리뷰 요약 API 진입점

## 기술 스택

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic Settings
- OpenAI Python SDK
- Pytest

## 서버 실행 방법

PowerShell 기준입니다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\seed_places.py
uvicorn app.main:app --reload
```

서버가 실행되면 아래 주소에서 확인할 수 있습니다.

- Health Check: http://localhost:8000/health
- API 문서: http://localhost:8000/docs

## 환경 변수

`.env.example`을 복사해 `.env`를 만든 뒤 필요한 값을 수정합니다.

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/localhub.db
OPENAI_API_KEY=OPENAI_API_KEY
OPENAI_MODEL=gpt-5.4-nano
FRONTEND_ORIGIN=http://localhost:5173
```

`OPENAI_API_KEY`가 설정되지 않으면 일반 API는 사용할 수 있지만 AI 관련 API는 503 응답을 반환합니다.

## 데이터 시드

원본 JSON은 `backend/data/raw`에 위치합니다. 아래 명령을 실행하면 SQLite DB가 생성되고 장소 데이터가 적재됩니다.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\seed_places.py
```

동일한 `content_id`는 중복 적재되지 않도록 건너뜁니다.

## 테스트

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```
