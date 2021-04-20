# 디스코드봇, 끝봇
![koreanbots](https://api.koreanbots.dev/widget/bots/votes/703956235900420226.svg) [![topgg](https://top.gg/api/widget/servers/703956235900420226.svg)](https://top.gg/bot/703956235900420226) ![GitHub](https://img.shields.io/badge/license-AGPL--3.0-brightgreen) ![python](https://img.shields.io/badge/python-3.8-blue) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/f5e1c2e0ce394529b1c57f9c8eccc7aa)](https://app.codacy.com/gh/janu8ry/kkutbot?utm_source=github.com&utm_medium=referral&utm_content=janu8ry/kkutbot&utm_campaign=Badge_Grade_Settings)

# 소개
끝봇은 재미를 위한 한국 디스코드 봇입니다.
주 기능은 **끝말잇기**입니다.   
끝봇은 인증된 봇으로, 걱정 없이 사용하실 수 있습니다.    
끝봇의 접두사는 ``ㄲ`` 입니다!

**[봇 초대하기](https://discord.com/api/oauth2/authorize?client_id=703956235900420226&permissions=126016&scope=bot)**


## 정보
- 개발자: [janu8ry](https://github.com/janu8ry), 관리자: [서진](https://github.com/seojin200403)
- 개발 언어: python 3.8.6 ([discord.py 1.7.0](https://discordpy.readthedocs.io/en/latest/index.html))
- 버전: 1.6 (개발버전: 1.7a)
- 데이터베이스: mongoDB  
- 크레딧: 끝봇 개발에 도움을 주신 ``서진#5826`` 님, 끝봇의 프로필 사진을 만들어주신 ``! Tim23#9999``님께 감사드립니다!
- 저작권: Icons made from [www.flaticon.com](https://www.flaticon.com)


# 기여하기
이슈 등록이나 PR은 언제나 환영입니다!

## 건의사항
Issue 등록 또는 서포트 서버의 `#건의사항` 채널
## 버그제보
Issue 등록 또는 서포트 서버의 `#버그제보` 채널

버그를 해결하는 방법을 아시면 Pull Request 부탁드립니다!

# Update Todo
- [x] 이미 출석해도 주간 출석 현황 조회 가능하도록 변경
- [ ] 게임 모드 추가 (커스텀, 앞말잇기, 1:1 랭킹전)
- [ ] 티어별 난이도 조정
- [ ] 데일리 퀘스트
- [ ] 패배한 경우 단어 힌트 보여주기
- [ ] 도움말 재작성
- [ ] 한방단어 입력시 즉시 판정

# 봇 실행하기
끝봇의 코드를 직접 실행해보고 싶으시면, [라이선스](https://github.com/janu8ry/kkutbot/blob/master/LICENSE) 를 꼭 지켜주세요.

## 요구사항
- python 3.8
- git
- mongoDB

```shell
git clone https://github.com/janu8ry/kkutbot.git
pip3 install -r requirements.txt
mv config.example.yml config.yml # config.yml 수정
python3 main.py
```

# 연락하기

개발자 디스코드: ``sonix18#3825``    
끝봇 이메일: [kkutbot@gmail.com](mailto:kkutbot@gmail.com)    
[![discord](https://discordapp.com/api/guilds/702761942217130005/embed.png?style=banner2)](https://discord.gg/z8tRzwf)

# 라이선스

**AGPL-3.0**
- 사용자의 요청시 소스코드를 제공할 의무가 있습니다.
- 어떤 목적으로, 어떤 형태로든 사용할 수 있지만 사용하거나 변경된 프로그램을 배포하는 경우 무조건 동일한 라이선스 즉, AGPL로 공개해야 합니다.
