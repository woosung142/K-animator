const API_BASE_URL = 'https://apim-k-animator.azure-api.net'; 

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, 
    headers: {
        'Ocp-Apim-Subscription-Key': 'a4bd779874b84eaa822f26531abb2509',
    }
});

api.interceptors.request.use(
    (config) => {
        const accessToken = localStorage.getItem('accessToken');
        if (accessToken) {
            config.headers['Authorization'] = `Bearer ${accessToken}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 4. "응답 가로채기" 설정: 토큰 자동 재발급
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response.status === 401 && !originalRequest._retry && originalRequest.url !== '/api/auth/login') {
            originalRequest._retry = true; // 무한 루프 방지를 위해 재시도 플래그 설정

            try {
                console.log('Access Token 만료! 재발급을 시도합니다...');
                
                const refreshResponse = await api.post('/api/auth/refresh');

                const { access_token: newAccessToken } = refreshResponse.data;

                localStorage.setItem('accessToken', newAccessToken);
                console.log('토큰 재발급 성공! 다시 시도합니다.');

                // 원래 실패했던 요청을 새로운 토큰으로 다시 실행
                return api(originalRequest);

            } catch (refreshError) {
                console.error('Refresh Token이 유효하지 않습니다. 강제 로그아웃합니다.', refreshError);
                localStorage.removeItem('accessToken');
                window.location.href = 'index.html'; // 로그인 페이지로 리디렉션
                return Promise.reject(refreshError);
            }
        }
        
        return Promise.reject(error);
    }
);

