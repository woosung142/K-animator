const API_BASE_URL = 'https://api.prtest.shop'; 

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

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        if (error.response.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/api/auth/')) {
            originalRequest._retry = true;

            try {
                console.log('Access Token 만료! 재발급을 시도합니다...');
                const refreshResponse = await api.post('/api/auth/refresh');

                if (refreshResponse.data && refreshResponse.data.access_token) {
                    const newAccessToken = refreshResponse.data.access_token;
                    localStorage.setItem('accessToken', newAccessToken);
                    console.log('토큰 재발급 성공! 원래 요청을 다시 시도합니다.');

                    originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
                    return api(originalRequest);
                } else {
                    console.error('Refresh 응답은 성공했으나, access_token이 비어있습니다. 응답 데이터:', refreshResponse.data);
                    throw new Error('Invalid refresh response');
                }

            } catch (refreshError) {
                console.error('Refresh Token이 유효하지 않거나 재발급에 실패했습니다. 강제 로그아웃합니다.', refreshError);
                localStorage.removeItem('accessToken');
                window.location.href = 'index.html'; 
                return Promise.reject(refreshError);
            }
        }
        
        // 처리할 수 없는 다른 모든 에러는 그대로 반환
        return Promise.reject(error);
    }
);