const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const port = 3000;

app.use(express.json());

// n8n 웹훅 URL - Chat Trigger는 쿼리 파라미터로 sessionId를 받습니다.
const N8N_WEBHOOK_URL = 'http://20.196.73.32:5678/webhook/4bafa620-3d7a-42b1-89aa-1eb17b31503e/chat';

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/send-message', async (req, res) => {
    // 1. 프론트엔드에서 message와 sessionId를 모두 받음
    const { message, sessionId } = req.body;

    if (!message || !sessionId) {
        return res.status(400).json({ error: '메시지 또는 세션 ID가 없습니다.' });
    }

    try {
        // 2. n8n 웹훅 URL에 쿼리 파라미터로 sessionId 추가
        const fullUrl = `${N8N_WEBHOOK_URL}?sessionId=${sessionId}`;

        // 3. n8n에는 message 객체만 본문으로 전송
        const n8nResponse = await axios.post(fullUrl, {
            message: message
        });

        // 4. n8n Agent의 최종 응답('output' 필드)을 프론트엔드로 전달
        res.json({ output: n8nResponse.data.output });
    } catch (error) {
        console.error('n8n 통신 오류:', error.message);
        res.status(500).json({ error: '챗봇 서버와 통신할 수 없습니다.' });
    }
});

app.listen(port, () => {
    console.log(`서버가 http://localhost:${port} 에서 실행 중입니다.`);
});