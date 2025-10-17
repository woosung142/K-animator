const API_BASE_URL = 'https://apim-k-animator.azure-api.net'; 

// 2. 기본 설정을 포함한 axios 인스턴스(api 통신 전용 객체)를 생성합니다.
const api = axios.create({
    baseURL: API_BASE_URL,
    // [핵심 수정] 모든 요청에 대해 쿠키를 주고받을 수 있도록 전역으로 설정합니다.
    withCredentials: true, 
    headers: {
        'Ocp-Apim-Subscription-Key': 'a4bd779874b84eaa822f26531abb2509',
    }
});

// 3. "요청 가로채기" 설정: 모든 API 요청이 보내지기 전에 이 코드가 먼저 실행됩니다.
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

        if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                console.log('Access Token 만료! 재발급을 시도합니다...');
                
                // '/api/auth/refresh' API 호출 (withCredentials는 이제 전역 설정으로 처리됩니다.)
                const refreshResponse = await api.post('/api/auth/refresh');

                const { access_token: newAccessToken } = refreshResponse.data;

                localStorage.setItem('accessToken', newAccessToken);
                console.log('토큰 재발급 성공! 다시 시도합니다.');

                return api(originalRequest);

            } catch (refreshError) {
                console.error('Refresh Token이 유효하지 않습니다. 강제 로그아웃합니다.', refreshError);
                localStorage.removeItem('accessToken');
                window.location.href = 'index.html';
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);