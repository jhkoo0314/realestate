# 메인 PC Tailscale 연결 실행 계획서

> 작성일: 2026-08-04  
> 대상: 메인 PC 1대와 허가된 업무용 사용자 PC 1~2대  
> 목적: 매물관리 프로그램을 인터넷에 공개하지 않고, Tailscale 전용 네트워크 안에서만 사용한다.

> 진행 상태 (2026-08-06): 메인 PC와 서브 PC의 Tailscale 연동 및 기존 HTTPS 주소를 통한 접속을 완료했다. Windows 재부팅 후 Streamlit 자동 실행의 실제 확인은 별도 진행한다.

## 1. 결정한 연결 방식

아래 방식으로 연결한다.

```text
허가된 사용자 PC
  └─ Tailscale + 웹브라우저
          │ 전용 암호화 연결(HTTPS)
          ▼
메인 PC
  ├─ Tailscale Serve
  ├─ Streamlit: 127.0.0.1:8501 에서만 실행
  └─ storage\real_estate.db 단일 원본 보관
```

- 메인 PC의 Streamlit은 외부·사무실 LAN에 직접 열지 않고 `127.0.0.1:8501`에서만 실행한다.
- Tailscale Serve가 그 로컬 화면을 Tailscale 전용 HTTPS 주소로만 중계한다.
- 사용자 PC는 SQLite 파일이나 프로그램을 설치·실행하지 않고 브라우저로만 접속한다.
- 공유기 포트 포워딩, Tailscale Funnel, 공용 주소 공개는 사용하지 않는다.

### 이 방식을 선택한 이유

기존 안내의 `--server.address 0.0.0.0`과 Windows 방화벽 8501 예외 방식은 사무실 네트워크에서 직접 접속할 때의 방법이다. 이번 운영 기준에서는 Tailscale Serve를 사용하므로 Streamlit을 로컬에만 묶어도 된다. 따라서 8501을 사내망 전체에 열 필요가 없고, 접속 권한은 Tailscale 계정·기기·정책으로 제한할 수 있다.

## 2. 작업 전 확인과 역할 분리

설정을 시작하기 전에 아래 항목을 확인한다.

| 항목 | 확인 내용 | 담당 |
|---|---|---|
| 메인 PC | 프로젝트 폴더, Python 환경, 실제 DB 파일 위치가 확정됨 | 운영 담당자 |
| 데이터 | 현재 DB의 백업 1개를 원본과 다른 위치에 보관하고, 원본을 수정하지 않음 | 운영 담당자 |
| Tailscale 관리자 | 사용자 초대·기기 승인·접근정책을 관리할 사무실 계정 1개를 지정 | 관리자 |
| 사용자 | 접속을 허용할 직원의 개별 Tailscale 계정과 업무용 PC만 목록화 | 관리자 |
| 운영 주소 | 메인 PC 이름을 `realestate-main`처럼 식별하기 쉽게 정함 | 관리자 |

계정을 공유하지 않는다. 퇴사·기기 교체 시에는 해당 사용자 또는 기기를 즉시 제거할 수 있어야 한다.

## 3. 실행 순서

### 3-1. 메인 PC 사전 점검

1. 메인 PC에서 프로젝트를 정상 경로에서 실행할 수 있는지 확인한다.
2. 메인 PC 로컬 브라우저에서 아래 주소가 열리는지 확인한다.

   ```text
   http://127.0.0.1:8501
   ```

3. 신규 등록·기존 이력 조회가 가능한지 짧게 확인한다.
4. 이 단계에서 DB 경로나 DB 파일을 복사·교체하지 않는다.

Streamlit 실행 명령은 다음처럼 로컬 전용으로 한다. 프로젝트 폴더에서 실행한다. `streamlit`만 입력하면 Windows가 설치 경로를 찾지 못할 수 있으므로, 반드시 프로젝트의 가상환경 Python으로 실행한다.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

실행 창은 업무 중 닫지 않고 최소화한다.

### 3-2. Tailscale 설치 및 기기 등록

1. 메인 PC에 Tailscale을 설치하고 사무실 관리자 계정으로 로그인한다.
2. Tailscale 관리 화면에서 메인 PC가 승인·연결됨인지 확인하고 이름을 `realestate-main`으로 정한다.
3. 사용자 PC마다 Tailscale을 설치한다.
4. 각 직원은 자신의 계정으로 로그인하고, 관리자가 해당 사용자를 사무실 tailnet에 초대·승인한다.
5. 관리 화면에서 허가된 메인 PC와 사용자 PC만 온라인 상태인지 확인한다.

### 3-3. 접근정책 설정

기본 정책이 모든 tailnet 기기 간 통신을 허용하는 상태라면, 메인 PC의 웹 화면은 허가된 사용자만 접근하도록 제한한다. 새 정책은 Tailscale 관리 화면에서 미리보기 후 적용한다.

권장 모델:

```text
group:realestate-users
  ├─ 운영 담당자 계정
  └─ 허가된 사용자 계정 1~2개

tag:realestate-main
  └─ 메인 PC에만 부여

허용: group:realestate-users → tag:realestate-main 의 HTTPS(443)만
그 외: 허용하지 않음
```

계정 주소가 확정된 뒤 관리자가 아래 구조에 맞춰 정책을 작성한다. 실제 이메일은 계획서에 적지 않고 관리 화면에서 입력한다.

```jsonc
{
  "groups": {
    "group:realestate-users": [
      "운영담당자_계정",
      "사용자1_계정",
      "사용자2_계정"
    ]
  },
  "tagOwners": {
    "tag:realestate-main": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["group:realestate-users"],
      "dst": ["tag:realestate-main:443"]
    }
  ]
}
```

기존 tailnet에 이미 다른 업무용 규칙이 있다면, 위 예시로 전체 정책을 덮어쓰지 않는다. 기존 규칙을 유지한 채 부동산관리용 그룹·태그·허용 규칙만 추가한다.

### 3-4. Tailscale Serve 연결

메인 PC에서 Streamlit이 `127.0.0.1:8501`으로 열려 있는 상태에서 관리자 권한 PowerShell을 열어 다음을 실행한다.

```powershell
tailscale serve --bg http://127.0.0.1:8501
```

그 다음 현재 설정과 Tailscale이 알려 주는 접속 주소를 확인한다.

```powershell
tailscale serve status
```

- 이 명령이 알려 주는 `https://...` 주소를 사용자 접속 주소로 사용한다.
- MagicDNS 이름을 사용할 수 있으면 숫자 IP보다 이 HTTPS 주소를 바탕화면 바로가기에 등록한다.
- `tailscale funnel`은 어떤 경우에도 실행하지 않는다.

### 3-5. 사용자 PC 접속 확인

1. 사용자 PC에서 Tailscale이 연결됨인지 확인한다.
2. 브라우저로 Tailscale Serve HTTPS 주소를 연다.
3. 매물 현황 리스트가 열리는지 확인한다.
4. 테스트용으로 조회 후, 허용된 업무 절차에 따라 1건을 저장하고 목록에서 즉시 재조회한다.
5. 메인 PC에서도 같은 결과와 같은 DB를 보는지 확인한다.

## 4. Windows 방화벽과 기존 안내의 처리

선택한 Serve 방식에서는 Streamlit이 `127.0.0.1`만 수신하므로 **8501 인바운드 규칙을 새로 만들지 않는다.** 기존에 테스트 과정에서 만든 `8501` 광범위 허용 규칙이 있다면, 실제 연결 검증 후 범위와 필요성을 다시 확인하고 불필요한 규칙은 비활성화 대상으로 기록한다.

`0.0.0.0:8501` + `100.64.0.0/10` 방화벽 제한 방식은 Serve를 사용할 수 없는 경우에만 별도 승인 후 검토하는 대안이다. 두 방식은 동시에 기본 설정으로 사용하지 않는다.

## 5. 완료 확인표

| 확인 항목 | 기준 | 결과 |
|---|---|---|
| 메인 PC 로컬 실행 | `http://127.0.0.1:8501`에서 정상 화면 표시 | [ ] |
| 외부 직접 노출 없음 | Streamlit이 `127.0.0.1`로만 실행되고 Funnel·포트포워딩 없음 | [ ] |
| Tailscale 기기 승인 | 메인 PC와 허가된 사용자 PC만 목록에서 승인됨 | [ ] |
| 접근 제한 | 허가된 계정만 메인 PC HTTPS에 접속 가능 | [ ] |
| 사용자 접속 | 사용자 PC 브라우저에서 Tailscale HTTPS 주소가 열림 | [ ] |
| 단일 DB | 사용자 PC에 DB 복사본이 없고 메인 PC 원본만 사용 | [ ] |
| 저장 공유 | 한 PC의 저장 결과를 다른 PC가 새로고침 후 확인 | [ ] |
| 이력 보존 | 재등록 후 과거 매물 회차가 그대로 조회됨 | [ ] |
| 장애 안내 | 메인 PC·Tailscale·Streamlit 중 하나를 끈 경우 원인을 구분 가능 | [ ] |

## 6. 운영 절차와 장애 대응

### 매일 시작

1. 메인 PC를 켠다.
2. Tailscale 연결 상태를 확인한다.
3. Streamlit을 로컬 전용 명령으로 실행한다.
4. 메인 PC에서 로컬 주소를 확인한다.
5. 사용자 PC에서 Serve HTTPS 주소를 열어 접속을 확인한다.

### 접속 불가 시 확인 순서

1. 메인 PC가 켜져 있는가?
2. 메인 PC의 Tailscale이 연결됨인가?
3. Streamlit 실행창이 열려 있는가?
4. 메인 PC에서 `http://127.0.0.1:8501`이 열리는가?
5. `tailscale serve status`에 로컬 대상과 HTTPS 주소가 보이는가?
6. 사용자 PC의 Tailscale이 연결됨인가?
7. 해당 사용자가 `group:realestate-users`에 포함되고, 메인 PC 태그·정책이 맞는가?

문제 해결을 위해 DB를 사용자 PC에 복사하거나 인터넷 포트를 열지 않는다.

### 연결 해제 또는 되돌리기

Tailscale Serve 중계만 중지해야 할 때는 메인 PC에서 다음을 실행한다.

```powershell
tailscale serve reset
```

이 작업은 Tailscale Serve 설정만 해제한다. Streamlit 프로그램과 SQLite 원본 데이터는 삭제·수정하지 않는다.

## 7. 운영 전 남은 확인

- [ ] 일일 백업 생성과 별도 위치에서의 백업본 조회를 완료한다.
- [ ] 메인 PC 재시작 후 Tailscale·Streamlit을 다시 실행해 동일한 주소로 접속되는지 확인한다.
- [ ] 사용자 PC 2대에서 동일한 목록과 저장 결과를 확인한다.
- [ ] 담당자 변경 시 계정·기기 삭제 절차를 한 번 점검한다.

## 참고 자료

- [Tailscale Serve 명령](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Tailscale 접근 제어와 Grants](https://tailscale.com/docs/features/access-control)
- [Tailscale ACL 정책](https://tailscale.com/docs/features/access-control/acls)
- [Tailscale 빠른 시작](https://tailscale.com/docs/how-to/quickstart)
