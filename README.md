# investment-decision.github.io

my-market-dashboard/
├── .github/
│   └── workflows/
│       └── weekly_update.yml   # [핵심] 주 1회 실행되는 자동화 스크립트 설정
├── data/
│   └── market_indices.json     # [DB 역할] 누적된 지수 데이터가 저장되는 파일
├── scripts/
│   └── update_indices.py       # [로직] 데이터 수집 및 지수 계산 파이썬 코드
├── index.html                  # [Frontend] 차트를 보여주는 메인 페이지
├── requirements.txt            # 파이썬 라이브러리 목록
└── README.md                   # 프로젝트 설명