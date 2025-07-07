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
    const { message, sessionId } = req.body;

    if (!message || !sessionId) {
        return res.status(400).json({ error: '메시지 또는 세션 ID가 없습니다.' });
    }

    try {
        const fullUrl = `${N8N_WEBHOOK_URL}?sessionId=${sessionId}`;

        // 메시지를 n8n 웹훅에 POST로 전달
        const n8nResponse = await axios.post(fullUrl, {
            message: message
        });

        // Gemini API 형식 기준으로 응답 파싱
        const candidates = n8nResponse.data?.candidates;
        const reply = candidates?.[0]?.content?.parts?.[0]?.text;

        if (reply) {
            res.json({ output: reply });
        } else {
            // 파싱 실패 시 전체 응답 로그와 함께 에러 반환
            console.error('Gemini 응답 파싱 실패:', n8nResponse.data);
            res.status(500).json({ error: '챗봇 응답을 파싱할 수 없습니다.' });
        }

    } catch (error) {
        console.error('n8n 통신 오류:', error.message);
        res.status(500).json({ error: '챗봇 서버와 통신할 수 없습니다.' });
    }
});

app.listen(port, () => {
    console.log(`서버가 http://localhost:${port} 에서 실행 중입니다.`);
});
