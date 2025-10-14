require('dotenv').config();

const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

const N8N_WEBHOOK_URL = process.env.N8N_WEBHOOK_URL;

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/send-message', async (req, res) => {
    const { messages, sessionId } = req.body;

    if (!messages || !sessionId) {
        return res.status(400).json({ error: '메시지 또는 세션 ID가 없습니다.' });
    }

    try {
        const fullUrl = `${N8N_WEBHOOK_URL}?sessionId=${sessionId}`;

        // n8n에 메시지 전송
        const n8nResponse = await axios.post(fullUrl, { chatInput: messages });

        // 응답 JSON 전체 출력 (디버깅용)
        console.log('[n8n 응답]', JSON.stringify(n8nResponse.data, null, 2));

        // 일반 텍스트 응답 추출
        const text = n8nResponse.data?.output || '[빈 응답]';

        res.json({ text });
    } catch (error) {
        console.error('n8n 통신 오류:', error.message); // ✅ 오타 수정
        res.status(500).json({ error: '챗봇 서버와 통신할 수 없습니다.' });
    }
});

app.listen(port, () => {
    console.log(`서버가 http://localhost:${port} 에서 실행 중입니다.`);
});
