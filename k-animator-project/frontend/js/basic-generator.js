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


// ===================================================================================
// 페이지 로드 시 실행되는 기능들
// ===================================================================================
document.addEventListener('DOMContentLoaded', () => {

    // 1. STT (Speech-to-Text) 기능
    // -----------------------------------------------------------------------------------
    const sttBtn = document.getElementById('stt-btn');
    const descriptionTextareaForStt = document.getElementById('description');
    let recognizer; 

    const initializeSpeechRecognizer = async () => {
        try {
            const response = await api.get('/api/utils/get-speech-token');
            const { token, region } = response.data;

            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
            speechConfig.speechRecognitionLanguage = 'ko-KR';

            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
            
            recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

            sttBtn.disabled = false;
            console.log("음성 인식기가 성공적으로 초기화되었습니다.");

        } catch (error) {
            console.error('음성 인식기 초기화 실패:', error);
            sttBtn.title = "음성 인식 서비스를 사용할 수 없습니다.";
            sttBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
            sttBtn.disabled = true;
        }
    };

    sttBtn.addEventListener('click', async () => {
        if (!recognizer) {
            alert('음성 인식 서비스가 아직 준비되지 않았습니다.');
            return;
        }

        const originalIconHTML = sttBtn.innerHTML;
        sttBtn.disabled = true;
        sttBtn.innerHTML = '<i class="fa-solid fa-ear-listen"></i>'; 
        descriptionTextareaForStt.placeholder = '말씀해주세요...';

        try {
            const result = await recognizer.recognizeOnceAsync();

            if (result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
                descriptionTextareaForStt.value = result.text;
            } else {
                descriptionTextareaForStt.placeholder = '음성을 인식하지 못했습니다. 다시 시도해주세요.';
            }
        } catch (error) {
            console.error("음성 인식 중 에러 발생:", error);
            descriptionTextareaForStt.placeholder = '음성 인식 중 오류가 발생했습니다.';
        } finally {
            sttBtn.disabled = false;
            sttBtn.innerHTML = originalIconHTML;
            descriptionTextareaForStt.placeholder = '예: 접시에 담긴 먹음직스러운 김치 그려줘';
        }
    });

    initializeSpeechRecognizer();

    // 2. 이미지 생성 기능
    // -----------------------------------------------------------------------------------
    
    const categoryButtons = document.querySelectorAll('.form-group:nth-of-type(1) .btn-option');
    const layerButtons = document.querySelectorAll('.form-group:nth-of-type(2) .btn-option');
    const keywordsInput = document.getElementById('keywords');
    const descriptionTextarea = document.getElementById('description');
    const charCounter = document.querySelector('.char-counter');
    const generateButton = document.getElementById('generate-button');
    const displayPanel = document.querySelector('.panel.display-panel');
    const uploadBox = document.querySelector('.upload-box');
    const fileInput = document.querySelector('.file-input');
    let uploadedImageUrl = null;

    const API_BASE_URL = '/api/model';

    function setupButtonGroup(buttons) {
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                buttons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
            });
        });
    }
    setupButtonGroup(categoryButtons);
    setupButtonGroup(layerButtons);

    const updateDisplayPanel = (state, data = null) => {
        const containerToUpdate = displayPanel.querySelector('.image-placeholder, .loading-spinner, .image-result-container, .error');
        let content = '';

        switch (state) {
            case 'loading':
                content = `
                    <div class="loading-spinner">
                        <div class="spinner"></div>
                        <p><b>이미지를 생성하고 있습니다...</b></p>
                        <p>잠시만 기다려 주세요. 최대 1~2분 소요될 수 있습니다.</p>
                    </div>
                `;
                break;
            case 'success':
                content = `
                    <div class="image-result-container">
                        <img src="${data.png_url}" alt="생성된 이미지" class="generated-image">
                        <div class="image-actions">
                            <a href="edit.html?imageUrl=${encodeURIComponent(data.png_url)}" class="btn btn-primary">이미지 편집하기</a>
                            <a href="${data.png_url}" download="generated_image.png" class="btn btn-secondary">PNG 다운로드</a>
                            <a href="${data.psd_url}" download="generated_image.psd" class="btn btn-secondary">PSD 다운로드</a>
                        </div>
                    </div>
                `;
                break;
            case 'error':
                content = `
                    <div class="image-placeholder error">
                        <i class="fa-regular fa-circle-xmark"></i>
                        <p><b>이미지 생성에 실패했습니다</b></p>
                        <p>${data.error || '알 수 없는 오류가 발생했습니다. 다시 시도해 주세요.'}</p>
                    </div>
                `;
                break;
            default: 
                content = `
                    <div class="image-placeholder">
                        <i class="fa-regular fa-image"></i>
                        <p><b>아직 생성된 이미지가 없습니다</b></p>
                        <p>왼쪽 패널에서 설정을 완료하고 이미지를 생성해보세요</p>
                    </div>
                `;
        }
        
        if (containerToUpdate) {
            containerToUpdate.outerHTML = content;
        }
    };

    const pollForResult = (taskId) => {
        const pollInterval = 4000;
        const maxAttempts = 45;
        let attempts = 0;

        const intervalId = setInterval(async () => {
            if (attempts >= maxAttempts) {
                clearInterval(intervalId);
                updateDisplayPanel('error', { error: '작업 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.' });
                generateButton.disabled = false;
                generateButton.textContent = '이미지 생성하기';
                return;
            }

            try {
                const response = await api.get(`${API_BASE_URL}/result/${taskId}`);
                const result = response.data;

                if (result.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    updateDisplayPanel('success', result);
                    generateButton.disabled = false;
                    generateButton.textContent = '이미지 생성하기';
                } else if (result.status === 'FAILURE') {
                    clearInterval(intervalId);
                    updateDisplayPanel('error', { error: result.error || '작업 실패' });
                    generateButton.disabled = false;
                    generateButton.textContent = '이미지 생성하기';
                }
            } catch (error) {
                console.error('결과 폴링 중 오류 발생:', error);
                clearInterval(intervalId);
                const errorMessage = error.response?.data?.detail || '결과를 가져오는 중 오류가 발생했습니다.';
                updateDisplayPanel('error', { error: errorMessage });
                generateButton.disabled = false;
                generateButton.textContent = '이미지 생성하기';
            }
            attempts++;
        }, pollInterval);
    };

    if (generateButton) {
        generateButton.addEventListener('click', async (event) => {
            event.preventDefault();

            const activeCategory = document.querySelector('.form-group:nth-of-type(1) .btn-option.active');
            const activeLayer = document.querySelector('.form-group:nth-of-type(2) .btn-option.active');
            const keywords = keywordsInput.value.trim();
            const description = descriptionTextarea.value.trim();

            if (!activeCategory || !activeLayer || !keywords || !description) {
                alert('카테고리, 레이어, 키워드, 장면 설명을 모두 입력해주세요.');
                return;
            }

            generateButton.disabled = true;
            generateButton.textContent = '생성 중...';
            updateDisplayPanel('loading');

            const requestData = {
                category: activeCategory.textContent,
                layer: activeLayer.textContent,
                tag: keywords,
                caption_input: description,
                image_url: uploadedImageUrl
            };

            try {
                const response = await api.post(`${API_BASE_URL}/generate-prompt`, requestData);
                const { task_id } = response.data;

                if (task_id) {
                    pollForResult(task_id);
                } else {
                    throw new Error('Task ID를 받지 못했습니다.');
                }
            } catch (error) {
                console.error('생성 요청 실패:', error);
                const errorMessage = error.response?.data?.detail || 'API 요청에 실패했습니다. 서버 상태를 확인해주세요.';
                updateDisplayPanel('error', { error: errorMessage });
                generateButton.disabled = false;
                generateButton.textContent = '이미지 생성하기';
            }
        });
    }

    if (uploadBox) {
        uploadBox.addEventListener('click', () => fileInput.click());
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files[0]) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    uploadedImageUrl = e.target.result;
                    uploadBox.innerHTML = `<img src="${uploadedImageUrl}" alt="참조 이미지 미리보기" class="image-preview">`;
                };
                reader.readAsDataURL(fileInput.files[0]);
            }
        });
    }
    
    if (descriptionTextarea) {
        descriptionTextarea.addEventListener('input', () => {
            const count = descriptionTextarea.value.length;
            if(charCounter) charCounter.textContent = `${count}/500`;
        });
    }
});

// 3. 내 정보 수정 (이름)
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
            fetchAndDisplayUserProfile(); 
        }
    });
}


// 4. 비밀번호 변경
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


// 5. 회원 탈퇴
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