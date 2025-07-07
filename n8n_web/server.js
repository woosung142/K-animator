const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const port = 3000;

// JSON 요청 본문을 파싱하기 위한 미들웨어
app.use(express.json());

// n8n 웹훅 URL (반드시 본인의 Production URL로 변경)
const N8N_WEBHOOK_URL = 'http://20.196.73.32:5678/webhook/9dc8aa1f-0e2b-4de9-ae86-141cdac3ede1';

// 기본 HTML 페이지 제공
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// 프론트엔드로부터 메시지를 받아 n8n으로 전달하는 API
app.post('/send-message', async (req, res) => {
    const { message } = req.body; // 프론트엔드에서 보낸 메시지

    if (!message) {
        return res.status(400).json({ error: '메시지가 없습니다.' });
    }

    try {
        // n8n 웹훅으로 POST 요청 전송
        const n8nResponse = await axios.post(N8N_WEBHOOK_URL, {
            message: message // 워크플로우에서 받을 데이터 형식에 맞게 전송
        });

        // n8n의 응답을 프론트엔드로 다시 전달
        res.json({ reply: n8nResponse.data.reply ?? n8nResponse.data});
    } catch (error) {
        console.error('n8n 통신 오류:', error);
        res.status(500).json({ error: '챗봇 서버와 통신할 수 없습니다.' });
    }
});

app.listen(port, () => {
    console.log(`서버가 http://localhost:${port} 에서 실행 중입니다.`);
});