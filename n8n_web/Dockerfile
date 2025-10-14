# 1. 기반 이미지 설정 (Node.js 버전 18의 가벼운 버전을 사용)
FROM node:18-slim

# 2. 컨테이너 내 작업 디렉토리 설정
WORKDIR /usr/src/app

# 3. 의존성 설치 (소스코드보다 먼저 복사하여 빌드 캐시 활용)
COPY package*.json ./
RUN npm install

# 4. 소스 코드 복사
COPY . .

# 5. 컨테이너가 노출할 포트 설정
EXPOSE 3000

# 6. 컨테이너 시작 시 실행할 명령어
CMD [ "node", "server.js" ]