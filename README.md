# 디스코드봇, 끝봇
[![koreanbots](https://koreanbots.dev/api/widget/bots/votes/703956235900420226.svg?style=classic)](https://koreanbots.dev/bots/703956235900420226)
[![GitHub](https://img.shields.io/badge/license-AGPL--3.0-brightgreen)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/6716eb15f92f4bb29c3da2f09d8e2483)](https://www.codacy.com/gh/janu8ry/kkutbot/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=janu8ry/kkutbot&amp;utm_campaign=Badge_Grade)
[![DeepSource](https://deepsource.io/gh/janu8ry/kkutbot.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/janu8ry/kkutbot/?ref=repository-badge)

# 소개
📔 끝말잇기 디스코드 봇 - 끝말잇기 게임을 디스코드에서 플레이하세요!

끝봇은 끝말잇기를 지원하는 디스코드 봇입니다.    
끝봇의 접두사는 ㄲ이며, 빗금 명령어로도 사용하실 수 있습니다!

**[![봇 초대하기](https://img.shields.io/badge/%EB%B4%87%20%EC%B4%88%EB%8C%80%ED%95%98%EA%B8%B0-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/api/oauth2/authorize?client_id=703956235900420226&permissions=126016&scope=bot)**


## 정보
- 개발자: [janu8ry](https://github.com/janu8ry), 관리자: [서진](https://github.com/seojin200403)
- 개발 언어: python 3.10.17 ([discord.py 2.3.1](https://discordpy.readthedocs.io/en/latest/index.html))
- 버전: 2.2.0-alpha
- 데이터베이스: mongoDB 4.4   
- 크레딧: 끝봇 개발에 도움을 주신 [서진](https://github.com/seojin200403)님, 끝봇의 프로필 사진을 만들어주신 [Tim232](https://github.com/Tim232)님께 감사드립니다!
- 저작권: Icons made from [www.flaticon.com](https://www.flaticon.com)


# 기여하기
이슈 등록이나 PR은 언제나 환영입니다!

## 건의사항
Issue 등록 또는 서포트 서버의 `#건의사항` 채널
## 버그제보
Issue 등록 또는 서포트 서버의 `#버그제보` 채널

버그를 해결하는 방법을 아시면 Pull Request 부탁드립니다!

# 다음 업데이트 TODO
- [ ] 게임 모드 추가 (커스텀, 앞말잇기, 1:1 랭킹전)
- [ ] 연승 시스템
- [ ] 티어별 난이도 조정

# 봇 실행하기
끝봇의 코드를 직접 실행해보고 싶으시면, [AGPL-3.0 라이선스](LICENSE)를 꼭 지켜주세요.

## 요구사항
- python 3.10.17
- git
- mongoDB 4.4
- [uv](https://docs.astral.sh/uv/)
- [pyenv](https://github.com/pyenv/pyenv)
- [docker](https://www.docker.com/) (배포시)
- 디스코드 봇의 '메시지 인텐트', '멤버 인텐트' 활성화

### uv 사용 (개발)
```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
uv sync
vi config.yml # config.yml 수정
python3 main.py
```

### docker 사용 (배포)
```shell
git clone https://github.com/janu8ry/kkutbot.git
cd kkutbot
vi config.yml # config.yml 수정
vi mongob.yml # mongob.yml 수정
vi .env # mongoDB 사용자 이름/암호, 데이터 저장 경로 수정
docker build -t kkutbot:latest .
docker compose up -d
```

## 로그 저장
매일 0시에 로그가 `logs/yyyy-mm-dd.log.gz` 형태로 압축되어 백업되고,   
0시 5분에 `config.yml`에 지정한 백업용 디스코드 채널에도 공유됩니다.

## DB 백업 (도커 전용)
매일 5시에 `kkutbot` 데이터베이스가 `backup/yyyy-mm-dd.gz` 형태로 압축되어 보관됩니다.   
또한 5시 5분에 `config.yml`에 지정한 백업용 디스코드 채널에도 공유됩니다.   

### 데이터 복구하기
```shell
docker exec -i kkutbot-mongo sh -c 'mongorestore --db kkutbot --gzip --archive --drop --authenticationDatabase admin -u username -p password' < /yyyy-mm-dd.gz
```

# 연락하기

개발자 디스코드: ``janu8ry``    
끝봇 이메일: [kkutbot@gmail.com](mailto:kkutbot@gmail.com)    
[![discord](https://discordapp.com/api/guilds/702761942217130005/embed.png?style=banner2)](https://discord.gg/z8tRzwf)

# 라이선스

**AGPL-3.0**
- 사용자의 요청시 소스코드를 제공할 의무가 있습니다.
- 어떤 목적으로, 어떤 형태로든 사용할 수 있지만 사용하거나 변경된 프로그램을 배포하는 경우 무조건 동일한 라이선스 즉, AGPL로 공개해야 합니다.

본 오픈소스 프로젝트를 사용하시려면 아래의 규칙을 따라주세요.
- 봇 도움말 또는 정보 명령어와 레포지토리에 본 오픈소스를 사용했다는 사실을 명시
- (선택) ⭐ 누르기
