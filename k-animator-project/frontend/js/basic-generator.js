// DOM 요소 가져오기
const userProfileBtn = document.getElementById('user-profile-btn');
const userProfileModal = document.getElementById('user-profile-modal');
const closeProfileBtn = document.getElementById('close-profile-btn');
const logoutBtn = document.getElementById('logout-btn');

const profileUsername = document.getElementById('profile-username');
const profileFullname = document.getElementById('profile-fullname');
const profileEmail = document.getElementById('profile-email');

// APIM 구독 키는 api.js에 설정되어 있으므로, 여기서는 신경 쓰지 않습니다.

/**
 * 사용자 프로필 데이터를 백엔드에서 가져와 모달에 표시합니다.
 */
async function fetchAndDisplayUserProfile() {
    // 로딩 상태 표시
    profileUsername.textContent = '로딩 중...';
    profileFullname.textContent = '로딩 중...';
    profileEmail.textContent = '로딩 중...';

    try {
        // '/api/users/me' 엔드포인트는 Access Token을 요구하며, 
        // api.js의 인터셉터가 자동으로 Authorization 헤더를 추가합니다.
        const response = await api.get('/api/users/me');
        const user = response.data;

        // 데이터 표시
        profileUsername.textContent = user.username;
        profileFullname.textContent = user.full_name;
        profileEmail.textContent = user.email;

    } catch (error) {
        console.error('사용자 프로필 조회 실패:', error);
        
        let errorMessage = '프로필 정보를 가져오는 데 실패했습니다.';
        if (error.response && error.response.status === 401) {
             errorMessage = '인증이 만료되었습니다. 다시 로그인해주세요.';
        } else if (error.response && error.response.data && error.response.data.detail) {
             errorMessage = `프로필 조회 실패: ${error.response.data.detail}`;
        }
        
        // 에러 메시지 표시
        profileUsername.textContent = '오류 발생';
        profileFullname.textContent = errorMessage;
        profileEmail.textContent = '---';

        // 401이면 로그인 페이지로 리다이렉트 (auth-guard.js에서 처리할 수도 있습니다)
        if (error.response && error.response.status === 401) {
             localStorage.removeItem('accessToken');
             window.location.href = 'index.html'; 
        }
    }
}

/**
 * 사용자 프로필 모달을 열고 사용자 데이터를 가져옵니다.
 */
userProfileBtn.addEventListener('click', () => {
    userProfileModal.classList.add('active');
    fetchAndDisplayUserProfile();
});

/**
 * 사용자 프로필 모달을 닫습니다.
 */
closeProfileBtn.addEventListener('click', () => {
    userProfileModal.classList.remove('active');
});

/**
 * 로그아웃 처리 함수입니다.
 */
logoutBtn.addEventListener('click', async () => {
    try {
        // 백엔드의 로그아웃 엔드포인트 호출
        // 이 요청은 쿠키에 담긴 Refresh Token을 삭제합니다.
        const response = await api.post('/api/users/logout');
        
        if (response.status === 200) {
            // 로컬 스토리지의 Access Token 제거 및 로그인 페이지로 리다이렉트
            localStorage.removeItem('accessToken');
            alert('성공적으로 로그아웃되었습니다.');
            window.location.href = 'index.html';
        }

    } catch (error) {
        // 로그아웃 자체는 서버에서 리프레시 토큰만 지우면 되므로, 
        // 오류 발생 시에도 클라이언트 측에서는 강제 로그아웃을 진행하는 것이 안전합니다.
        console.error('로그아웃 요청 실패:', error);
        localStorage.removeItem('accessToken');
        alert('로그아웃 처리 중 오류가 발생했습니다. 강제 로그아웃됩니다.');
        window.location.href = 'index.html';
    }
});


// 기타 생성기 관련 로직은 여기에 추가될 수 있습니다.
const generateButton = document.getElementById('generate-button');
if (generateButton) {
    generateButton.addEventListener('click', () => {
        console.log('이미지 생성 버튼이 클릭되었습니다.');
        // 여기에 이미지 생성 API 호출 로직을 구현합니다.
    });
}
