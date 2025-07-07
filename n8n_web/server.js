const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const port = 3000;

app.use(express.json());

// n8n 웹훅 URL - Chat Trigger는 쿼리 파라미터로 sessionId를 받습니다.
const N8N_WEBHOOK_URL = 'http://20.196.73.32:5678/webhook/bc35d298-b105-4394-81df-b1c981efaaf2/chat';

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/send-message', async (req, res) => {
    // 1. 프론트엔드에서 message와 sessionId를 모두 받음
    const { messages, sessionId } = req.body;

    if (!messages || !sessionId) {
        return res.status(400).json({ error: '메시지 또는 세션 ID가 없습니다.' });
    }

    try {
        const fullUrl = `${N8N_WEBHOOK_URL}?sessionId=${sessionId}`;

        // 메시지를 n8n 웹훅에 POST로 전달
        const n8nResponse = await axios.post(fullUrl, {
            messages: messages
        });

        // 4. n8n Agent의 최종 응답('output' 필드)을 프론트엔드로 전달
        res.json({ text: n8nResponse.data.text });
    } catch (error) {
        console.error('n8n 통신 오류:', error.messages);
        res.status(500).json({ error: '챗봇 서버와 통신할 수 없습니다.' });
    }
});

app.listen(port, () => {
    console.log(`서버가 http://localhost:${port} 에서 실행 중입니다.`);
});
