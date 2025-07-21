## 아키텍처 구조

![아키텍처 구조](./포드.png)

## ✅ 사용자 요청 처리 과정

```
[ 1. 사용자의 요청 ]
        ↓
[ 2. 웹 서버 (web - 마이크 입력, 이미지 업로드 → Azure Blob Storage 저장) ]
        ↓
[ 3. 모델 API 서버 (model-api - 입력 정제 및 Celery 작업 등록) ]
        ↓
[ 4. 작업 큐 등록 (Redis - 작업 상태 및 결과 저장) ]
        ↓
[ 5. Celery 워커 (model-worker - 프롬프트 생성 + RAG 파이프라인 기반 이미지 생성) ]
        ↓
[ 6. 결과 저장 (Azure Blob Storage 저장 + Redis에 상태 업데이트) ]
        ↓
[ 7. 모델 API 서버 (model-api - Redis에서 결과 확인) ]
        ↓
[ 8. 사용자 웹사이트 응답 (index.html에서 이미지 및 PSD 표시) ]
```
---

## ✅ 전체 포드 아키텍처 요약 (최종 정리)

| 포드 이름          | 설명            | 주요 기능                    | 관련 파일                  |
| -------------- | ------------- | ------------------------ | ---------------------- |
| `web`          | 사용자와의 UI 상호작용 | 입력, 이미지 첨부, STT, 결과 표시   | `index.html`, `web.py` |
| `model-api`    | API 중계        | Celery 작업 요청 및 결과 확인     | `api.py`               |
| `model-worker` | AI 비동기 처리     | 프롬프트 생성, 이미지 생성, Blob 저장 | `worker.py`            |
| `redis`        | 작업 상태 저장      | Celery 큐 및 결과 상태 관리      | (환경 구성 요소)             |

---

## ✅ 웹 프론트엔드 (`web/index.html`) 설명

### 📌 포드 이름: `web`

### 📁 주요 역할:

* 사용자 입력 UI 제공 (키워드, 카테고리, 레이어, 장면 설명)
* 마이크 음성 입력 → 장면 설명 자동 채우기
* 이미지 업로드 및 미리보기
* FastAPI 백엔드(`/api/generate-image`)로 요청 전송
* 이미지 생성 결과 및 PSD 다운로드 UI 표시

---

### 🧩 핵심 기능별 설명:

#### 1. **카테고리 & 레이어 선택**

* 사용자가 버튼을 클릭해서 한 가지 카테고리와 한 가지 레이어를 선택
* `.selection-btn` 클래스와 `selected` 상태로 UI 반영

#### 2. **텍스트 입력 (키워드 + 장면 설명)**

* 키워드는 `input#userInput`, 장면 설명은 `textarea#captionInput`
* `Enter` 키를 누르면 이미지 생성 요청 실행

#### 3. **마이크 음성 입력 (STT)**

* 🎤 버튼을 누르면 Microsoft STT API를 사용해 한 문장 음성 인식
* 결과가 `captionInput`에 자동 입력됨

#### 4. **이미지 첨부**

* 이미지 드래그, 붙여넣기, 또는 파일 선택으로 업로드 가능
* 최대 10MB 제한, 썸네일 미리보기 UI 포함
* 서버에 먼저 업로드한 후 URL을 생성해서 API 요청에 포함시킴

#### 5. **이미지 생성 요청 흐름**

* `/upload-image`: 이미지가 있을 경우 먼저 업로드
* `/api/generate-image`: 전체 요청 전송

  * `category`, `layer`, `tag`, `caption_input`, `image_url` 포함
* `/api/result/<task_id>`: 결과 조회를 위한 상태 체크

#### 6. **응답 처리**

* 이미지가 생성되면 `<img src="...">` 형태로 결과 표시
* `.psd` 파일도 함께 다운로드 가능
* 실행기를 통해 로컬에서 PSD 파일 자동 실행 시도 가능

---

### 🧾 이 포드에서 처리하는 전체 흐름

```
[ 사용자 입력 ]
   ↓
[ index.html: UI 처리, 이미지 업로드, API 요청 전송 ]
   ↓
[ 결과 수신 → 화면에 이미지 & PSD 다운로드 버튼 표시 ]
```

---

## ✅ 웹 백엔드 (`web/web.py`) 설명

### 📌 포드 이름: `web` (웹 프론트엔드와 같은 포드에 포함)

### 📁 주요 역할:

* 사용자가 첨부한 이미지를 **Azure Blob Storage에 업로드**
* **마이크 입력용 음성 인식 토큰 발급** (Azure Speech API용)
* 정적 파일 제공 (`index.html`)
* 이 포드는 프론트엔드와 백엔드를 함께 실행하는 **전체 UI 담당 포드**

---

### 🧩 주요 기능별 설명:

#### 1. `/upload-image`: 이미지 업로드 및 변환

* 사용자가 선택하거나 붙여넣은 이미지 파일을 받음
* \*\*Pillow(PIL)\*\*로 리사이즈 (최대 1024px, RGB 변환 → PNG 저장)
* **Azure Blob Storage**에 이미지 업로드
* **읽기 전용 SAS URL**을 생성해서 클라이언트에 전달

→ ⚙️ 사용처: `index.html`에서 이미지 첨부 시 호출

---

#### 2. `/get-speech-token`: 음성 인식 토큰 발급

* Azure Cognitive Speech API 사용을 위한 **인증 토큰 요청**
* `SPEECH_KEY`, `SPEECH_REGION` 환경변수를 바탕으로 토큰 발급
* 클라이언트에서 받은 토큰으로 STT 기능 활성화 (🎤 버튼)

→ ⚙️ 사용처: `index.html`의 STT 초기화 시 호출

---

#### 3. `/`: 루트 요청 → 정적 페이지 반환

* `/` 요청이 들어오면 `index.html`을 바로 응답
* 개발 또는 퍼블릭 서비스 시에도 바로 접속 가능하게 만듦

---

### 🔧 기타 구성 요소

* 환경변수:

  * `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`: Blob Storage 연결 정보
  * `SPEECH_KEY`, `SPEECH_REGION`: Azure STT 인증 정보
* 의존 라이브러리:

  * `fastapi`, `requests`, `Pillow`, `azure-storage-blob`

---

### 🧾 전체 흐름 내 위치

```
[ index.html (웹 프론트) ]
   ↓
[ web.py (업로드 처리 및 음성 토큰 발급) ]
   ↓
[ Azure Blob Storage / Azure Speech API 연동 ]
```

---

## ✅ 모델 API 서버 (`model-api/api.py`) 설명

### 📌 포드 이름: `model-api`

### 📁 주요 역할:

* 사용자 입력을 받아서 Celery 워커에 작업 요청
* 워커가 완료한 결과를 Redis를 통해 확인하고 사용자에게 전달
* 두 가지 이미지 생성 방식 지원:

  * 일반적인 프롬프트 기반 요청
  * 이미 생성된 프롬프트로부터 이미지 생성 요청

---

### 🧩 주요 기능별 설명:

#### 1. `/api/generate-prompt`

* 사용자 입력값 (`category`, `layer`, `tag`, `caption_input`, `image_url`)을 수신
* Celery 워커에 `"generate_image"`라는 이름의 태스크 전송
* 생성된 `task_id`를 반환 → 프론트에서 이 ID로 추후 상태 확인

→ ⚙️ 사용처: 웹에서 최초 입력 요청 시 사용

---

#### 2. `/api/generate-image-from-prompt`

* 정제된 프롬프트(`dalle_prompt`)를 직접 받아서 `"generate_final_image"` 태스크를 Celery에 전달
* 일반 입력이 아닌 "최종 생성 프롬프트"를 활용한 워크플로우용

→ ⚙️ 확장: RAG 파이프라인 후 직접 프롬프트 생성했을 때 사용 가능

---

#### 3. `/api/result/{task_id}`

* 주어진 `task_id`의 상태를 Redis에서 확인
* `PENDING`, `SUCCESS`, `FAILURE` 등 상태 반환
* 성공 시 생성된 이미지의 `png_url`, `psd_url` 함께 반환

→ ⚙️ 사용처: 프론트엔드에서 생성 완료 여부 확인용

---

### 🔧 기타 설정

* **Celery 연결**: Redis를 브로커 및 백엔드로 사용 (`redis://redis:6379/0`)
* **CORS 허용**: 개발 편의상 모든 origin 허용(`'*'`)

---

### 🧾 이 포드의 전체 흐름 내 위치

```
[ 사용자 입력 API 호출 ]
   ↓
[ model-api (FastAPI) - Celery 작업 등록 ]
   ↓
[ Celery 워커에서 비동기 처리 → Redis에 결과 저장 ]
   ↓
[ model-api가 상태 확인 후 사용자에게 결과 URL 반환 ]
```

---


## ✅ 모델 워커 (`model-worker/worker.py`) 설명

### 📌 포드 이름: `model-worker`

### 📁 주요 역할:

* GPT-4o + KoCLIP을 활용해 **텍스트 기반 프롬프트 생성**
* OpenAI DALL·E 3 API를 호출해 **이미지 생성**
* 생성된 이미지를 **Azure Blob Storage**에 저장 (PNG + PSD 변환)
* 결과 URL을 Redis를 통해 반환

---

### 🧩 태스크별 설명:

#### 1. `generate_prompt` (비동기 프롬프트 생성)

* 사용자 입력을 바탕으로 GPT-4o에 전달할 프롬프트를 생성
* 사용자의 `tag`와 `caption_input`을 **KoCLIP 임베딩** 후, PostgreSQL에서 유사한 이미지 탐색
* 이미지 2장을 확보 (업로드 + 유사 이미지 + Wikipedia)
* GPT-4o에게 **영문 DALL·E 프롬프트 생성 요청**
* 결과로 `"prompt"` 반환 → 이후 단계에서 이미지 생성에 사용됨

#### 2. `generate_final_image` (이미지 생성 및 저장)

* 위에서 생성한 프롬프트로 OpenAI DALL·E 3 API 호출
* 1024x1024 PNG 이미지 생성 → Blob Storage에 `png/`로 저장
* 생성된 이미지를 PSD로 변환 (ImageMagick `convert` 사용)
* PSD도 `psd/`로 저장
* 각각 **SAS URL**로 사용자에게 제공할 수 있도록 반환

---

### 🛠 사용된 기술 요소

* `Celery`: 비동기 작업 큐 프레임워크
* `KoCLIP`: 한글 자연어 기반 벡터 임베딩
* `GPT-4o`: 영어 프롬프트 생성
* `OpenAI DALL·E 3`: 이미지 생성
* `Azure Blob Storage`: 이미지 업로드 및 퍼블릭 URL 제공
* `psycopg2`: PostgreSQL에서 벡터 유사 이미지 조회
* `PIL + ImageMagick`: 이미지 리사이징 및 포맷 변환

---

### 🧾 전체 흐름 내 위치

```
[ model-api 포드 → Celery에 작업 요청 ]
   ↓
[ model-worker 포드가 GPU/모델 기반으로 프롬프트 생성 ]
   ↓
[ OpenAI API를 통해 이미지 생성 → Blob에 저장 ]
   ↓
[ 결과 URL 반환 → Redis → model-api → 사용자 ]
```

---


