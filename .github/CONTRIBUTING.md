# 끝봇에 기여하기

## 개발 환경 설정하기

요구사항:
 - python >= 3.9
 - mongoDB ~= 4.4
 - poetry ~= 1.1.6
 - docker
 - pyenv (선택)
 - git

```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
poetry install
nano config.yml # config.yml 수정
poetry shell
python3 main.py
```

## 코드 스타일

커밋을 하기 전에, 꼭 isort를 이용하여 코드를 포맷팅 한 후, mypy를 사용하여 타입체크를 해주세요.

```shell
isort .
mypy .
```
