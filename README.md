# 디스코드봇, 끝봇
[![koreanbots](https://koreanbots.dev/api/widget/bots/votes/703956235900420226.svg?style=classic)](https://koreanbots.dev/bots/703956235900420226)
[![topgg](https://top.gg/api/widget/servers/703956235900420226.svg)](https://top.gg/bot/703956235900420226)
[![GitHub](https://img.shields.io/badge/license-AGPL--3.0-brightgreen)](LICENSE)
[![python](https://img.shields.io/badge/python-3.8-blue)](https://www.python.org/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f5e1c2e0ce394529b1c57f9c8eccc7aa)](https://app.codacy.com/gh/janu8ry/kkutbot?utm_source=github.com&utm_medium=referral&utm_content=janu8ry/kkutbot&utm_campaign=Badge_Grade_Settings)
[![DeepSource](https://deepsource.io/gh/janu8ry/kkutbot.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/janu8ry/kkutbot/?ref=repository-badge)

# 소개
끝봇은 재미를 위한 한국 디스코드 봇입니다.
주 기능은 **끝말잇기**입니다.   
끝봇은 인증된 봇으로, 걱정 없이 사용하실 수 있습니다.    
끝봇의 접두사는 ``ㄲ``입니다!

**[![봇 초대하기](https://img.shields.io/badge/%EB%B4%87%20%EC%B4%88%EB%8C%80%ED%95%98%EA%B8%B0-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/api/oauth2/authorize?client_id=703956235900420226&permissions=126016&scope=bot)**


## 정보
- 개발자: [janu8ry](https://github.com/janu8ry), 관리자: [서진](https://github.com/seojin200403)
- 개발 언어: python 3.9.13 ([discord.py 2.0](https://discordpy.readthedocs.io/en/latest/index.html))
- 버전: 2.0.0 alpha
- 데이터베이스: mongoDB  
- 크레딧: 끝봇 개발에 도움을 주신 ``서진#5826``님, 끝봇의 프로필 사진을 만들어주신 ``! Tim23#9999``님께 감사드립니다!
- 저작권: Icons made from [www.flaticon.com](https://www.flaticon.com)


# 기여하기
이슈 등록이나 PR은 언제나 환영입니다!

## 건의사항
Issue 등록 또는 서포트 서버의 `#건의사항` 채널
## 버그제보
Issue 등록 또는 서포트 서버의 `#버그제보` 채널

버그를 해결하는 방법을 아시면 Pull Request 부탁드립니다!

# 2.0 업데이트 TODO
- [ ] 통계 명령어 ui 개선
- [ ] $정보수정 명령어 dict, list 자료형 허용
- [x] 커맨드 답변을 모두 reply로 교체
- [ ] 기한 지난 메일 숨기기
- [ ] 게임 모드 추가 (커스텀, 앞말잇기, 1:1 랭킹전)
- [ ] 티어별 난이도 조정
- [ ] 한방단어 입력시 즉시 판정
- [ ] 웹사이트 개발, 상세 도움말 / 티어 정보 작성
- [ ] 도커 환경 테스트
- [ ] https://betteruptime.com/ 사용

# 봇 실행하기
끝봇의 코드를 직접 실행해보고 싶으시면, [AGPL-3.0 라이선스](LICENSE)를 꼭 지켜주세요.

## 요구사항
- python 3.9
- git
- mongoDB 4.4
- [poetry](https://python-poetry.org)
- [pyenv](https://github.com/pyenv/pyenv), [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) (선택)
- [docker](https://www.docker.com/) (배포시)

### poetry 가상환경 사용 (기본)
```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
poetry install
nano config.yml # config.yml 수정
poetry shell
python3 main.py
```

### pyenv 가상환경 사용 (추천)
```shell
pyenv install 3.9.13
pyenv virtualenv 3.9.13 kkutbot

git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
poetry config virtualenvs.create false --local
pyenv local kkutbot
poetry install
nano config.yml # config.yml 수정
python3 main.py
```

### docker 사용 (배포시)
```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot

docker compose up -d
```

## 로그 저장
매일 0시에 로그가 `logs/yyyy-mm-dd.log.gz` 형태로 압축되어 백업되고,   
`config.yml`에 지정한 백업용 디스코드 채널에도 공유됩니다.

## DB 백업
매일 새벽 5시에 `kkutbot` 데이터베이스가 `backup/yyyy-mm-dd.zip` 형태로 압축되어 보관됩니다.

### 데이터 복구하기
```shell
unzip backup/backup-xxxx-xx-xx.zip  # 압축 해제  tmp 디렉토리 생성
mongorestore -h dbhost:dbport --db kkutbot --authenticationDatabase admin -u dbuser -p dbpasswd tmp/kkutbot --drop
rm -rf tmp
```

# 연락하기

개발자 디스코드: ``so#2375``    
끝봇 이메일: [kkutbot@gmail.com](mailto:kkutbot@gmail.com)    
[![discord](https://discordapp.com/api/guilds/702761942217130005/embed.png?style=banner2)](https://discord.gg/z8tRzwf)

# 라이선스

**AGPL-3.0**
- 사용자의 요청시 소스코드를 제공할 의무가 있습니다.
- 어떤 목적으로, 어떤 형태로든 사용할 수 있지만 사용하거나 변경된 프로그램을 배포하는 경우 무조건 동일한 라이선스 즉, AGPL로 공개해야 합니다.

본 오픈소스 프로젝트를 사용하시려면 아래의 규칙을 따라주세요.
- 봇 도움말 또는 정보 명령어와 레포지토리에 본 오픈소스를 사용했다는 사실을 명시
- (선택) ⭐ 누르기