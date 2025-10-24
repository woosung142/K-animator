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

// ===================================================================================
// 추가된 기능들
// ===================================================================================

// 1. STT (Speech-to-Text) 기능 (Azure Speech SDK 사용)
// -----------------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {

    // 1. 필요한 모든 변수를 미리 선언합니다.
    const sttBtn = document.getElementById('stt-btn');
    const descriptionTextarea = document.getElementById('description');
    let recognizer; // 음성 인식기는 한 번만 만들어서 계속 사용할 것이므로 미리 변수를 만들어 둡니다.

    // 2. [잘 되던 코드의 장점] 페이지가 열리면 딱 한 번만 실행해서 미리 모든 것을 준비합니다.
    const initializeSpeechRecognizer = async () => {
        try {
            // 백엔드에서 토큰을 먼저 받아옵니다.
            const response = await api.get('/api/utils/get-speech-token');
            const { token, region } = response.data;

            // 받아온 토큰으로 SpeechSDK 설정을 구성합니다.
            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
            speechConfig.speechRecognitionLanguage = 'ko-KR';

            // 마이크 입력을 설정합니다.
            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
            
            recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

            // 모든 준비가 끝났으므로 버튼을 활성화합니다.
            sttBtn.disabled = false;
            console.log("음성 인식기가 성공적으로 초기화되었습니다.");

        } catch (error) {
            // 초기화 과정에서 에러가 발생하면 사용자에게 알립니다.
            console.error('음성 인식기 초기화 실패:', error);
            sttBtn.title = "음성 인식 서비스를 사용할 수 없습니다.";
            sttBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
            sttBtn.disabled = true;
        }
    };

    // 3. [개선된 에러 처리] 버튼 클릭 이벤트는 이제 '사용'에만 집중하며, 어떤 상황에서도 먹통이 되지 않습니다.
    sttBtn.addEventListener('click', async () => {
        if (!recognizer) {
            alert('음성 인식 서비스가 아직 준비되지 않았습니다.');
            return;
        }

        const originalIconHTML = sttBtn.innerHTML;
        sttBtn.disabled = true;
        sttBtn.innerHTML = '<i class="fa-solid fa-ear-listen"></i>'; // 듣는 중 아이콘
        descriptionTextarea.placeholder = '말씀해주세요...';

        try {
            // 미리 준비된 recognizer를 사용해 음성 인식을 시작합니다.
            const result = await recognizer.recognizeOnceAsync();

            // 결과를 텍스트 상자에 표시합니다.
            if (result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
                descriptionTextarea.value = result.text;
            } else {
                descriptionTextarea.placeholder = '음성을 인식하지 못했습니다. 다시 시도해주세요.';
            }
        } catch (error) {
            console.error("음성 인식 중 에러 발생:", error);
            descriptionTextarea.placeholder = '음성 인식 중 오류가 발생했습니다.';
        } finally {
            // 성공하든, 실패하든, 무조건 버튼을 원래 상태로 되돌립니다.
            sttBtn.disabled = false;
            sttBtn.innerHTML = originalIconHTML;
            descriptionTextarea.placeholder = '예: 접시에 담긴 먹음직스러운 김치 그려줘';
        }
    });

    // --- 실행 시작 ---
    // 페이지의 모든 HTML이 준비되면, 음성 인식기 초기화를 시작합니다.
    initializeSpeechRecognizer();
});

// 2. 내 정보 수정 (이름)
// -----------------------------------------------------------------------------------
const editProfileBtn = document.getElementById('edit-profile-btn');
const saveProfileBtn = document.getElementById('save-profile-btn');

if (editProfileBtn && saveProfileBtn && profileFullname) {
    editProfileBtn.addEventListener('click', () => {
        profileFullname.contentEditable = true;
        profileFullname.focus();
        editProfileBtn.style.display = 'none';
        saveProfileBtn.style.display = 'inline-block';
    });

    saveProfileBtn.addEventListener('click', async () => {
        const newFullName = profileFullname.textContent;
        try {
            await api.patch('/api/users/me', { full_name: newFullName });
            alert('이름이 성공적으로 변경되었습니다.');
            profileFullname.contentEditable = false;
            saveProfileBtn.style.display = 'none';
            editProfileBtn.style.display = 'inline-block';
        } catch (error) {
            console.error('이름 변경 실패:', error);
            alert('이름 변경에 실패했습니다.');
            // 원래 이름으로 되돌릴 수 있도록 다시 프로필 정보를 불러옵니다.
            fetchAndDisplayUserProfile(); 
        }
    });
}


// 3. 비밀번호 변경
// -----------------------------------------------------------------------------------
const changePasswordBtn = document.getElementById('change-password-btn');
const changePasswordModal = document.getElementById('change-password-modal');
const closeChangePasswordBtn = document.getElementById('close-change-password-btn');
const changePasswordForm = document.getElementById('change-password-form');

if (changePasswordBtn && changePasswordModal && closeChangePasswordBtn && changePasswordForm) {
    changePasswordBtn.addEventListener('click', () => {
        changePasswordModal.classList.add('active');
    });

    closeChangePasswordBtn.addEventListener('click', () => {
        changePasswordModal.classList.remove('active');
    });

    changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const oldPassword = document.getElementById('old-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        if (newPassword !== confirmPassword) {
            alert('새 비밀번호가 일치하지 않습니다.');
            return;
        }

        try {
            // [FIX] HTTP 메소드를 PUT에서 PATCH로 변경
            await api.patch('/api/users/me/password', {
                current_password: oldPassword,
                new_password: newPassword,
            });
            alert('비밀번호가 성공적으로 변경되었습니다.');
            changePasswordForm.reset();
            changePasswordModal.classList.remove('active');
        } catch (error) {
            console.error('비밀번호 변경 실패:', error);
            let errorMessage = '비밀번호 변경에 실패했습니다.';
            if (error.response && error.response.data && error.response.data.detail) {
                errorMessage = `실패: ${error.response.data.detail}`;
            }
            alert(errorMessage);
        }
    });
}


// 4. 회원 탈퇴
// -----------------------------------------------------------------------------------
const deleteAccountBtn = document.getElementById('delete-account-btn');

if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener('click', async () => {
        if (confirm('정말로 회원 탈퇴를 하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
            try {
                await api.delete('/api/users/me');
                alert('회원 탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.');
                localStorage.removeItem('accessToken');
                window.location.href = 'index.html';
            } catch (error) {
                console.error('회원 탈퇴 실패:', error);
                alert('회원 탈퇴 처리 중 오류가 발생했습니다.');
            }
        }
    });
}
