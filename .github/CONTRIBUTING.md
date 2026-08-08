# 끝봇에 기여하기

## 개발 환경 설정하기

요구사항:
 - python ~= 3.14
 - mongoDB ~= 7.0
 - uv
 - pyenv (선택)
 - git

```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
uv sync
cp .env.example .env
nano .env # 토큰, DB 계정 등 수정
uv run python3 main.py
```

## 코드 스타일

커밋을 하기 전에, 꼭 ruff를 이용하여 코드를 포맷팅 해주세요.

```shell
uv run ruff format .      # 코드 포맷 (line-length=150)
uv run ruff check --fix .  # 린트 + import 정렬
uv run mypy .              # 타입 체크
```
